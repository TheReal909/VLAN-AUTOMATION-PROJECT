import re

from changes.models import VlanChangeLog


class FastIronVlanChangeConnector:
    """Apply and verify an access-port VLAN change on a FastIron switch."""

    def __init__(self, username: str, password: str, *, port: int = 22, timeout: int = 10):
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout

    def _connect(self, change: VlanChangeLog):
        from netmiko import ConnectHandler

        return ConnectHandler(
            device_type="brocade_fastiron",
            host=change.switch.management_ip,
            username=self.username,
            password=self.password,
            port=self.port,
            conn_timeout=self.timeout,
            auth_timeout=self.timeout,
            banner_timeout=self.timeout,
        )

    def apply(self, change: VlanChangeLog) -> None:
        connection = self._connect(change)
        try:
            output = connection.send_config_set(
                [
                    f"interface ethernet {change.interface_name}",
                    f"vlan-config move untagged {change.requested_vlan.vlan_id}",
                ],
                exit_config_mode=False,
            )
            if "Added untagged port" not in output:
                raise RuntimeError("Switch did not confirm the untagged VLAN move.")
        finally:
            connection.disconnect()

    def verify(self, change: VlanChangeLog) -> bool:
        connection = self._connect(change)
        try:
            output = connection.send_command(
                f"show vlan brief ethernet {change.interface_name}",
                read_timeout=self.timeout,
            )
        finally:
            connection.disconnect()
        match = re.search(r"Untagged VLAN\s*:\s*(\d+)", output, re.IGNORECASE)
        return bool(match and int(match.group(1)) == change.requested_vlan.vlan_id)
