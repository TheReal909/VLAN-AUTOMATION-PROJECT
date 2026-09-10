from django.core.management.base import BaseCommand
from django.db import transaction

from discovery.models import PortObservation
from inventory.models import Facility, Switch, VlanProfile


class Command(BaseCommand):
    help = "Create or update sanitized demo inventory data."

    @transaction.atomic
    def handle(self, *args, **options):
        facility, _ = Facility.objects.update_or_create(
            code="F19114",
            defaults={
                "name": "Demo Main Office",
                "address": "123 Example Street",
                "is_active": True,
            },
        )

        mdf = self._switch(
            facility,
            name="MDF-01",
            hostname="mdf-01.example.test",
            management_ip="192.0.2.10",
            closet_role=Switch.ClosetRole.MDF,
        )
        idf_01 = self._switch(
            facility,
            name="IDF-01",
            hostname="idf-01.example.test",
            management_ip="192.0.2.11",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=mdf,
        )
        idf_02 = self._switch(
            facility,
            name="IDF-02",
            hostname="idf-02.example.test",
            management_ip="192.0.2.12",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=idf_01,
        )

        VlanProfile.objects.update_or_create(
            facility=facility,
            label="Guest",
            defaults={
                "vlan_id": 120,
                "assignment_mode": VlanProfile.AssignmentMode.STATIC,
                "requester_ad_group": "GG-Network-Guest",
                "allow_helpdesk_port_change": True,
                "description": "Demo guest network",
                "is_active": True,
            },
        )
        VlanProfile.objects.update_or_create(
            facility=facility,
            label="Voice",
            defaults={
                "vlan_id": 130,
                "assignment_mode": VlanProfile.AssignmentMode.POLICY_CONTROLLED,
                "requester_ad_group": "GG-Network-Voice",
                "allow_helpdesk_port_change": False,
                "description": "Demo managed voice network",
                "is_active": True,
            },
        )
        PortObservation.objects.update_or_create(
            mac_address="02:00:00:00:00:01",
            defaults={
                "switch": idf_02,
                "interface_name": "1/1/10",
                "vlan_id": 120,
            },
        )

        self.stdout.write(self.style.SUCCESS("Demo facility, switches, VLANs, and observation are ready."))

    @staticmethod
    def _switch(facility, *, name, hostname, management_ip, closet_role, upstream_switch=None):
        switch, _ = Switch.objects.update_or_create(
            facility=facility,
            name=name,
            defaults={
                "hostname": hostname,
                "management_ip": management_ip,
                "closet_role": closet_role,
                "upstream_switch": upstream_switch,
                "model_family": Switch.ModelFamily.ICX_7150,
                "stack_member_count": 1,
                "fastiron_version": "10.0.10",
                "location_note": "Sanitized demo record",
                "is_active": True,
            },
        )
        return switch
