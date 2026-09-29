from django.test import SimpleTestCase

from unittest.mock import patch

from django.test import SimpleTestCase

from discovery.connectors import NetmikoReadOnlyConnector
from discovery.parsers import normalize_mac, parse_interface_is_trunk, parse_lldp_neighbors, parse_mac_table, parse_port_name


class DiscoveryParserTests(SimpleTestCase):
    def test_normalize_mac_accepts_common_formats(self):
        self.assertEqual(normalize_mac("a8:3c:a5:34:a1:28"), "a83c.a534.a128")
        self.assertEqual(normalize_mac("a83c.a534.a128"), "a83c.a534.a128")
        self.assertEqual(normalize_mac("A83C.A534.A128"), "a83c.a534.a128")
        self.assertEqual(normalize_mac("AC71.2EDF.1092"), "ac71.2edf.1092")

    def test_parse_mac_table_finds_endpoint_and_trunk_entries(self):
        output = """
        VLAN MAC Address       Type      Port
        201  aabb.ccdd.eeff    Dynamic   2/1/15
        201  aabb.ccdd.eeff    Dynamic   1/1/48 trunk
        220  0011.2233.4455    Dynamic   1/1/20
        """

        entries = parse_mac_table(output, "aa:bb:cc:dd:ee:ff")

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].vlan_id, 201)
        self.assertEqual(entries[0].mac_address, "aabb.ccdd.eeff")
        self.assertEqual(entries[0].interface_name, "2/1/15")
        self.assertFalse(entries[0].is_trunk_candidate)
        self.assertTrue(entries[1].is_trunk_candidate)

    def test_parse_mac_table_does_not_take_vlan_from_numeric_mac_group(self):
        output = """
        MAC-Address     Port     Type       VLAN
        fc5c.4530.165f  2/1/21   Dynamic    1
        """

        entries = parse_mac_table(output, "fc5c.4530.165f")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].vlan_id, 1)
        self.assertEqual(entries[0].interface_name, "2/1/21")

    def test_parse_lldp_neighbors_collects_name_and_management_ip(self):
        output = """
        Local Port: 1/1/48
        System Name: IDF-01
        Management Address: 10.10.1.11
        + MED device type : Bridge, switch
        """

        neighbors = parse_lldp_neighbors(output)

        self.assertEqual(neighbors[0].interface_name, "1/1/48")
        self.assertEqual(neighbors[0].neighbor_name, "IDF-01")
        self.assertEqual(neighbors[0].management_ip, "10.10.1.11")
        self.assertEqual(neighbors[0].device_type, "Bridge, switch")
        self.assertFalse(neighbors[0].is_endpoint)

    def test_parse_lldp_endpoint_class(self):
        output = """
        Local port: 1/1/5
          Neighbor: a83c.a534.a128, TTL 2706 seconds
          + MED device type : Endpoint Class I
        """

        neighbor = parse_lldp_neighbors(output)[0]

        self.assertTrue(neighbor.is_endpoint)
        self.assertEqual(neighbor.device_type, "Endpoint Class I")

    def test_parse_interface_trunk_status_requires_explicit_switchport_output(self):
        self.assertTrue(parse_interface_is_trunk("Switchport mode: trunk"))
        self.assertFalse(parse_interface_is_trunk("Port type: access"))
        self.assertIsNone(parse_interface_is_trunk("Interface is up"))

    def test_parse_port_name(self):
        self.assertEqual(
            parse_port_name("Port name: C2-CP_UPLNK_PT_IDF"),
            "C2-CP_UPLNK_PT_IDF",
        )

    @patch.object(NetmikoReadOnlyConnector, "_send")
    def test_switch_command_uses_lowercase_dotted_mac(self, send):
        send.return_value = "201 a83c.a534.a128 Dynamic 2/1/15"
        switch = type("Switch", (), {"name": "MDF-01"})()
        connector = NetmikoReadOnlyConnector("reader", "secret")

        entries = connector.find_mac(switch, "a8:3c:a5:34:a1:28")

        send.assert_called_once_with(switch, "show mac-address a83c.a534.a128")
        self.assertEqual(entries[0].mac_address, "a83c.a534.a128")

    @patch.object(NetmikoReadOnlyConnector, "_send")
    def test_interface_description_uses_fastiron_ethernet_keyword(self, send):
        send.return_value = "Port name: C2-CP_UPLNK_PT_IDF"
        switch = type("Switch", (), {"name": "MDF-01"})()
        connector = NetmikoReadOnlyConnector("reader", "secret")

        port_name = connector.find_port_name(switch, "1/2/2")

        send.assert_called_once_with(switch, "show interfaces ethernet 1/2/2")
        self.assertEqual(port_name, "C2-CP_UPLNK_PT_IDF")

    @patch("netmiko.ConnectHandler")
    def test_each_read_command_opens_and_closes_its_own_ssh_session(self, connect):
        connection = connect.return_value
        connection.send_command.side_effect = [
            "1 a83c.a534.a128 2/1/5",
            "Local port: 1/1/48\nNeighbor: IDF-01, TTL 30 seconds",
            "Port name: C2-CP_UPLNK_PT_IDF",
        ]
        switch = type("Switch", (), {"pk": 42, "name": "MDF-01", "management_ip": "192.0.2.10"})()
        connector = NetmikoReadOnlyConnector("reader", "secret")

        connector.find_mac(switch, "a83c.a534.a128")
        connector.find_neighbors(switch)
        connector.find_port_name(switch, "1/1/48")

        self.assertEqual(connect.call_count, 3)
        self.assertEqual(connection.send_command.call_count, 3)
        self.assertEqual(connection.disconnect.call_count, 3)
