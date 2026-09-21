from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from changes.models import VlanChangeLog
from discovery.models import PortObservation
from inventory.models import Facility, Switch, VlanProfile


class VlanChangeWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="agent", password="test-password")
        self.facility = Facility.objects.create(code="F19114", name="Main Office")
        self.switch = Switch.objects.create(
            facility=self.facility,
            name="MDF-01",
            hostname="mdf-01.example.test",
            management_ip="192.0.2.10",
            closet_role=Switch.ClosetRole.MDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        self.current_vlan = VlanProfile.objects.create(
            facility=self.facility,
            label="Vendor",
            vlan_id=201,
            assignment_mode=VlanProfile.AssignmentMode.STATIC,
            requester_ad_group="GG-Network-Vendor",
        )
        self.target_vlan = VlanProfile.objects.create(
            facility=self.facility,
            label="Internal",
            vlan_id=1,
            assignment_mode=VlanProfile.AssignmentMode.POLICY_CONTROLLED,
            requester_ad_group="GG-Network-Internal",
            allow_helpdesk_port_change=True,
        )
        self.voice_vlan = VlanProfile.objects.create(
            facility=self.facility,
            label="Voice",
            vlan_id=300,
            assignment_mode=VlanProfile.AssignmentMode.POLICY_CONTROLLED,
            requester_ad_group="GG-Network-Voice",
        )
        self.observation = PortObservation.objects.create(
            mac_address="02:00:00:00:00:01",
            switch=self.switch,
            interface_name="1/1/15",
            vlan_id=201,
        )

    def test_request_requires_login(self):
        response = self.client.get(reverse("changes-request", args=[self.observation.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_login_page_is_available(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_agent_can_request_vlan_one_without_writing_to_switch(self):
        self.client.login(username="agent", password="test-password")

        response = self.client.post(
            reverse("changes-request", args=[self.observation.pk]),
            {"requested_vlan": self.target_vlan.pk},
        )

        self.assertRedirects(response, reverse("changes-requested", args=[self.observation.pk]))
        change = VlanChangeLog.objects.get()
        self.assertEqual(change.status, VlanChangeLog.Status.PENDING)
        self.assertEqual(change.requested_vlan, self.target_vlan)
        audit = AuditLog.objects.get()
        self.assertEqual(audit.event_type, AuditLog.EventType.VLAN_CHANGE)
        self.assertEqual(audit.detail["action"], "request_created")
        self.assertEqual(audit.detail["requested_vlan"], 1)

    def test_policy_controlled_non_vlan_one_is_not_offered(self):
        self.client.login(username="agent", password="test-password")

        response = self.client.get(reverse("changes-request", args=[self.observation.pk]))

        self.assertNotContains(response, "Voice")