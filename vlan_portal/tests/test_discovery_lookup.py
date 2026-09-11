from django.test import TestCase
from django.urls import reverse

from discovery.models import PortObservation
from inventory.models import Facility, Switch


class MacLookupTests(TestCase):
    def setUp(self):
        self.facility = Facility.objects.create(code="F19114", name="Main Office")
        self.mdf = Switch.objects.create(
            facility=self.facility,
            name="MDF-01",
            hostname="mdf-01.example.test",
            management_ip="192.0.2.10",
            closet_role=Switch.ClosetRole.MDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        self.switch = Switch.objects.create(
            facility=self.facility,
            name="IDF-02",
            hostname="idf-02.example.test",
            management_ip="192.0.2.12",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=self.mdf,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        PortObservation.objects.create(
            mac_address="02:00:00:00:00:01",
            switch=self.switch,
            interface_name="2/1/15",
            vlan_id=120,
        )

    def test_lookup_returns_switch_interface_and_vlan(self):
        response = self.client.get(
            reverse("discovery"),
            {"facility": self.facility.pk, "mac_address": "02-00-00-00-00-01"},
        )

        self.assertContains(response, "IDF-02")
        self.assertContains(response, "2/1/15")
        self.assertContains(response, "120")

    def test_lookup_does_not_return_observation_from_another_facility(self):
        other_facility = Facility.objects.create(code="F19115", name="Other Office")
        response = self.client.get(
            reverse("discovery"),
            {"facility": other_facility.pk, "mac_address": "02:00:00:00:00:01"},
        )

        self.assertContains(response, "No observation was found")
        self.assertNotContains(response, "IDF-02")
