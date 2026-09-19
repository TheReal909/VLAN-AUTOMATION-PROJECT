from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase
from django.test import TestCase

from discovery.models import PortObservation
from inventory.models import Facility, Switch, VlanProfile


class SwitchCleanTests(SimpleTestCase):
    def setUp(self):
        self.facility = Facility(code="F19114", name="Test facility")
        self.mdf = Switch(
            pk=1,
            facility=self.facility,
            name="MDF-01",
            hostname="mdf-01.example.test",
            management_ip="192.0.2.1",
            closet_role=Switch.ClosetRole.MDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )

    def test_idf_can_point_to_another_idf_that_points_to_mdf(self):
        idf_01 = Switch(
            pk=2,
            facility=self.facility,
            name="IDF-01",
            hostname="idf-01.example.test",
            management_ip="192.0.2.2",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=self.mdf,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        idf_02 = Switch(
            pk=3,
            facility=self.facility,
            name="IDF-02",
            hostname="idf-02.example.test",
            management_ip="192.0.2.3",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=idf_01,
            model_family=Switch.ModelFamily.ICX_7150,
        )

        idf_02.clean()

    def test_idf_without_upstream_is_valid_for_dynamic_discovery(self):
        idf = Switch(
            pk=2,
            facility=self.facility,
            name="IDF-01",
            hostname="idf-01.example.test",
            management_ip="192.0.2.2",
            closet_role=Switch.ClosetRole.IDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )

        idf.clean()

    def test_idf_upstream_hierarchy_cannot_contain_a_cycle(self):
        idf_01 = Switch(
            pk=2,
            facility=self.facility,
            name="IDF-01",
            hostname="idf-01.example.test",
            management_ip="192.0.2.2",
            closet_role=Switch.ClosetRole.IDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        idf_02 = Switch(
            pk=3,
            facility=self.facility,
            name="IDF-02",
            hostname="idf-02.example.test",
            management_ip="192.0.2.3",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=idf_01,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        idf_01.upstream_switch = idf_02

        with self.assertRaisesMessage(ValidationError, "cannot contain a cycle"):
            idf_02.clean()


class SeedDemoCommandTests(TestCase):
    def test_seed_demo_is_repeatable_and_creates_expected_topology(self):
        call_command("seed_demo")
        call_command("seed_demo")

        self.assertEqual(Facility.objects.count(), 1)
        self.assertEqual(Switch.objects.count(), 3)
        self.assertEqual(PortObservation.objects.count(), 1)
        idf_02 = Switch.objects.get(name="IDF-02")
        self.assertEqual(idf_02.upstream_switch.name, "IDF-01")
        self.assertEqual(idf_02.upstream_switch.upstream_switch.name, "MDF-01")

    def test_vlan_one_is_a_manual_change_target_even_when_policy_controlled(self):
        vlan_one = VlanProfile.objects.create(
            facility=Facility.objects.create(code="F19115", name="VLAN 1 Test"),
            label="Internal",
            vlan_id=1,
            assignment_mode=VlanProfile.AssignmentMode.POLICY_CONTROLLED,
            requester_ad_group="GG-Network-Internal",
            allow_helpdesk_port_change=True,
        )

        self.assertTrue(vlan_one.is_manually_changeable)
