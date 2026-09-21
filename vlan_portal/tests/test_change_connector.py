from unittest.mock import patch

from django.test import SimpleTestCase

from changes.connectors import FastIronVlanChangeConnector


class FastIronVlanChangeConnectorTests(SimpleTestCase):
    @patch("netmiko.ConnectHandler")
    def test_apply_uses_legacy_vlan_context_sequence_by_default(self, connect):
        connection = connect.return_value
        connection.send_config_set.return_value = (
            "Added untagged port(s) ethe 1/1/6 to port-vlan 1."
        )
        connector = FastIronVlanChangeConnector("writer", "secret")
        change = self._change(target_vlan=1)

        connector.apply(change)

        connection.send_config_set.assert_called_once_with(
            [
                "interface ethernet 1/1/6",
                "exit",
                "vlan 201",
                "no untagged ethernet 1/1/6",
                "vlan 1",
                "untagged ethernet 1/1/6",
                "end",
            ],
            exit_config_mode=False,
        )
        self.assertNotIn("write memory", str(connection.send_config_set.call_args).lower())
        connection.disconnect.assert_called_once()

    @patch("netmiko.ConnectHandler")
    def test_move_sequence_is_explicit_opt_in(self, connect):
        connection = connect.return_value
        connection.send_config_set.return_value = "Added untagged port(s) ethe 1/1/6 to port-vlan 1."
        connector = FastIronVlanChangeConnector("writer", "secret", command_mode="move")

        connector.apply(self._change(target_vlan=1))

        self.assertEqual(
            connection.send_config_set.call_args.args[0],
            ["interface ethernet 1/1/6", "vlan-config move untagged 1"],
        )

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
            previous_vlan = type("PreviousVlan", (), {"vlan_id": 201})()
            requested_vlan = Vlan()
            switch = Switch()

        return Change()
