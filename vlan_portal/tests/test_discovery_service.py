from django.test import TestCase

from discovery.connectors import DiscoveryError, MacDiscoveryService
from discovery.parsers import LldpNeighbor, MacTableEntry
from inventory.models import Facility, Switch


class FakeConnector:
    def __init__(self, mac_results, neighbors):
        self.mac_results = mac_results
        self.neighbors = neighbors
        self.queried_switches = []

    def find_mac(self, switch, mac_address):
        self.queried_switches.append(switch.name)
        return self.mac_results.get(switch.name, [])

    def find_neighbors(self, switch):
        return self.neighbors.get(switch.name, [])


class MacDiscoveryServiceTests(TestCase):
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
        self.idf = Switch.objects.create(
            facility=self.facility,
            name="IDF-01",
            hostname="idf-01.example.test",
            management_ip="192.0.2.11",
            closet_role=Switch.ClosetRole.IDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )

    def test_service_follows_trunk_then_returns_endpoint(self):
        mac = "aa:bb:cc:dd:ee:ff"
        connector = FakeConnector(
            mac_results={
                "MDF-01": [MacTableEntry(mac, 201, "1/1/48", True)],
                "IDF-01": [MacTableEntry(mac, 201, "2/1/15", False)],
            },
            neighbors={
                "MDF-01": [LldpNeighbor("1/1/48", "IDF-01", "192.0.2.11")],
            },
        )

        result = MacDiscoveryService(connector).locate(self.facility, mac)

        self.assertEqual(result.switch, self.idf)
        self.assertEqual(result.entry.interface_name, "2/1/15")
        self.assertEqual(result.entry.vlan_id, 201)
        self.assertEqual([switch.name for switch in result.path], ["MDF-01", "IDF-01"])
        self.assertEqual(connector.queried_switches, ["MDF-01", "IDF-01"])

    def test_service_rejects_unresolved_uplink(self):
        mac = "aa:bb:cc:dd:ee:ff"
        connector = FakeConnector(
            mac_results={"MDF-01": [MacTableEntry(mac, 201, "1/1/48", True)]},
            neighbors={"MDF-01": []},
        )

        with self.assertRaisesMessage(DiscoveryError, "managed LLDP neighbor"):
            MacDiscoveryService(connector).locate(self.facility, mac)
