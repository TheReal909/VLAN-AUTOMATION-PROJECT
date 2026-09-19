from dataclasses import dataclass
from typing import Protocol

from inventory.models import Facility, Switch

from .parsers import (
    LldpNeighbor,
    MacTableEntry,
    parse_interface_is_trunk,
    parse_lldp_neighbors,
    parse_mac_table,
)


class DiscoveryError(Exception):
    """Raised when a switch cannot produce a safe discovery result."""


class ReadOnlySwitchConnector(Protocol):
    def find_mac(self, switch: Switch, mac_address: str) -> list[MacTableEntry]: ...

    def find_neighbors(self, switch: Switch) -> list[LldpNeighbor]: ...

    def is_trunk(self, switch: Switch, interface_name: str) -> bool | None: ...


class NetmikoReadOnlyConnector:
    def __init__(self, username: str, password: str, *, port: int = 22, timeout: int = 10):
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout

    def _send(self, switch: Switch, command: str) -> str:
        from netmiko import ConnectHandler

        try:
            connection = ConnectHandler(
                device_type="brocade_fastiron",
                host=switch.management_ip,
                username=self.username,
                password=self.password,
                port=self.port,
                conn_timeout=self.timeout,
                auth_timeout=self.timeout,
                banner_timeout=self.timeout,
            )
        except Exception as exc:
            raise DiscoveryError(f"Could not connect to {switch.name} for read-only discovery.") from exc
        try:
            return connection.send_command(command, read_timeout=self.timeout)
        except Exception as exc:
            raise DiscoveryError(f"Read-only discovery failed on {switch.name}.") from exc
        finally:
            connection.disconnect()

    def find_mac(self, switch: Switch, mac_address: str) -> list[MacTableEntry]:
        output = self._send(switch, f"show mac-address {mac_address}")
        return parse_mac_table(output, mac_address)

    def find_neighbors(self, switch: Switch) -> list[LldpNeighbor]:
        return parse_lldp_neighbors(self._send(switch, "show lldp neighbors detail"))

    def is_trunk(self, switch: Switch, interface_name: str) -> bool | None:
        return parse_interface_is_trunk(self._send(switch, f"show interfaces {interface_name}"))


@dataclass(frozen=True)
class DiscoveryResult:
    mac_address: str
    switch: Switch
    entry: MacTableEntry
    path: tuple[Switch, ...]


class MacDiscoveryService:
    def __init__(self, connector: ReadOnlySwitchConnector, *, max_hops: int = 8):
        if max_hops < 1:
            raise ValueError("max_hops must be at least 1")
        self.connector = connector
        self.max_hops = max_hops

    def locate(self, facility: Facility, mac_address: str) -> DiscoveryResult:
        switches = list(facility.switches.filter(is_active=True))
        current_switches = [switch for switch in switches if switch.closet_role == Switch.ClosetRole.MDF]
        if not current_switches:
            raise DiscoveryError(f"No active MDF switch is configured for facility {facility.code}.")

        visited: set[int] = set()
        path: list[Switch] = []
        current = current_switches[0]
        for _ in range(self.max_hops):
            if current.pk in visited:
                raise DiscoveryError("Discovery encountered a switch loop.")
            visited.add(current.pk)
            path.append(current)
            entries = self.connector.find_mac(current, mac_address)
            if not entries:
                raise DiscoveryError(f"MAC {mac_address} was not found on {current.name}.")

            endpoint_entries = []
            trunk_entries = []
            for entry in entries:
                is_trunk = self.connector.is_trunk(current, entry.interface_name)
                if is_trunk is True:
                    trunk_entries.append(entry)
                elif is_trunk is False:
                    endpoint_entries.append(entry)
            if not endpoint_entries and not trunk_entries:
                raise DiscoveryError(f"Could not verify the port role on {current.name}.")
            if len(endpoint_entries) == 1:
                return DiscoveryResult(mac_address, current, endpoint_entries[0], tuple(path))
            if len(endpoint_entries) > 1:
                raise DiscoveryError(f"MAC {mac_address} was found on multiple endpoint ports on {current.name}.")

            neighbor = self._resolve_neighbor(current, trunk_entries, facility, visited)
            if neighbor is None:
                raise DiscoveryError(f"No managed LLDP neighbor was found for {current.name}.")
            current = neighbor
        raise DiscoveryError(f"Discovery exceeded the {self.max_hops}-hop limit.")

    def _resolve_neighbor(
        self,
        current: Switch,
        entries: list[MacTableEntry],
        facility: Facility,
        visited: set[int],
    ) -> Switch | None:
        neighbors = self.connector.find_neighbors(current)
        trunk_interfaces = {entry.interface_name for entry in entries}
        candidates = [neighbor for neighbor in neighbors if neighbor.interface_name in trunk_interfaces]
        if len(candidates) != 1:
            return None
        neighbor = candidates[0]
        managed = list(facility.switches.filter(is_active=True).filter(
            management_ip=neighbor.management_ip
        )) if neighbor.management_ip else []
        if not managed:
            managed = [switch for switch in facility.switches.filter(is_active=True)
                       if switch.name.lower() == neighbor.neighbor_name.lower()
                       or switch.hostname.lower() == neighbor.neighbor_name.lower()]
        if len(managed) != 1 or managed[0].pk in visited:
            return None
        return managed[0]
