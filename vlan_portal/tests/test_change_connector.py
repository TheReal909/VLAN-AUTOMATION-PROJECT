from unittest.mock import patch

from django.test import SimpleTestCase

from changes.connectors import FastIronVlanChangeConnector


class FastIronVlanChangeConnectorTests(SimpleTestCase):
    @patch("netmiko.ConnectHandler")
    def test_apply_sends_confirmed_fastiron_commands_without_write_memory(self, connect):
        connection = connect.return_value
        connection.send_config_set.return_value = (
            "Added untagged port(s) ethe 1/1/6 to port-vlan 1."
        )
        connector = FastIronVlanChangeConnector("writer", "secret")
        change = self._change(target_vlan=1)

        connector.apply(change)

        connection.send_config_set.assert_called_once_with(
            ["interface ethernet 1/1/6", "vlan-config move untagged 1"],
            exit_config_mode=False,
        )
        self.assertNotIn("write memory", str(connection.send_config_set.call_args).lower())
        connection.disconnect.assert_called_once()

    @patch("netmiko.ConnectHandler")
    def test_verify_requires_requested_untagged_vlan(self, connect):
        connection = connect.return_value
        connection.send_command.return_value = """
        Port 1/1/6 is a member of 2 VLANs
        VLANs 1 300
        Untagged VLAN   : 1
        Tagged VLANs    : 300
        """
        connector = FastIronVlanChangeConnector("writer", "secret")
        change = self._change(target_vlan=1)

        self.assertTrue(connector.verify(change))
        connection.send_command.assert_called_once_with(
            "show vlan brief ethernet 1/1/6",
            read_timeout=10,
        )

    @staticmethod
    def _change(target_vlan):
        class Vlan:
            vlan_id = target_vlan

        class Switch:
            management_ip = "192.0.2.10"

        class Change:
            interface_name = "1/1/6"
            requested_vlan = Vlan()
            switch = Switch()

        return Change()
