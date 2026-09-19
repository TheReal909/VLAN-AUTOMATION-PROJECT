from django.test import SimpleTestCase

from discovery.parsers import normalize_mac, parse_interface_is_trunk, parse_lldp_neighbors, parse_mac_table, parse_port_name


class DiscoveryParserTests(SimpleTestCase):
    def test_normalize_mac_accepts_common_formats(self):
        self.assertEqual(normalize_mac("aabb.ccdd.eeff"), "aa:bb:cc:dd:ee:ff")
        self.assertEqual(normalize_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")

    def test_parse_mac_table_finds_endpoint_and_trunk_entries(self):
        output = """
        VLAN MAC Address       Type      Port
        201  aabb.ccdd.eeff    Dynamic   2/1/15
        201  aabb.ccdd.eeff    Dynamic   1/1/48 trunk
        220  0011.2233.4455    Dynamic   1/1/20
        """

        entries = parse_mac_table(output, "AA:BB:CC:DD:EE:FF")

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].vlan_id, 201)
        self.assertEqual(entries[0].interface_name, "2/1/15")
        self.assertFalse(entries[0].is_trunk_candidate)
        self.assertTrue(entries[1].is_trunk_candidate)

    def test_parse_lldp_neighbors_collects_name_and_management_ip(self):
        output = """
        Local Port: 1/1/48
        System Name: IDF-01
        Management Address: 10.10.1.11
        """

        neighbors = parse_lldp_neighbors(output)

        self.assertEqual(neighbors[0].interface_name, "1/1/48")
        self.assertEqual(neighbors[0].neighbor_name, "IDF-01")
        self.assertEqual(neighbors[0].management_ip, "10.10.1.11")

    def test_parse_interface_trunk_status_requires_explicit_switchport_output(self):
        self.assertTrue(parse_interface_is_trunk("Switchport mode: trunk"))
        self.assertFalse(parse_interface_is_trunk("Port type: access"))
        self.assertIsNone(parse_interface_is_trunk("Interface is up"))

    def test_parse_port_name(self):
        self.assertEqual(
            parse_port_name("Port name: C2-CP_UPLNK_PT_IDF"),
            "C2-CP_UPLNK_PT_IDF",
        )
