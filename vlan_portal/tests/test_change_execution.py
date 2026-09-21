from unittest.mock import patch

from django.contrib import admin
from django.test import TestCase, override_settings
from django.test.client import RequestFactory

from changes.execution import ChangeExecutionError, execute_pending_change
from changes.admin import VlanChangeLogAdmin
from changes.models import VlanChangeLog
from audit.models import AuditLog
from inventory.models import Facility, Switch, VlanProfile
from django.contrib.auth import get_user_model


class FakeChangeConnector:
    def __init__(self, verified=True, error=None):
        self.verified = verified
        self.error = error
        self.applied = []

    def apply(self, change):
        if self.error:
            raise RuntimeError(self.error)
        self.applied.append(change.id)

    def verify(self, change):
        return self.verified


class ChangeExecutionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="agent", password="test-password")
        facility = Facility.objects.create(code="F19114", name="Main Office")
        self.switch = Switch.objects.create(
            facility=facility,
            name="MDF-01",
            hostname="mdf-01.example.test",
            management_ip="192.0.2.10",
            closet_role=Switch.ClosetRole.MDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        self.previous_vlan = VlanProfile.objects.create(
            facility=facility,
            label="Vendor",
            vlan_id=201,
            assignment_mode=VlanProfile.AssignmentMode.STATIC,
            requester_ad_group="GG-Network-Vendor",
        )
        self.requested_vlan = VlanProfile.objects.create(
            facility=facility,
            label="Internal",
            vlan_id=1,
            assignment_mode=VlanProfile.AssignmentMode.POLICY_CONTROLLED,
            requester_ad_group="GG-Network-Internal",
            allow_helpdesk_port_change=True,
        )
        self.change = VlanChangeLog.objects.create(
            requested_by=self.user,
            switch=self.switch,
            interface_name="1/1/15",
            mac_address="02:00:00:00:00:01",
            previous_vlan=self.previous_vlan,
            requested_vlan=self.requested_vlan,
        )
        self.change.approve(self.user)
        self.change.save(update_fields=["status", "approved_by", "approved_at"])

    @override_settings(CHANGE_EXECUTION_ENABLED=True)
    def test_verified_change_becomes_applied(self):
        connector = FakeChangeConnector()

        result = execute_pending_change(self.change.pk, connector)

        self.change.refresh_from_db()
        self.assertEqual(result.status, VlanChangeLog.Status.APPLIED)
        self.assertEqual(self.change.status, VlanChangeLog.Status.APPLIED)
        self.assertEqual(connector.applied, [self.change.pk])
        self.assertIsNotNone(self.change.applied_at)
        self.assertEqual(AuditLog.objects.filter(detail__action="execution_applied").count(), 1)

    @override_settings(CHANGE_EXECUTION_ENABLED=True)
    def test_failed_verification_marks_change_failed(self):
        connector = FakeChangeConnector(verified=False)

        with self.assertRaisesMessage(ChangeExecutionError, "did not verify"):
            execute_pending_change(self.change.pk, connector)

        self.change.refresh_from_db()
        self.assertEqual(self.change.status, VlanChangeLog.Status.FAILED)
        self.assertIn("did not verify", self.change.error_message)
        self.assertEqual(AuditLog.objects.filter(detail__action="execution_failed").count(), 1)

    def test_execution_is_disabled_by_default(self):
        with self.assertRaisesMessage(ChangeExecutionError, "disabled by configuration"):
            execute_pending_change(self.change.pk, FakeChangeConnector())

        self.change.refresh_from_db()
        self.assertEqual(self.change.status, VlanChangeLog.Status.APPROVED)

    @override_settings(
        CHANGE_EXECUTION_ENABLED=True,
        CHANGE_SSH_USERNAME="writer",
        CHANGE_SSH_PASSWORD="secret",
    )
    @patch("changes.admin.execute_vlan_change.delay")
    def test_approval_queues_worker_after_commit(self, delay):
        pending = VlanChangeLog.objects.create(
            requested_by=self.user,
            switch=self.switch,
            interface_name="1/1/16",
            mac_address="02:00:00:00:00:02",
            previous_vlan=self.previous_vlan,
            requested_vlan=self.requested_vlan,
        )
        request = RequestFactory().post("/admin/changes/vlanchangelog/")
        request.user = self.user
        model_admin = VlanChangeLogAdmin(VlanChangeLog, admin.site)

        with self.captureOnCommitCallbacks(execute=True):
            with patch.object(model_admin, "message_user"):
                model_admin.approve_requests(request, VlanChangeLog.objects.filter(pk=pending.pk))

        pending.refresh_from_db()
        self.assertEqual(pending.status, VlanChangeLog.Status.APPROVED)
        delay.assert_called_once_with(pending.pk)
