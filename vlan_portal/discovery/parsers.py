import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MacTableEntry:
    mac_address: str
    vlan_id: int
    interface_name: str
    is_trunk_candidate: bool


@dataclass(frozen=True)
class LldpNeighbor:
    interface_name: str
    neighbor_name: str
    management_ip: str | None


_MAC_PATTERN = r"(?P<mac>[0-9a-fA-F]{2}(?:[:-]?[0-9a-fA-F]{2}){5}|[0-9a-fA-F]{4}(?:[.-][0-9a-fA-F]{4}){2})"
_INTERFACE_PATTERN = r"(?P<interface>\d+/\d+/\d+|\d+/\d+|Trunk\d+|Port-channel\d+)"


def normalize_mac(value: str) -> str:
    compact = re.sub(r"[^0-9a-fA-F]", "", value)
    if len(compact) != 12 or not re.fullmatch(r"[0-9a-fA-F]{12}", compact):
        raise ValueError(f"Invalid MAC address: {value}")
    return ":".join(compact[index:index + 2].lower() for index in range(0, 12, 2))


def parse_mac_table(output: str, mac_address: str) -> list[MacTableEntry]:
    target = normalize_mac(mac_address)
    entries = []
    for line in output.splitlines():
        mac_match = re.search(_MAC_PATTERN, line)
        interface_match = re.search(_INTERFACE_PATTERN, line, re.IGNORECASE)
        if not mac_match or not interface_match:
            continue
        try:
            normalized = normalize_mac(mac_match.group("mac"))
        except ValueError:
            continue
        if normalized != target:
            continue
        vlan_match = re.search(r"\b(?:vlan\s+)?(?P<vlan>\d{1,4})\b", line, re.IGNORECASE)
        if not vlan_match:
            continue
        interface_name = interface_match.group("interface")
        entries.append(
            MacTableEntry(
                mac_address=normalized,
                vlan_id=int(vlan_match.group("vlan")),
                interface_name=interface_name,
                is_trunk_candidate=bool(re.search(r"trunk|port-channel", line, re.IGNORECASE)),
            )
        )
    return entries


def parse_lldp_neighbors(output: str) -> list[LldpNeighbor]:
    neighbors = []
    current_interface = None
    current_name = None
    current_ip = None
    for line in output.splitlines():
        interface_match = re.search(r"(?:Local Port|Local Intf|Interface)\s*[:：]\s*(\S+)", line, re.IGNORECASE)
        name_match = re.search(r"(?:System Name|Neighbor|Chassis Name)\s*[:：]\s*(\S+)", line, re.IGNORECASE)
        ip_match = re.search(r"(?:Management Address|Management IP|IP address)\s*[:：]\s*(\d{1,3}(?:\.\d{1,3}){3})", line, re.IGNORECASE)
        if interface_match:
            if current_interface and current_name:
                neighbors.append(LldpNeighbor(current_interface, current_name, current_ip))
            current_interface = interface_match.group(1)
            current_name = None
            current_ip = None
        if name_match:
            current_name = name_match.group(1)
        if ip_match:
            current_ip = ip_match.group(1)
    if current_interface and current_name:
        neighbors.append(LldpNeighbor(current_interface, current_name, current_ip))
    return neighbors


def parse_interface_is_trunk(output: str) -> bool | None:
    normalized = output.lower()
    if re.search(r"\b(?:tagging|port type|switchport mode)\s*[:：]?\s*(?:tagged|trunk)", normalized):
        return True
    if re.search(r"\b(?:tagging|port type|switchport mode)\s*[:：]?\s*(?:untagged|access)", normalized):
        return False
    return None
