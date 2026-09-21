from celery import shared_task
from django.conf import settings

from .connectors import FastIronVlanChangeConnector
from .execution import ChangeExecutionError, execute_pending_change


@shared_task(bind=True, max_retries=2)
def execute_vlan_change(self, change_id: int):
    if not settings.CHANGE_SSH_USERNAME or not settings.CHANGE_SSH_PASSWORD:
        raise RuntimeError("Change execution credentials are not configured.")
    connector = FastIronVlanChangeConnector(
        settings.CHANGE_SSH_USERNAME,
        settings.CHANGE_SSH_PASSWORD,
        port=settings.CHANGE_SSH_PORT,
        timeout=settings.CHANGE_SSH_TIMEOUT,
        command_mode=settings.CHANGE_COMMAND_MODE,
    )
    try:
        result = execute_pending_change(change_id, connector)
    except ChangeExecutionError:
        raise
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
    return {
        "change_id": result.change_id,
        "status": result.status,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
    }