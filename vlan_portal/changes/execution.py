from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import VlanChangeLog


class ChangeExecutionError(Exception):
    """Raised when a VLAN change cannot be safely completed."""


class VlanChangeConnector(Protocol):
    def apply(self, change: VlanChangeLog) -> None: ...

    def verify(self, change: VlanChangeLog) -> bool: ...


@dataclass(frozen=True)
class ExecutionResult:
    change_id: int
    status: str
    completed_at: datetime | None


def execute_pending_change(change_id: int, connector: VlanChangeConnector) -> ExecutionResult:
    with transaction.atomic():
        change = (
            VlanChangeLog.objects.select_for_update()
            .select_related("switch", "previous_vlan", "requested_vlan")
            .get(pk=change_id)
        )
        if change.status != VlanChangeLog.Status.PENDING:
            raise ChangeExecutionError(f"Change {change_id} is not pending.")
    if not settings.CHANGE_EXECUTION_ENABLED:
        raise ChangeExecutionError("Change execution is disabled by configuration.")

    try:
        change.full_clean()
        connector.apply(change)
        if not connector.verify(change):
            raise ChangeExecutionError("The switch did not verify the requested VLAN.")
    except Exception as exc:
        change.status = VlanChangeLog.Status.FAILED
        change.error_message = str(exc)
        change.save(update_fields=["status", "error_message"])
        if isinstance(exc, ChangeExecutionError):
            raise
        raise ChangeExecutionError("VLAN change execution failed.") from exc

    completed_at = timezone.now()
    change.status = VlanChangeLog.Status.APPLIED
    change.applied_at = completed_at
    change.error_message = ""
    change.save(update_fields=["status", "applied_at", "error_message"])
    return ExecutionResult(change.id, change.status, completed_at)
