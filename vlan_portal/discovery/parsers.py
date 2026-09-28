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
    device_type: str | None = None

    @property
    def is_endpoint(self) -> bool:
        return bool(self.device_type and "endpoint class" in self.device_type.lower())


_MAC_PATTERN = r"(?P<mac>[0-9a-fA-F]{2}(?:[:-]?[0-9a-fA-F]{2}){5}|[0-9a-fA-F]{4}(?:[.-][0-9a-fA-F]{4}){2})"
_INTERFACE_PATTERN = r"(?P<interface>\d+/\d+/\d+|\d+/\d+|Trunk\d+|Port-channel\d+)"


def normalize_mac(value: str) -> str:
    compact = re.sub(r"[^0-9a-fA-F]", "", value)
    if len(compact) != 12 or not re.fullmatch(r"[0-9a-fA-F]{12}", compact):
        raise ValueError(f"Invalid MAC address: {value}")
    compact = compact.lower()
    return ".".join(compact[index:index + 4] for index in range(0, 12, 4))


def mac_address_variants(value: str) -> set[str]:
    normalized = normalize_mac(value)
    compact = normalized.replace(".", "")
    return {
        normalized,
        normalized.lower(),
        ":".join(compact[index:index + 2] for index in range(0, 12, 2)),
        ":".join(compact[index:index + 2].lower() for index in range(0, 12, 2)),
        "-".join(compact[index:index + 2] for index in range(0, 12, 2)),
        "-".join(compact[index:index + 2].lower() for index in range(0, 12, 2)),
        compact,
        compact.lower(),
    }


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
        tokens = line.split()
        mac_index = next(
            (index for index, token in enumerate(tokens) if _token_is_mac(token, target)),
            None,
        )
        interface_index = next(
            (index for index, token in enumerate(tokens) if token == interface_match.group("interface")),
            None,
        )
        if mac_index is None or interface_index is None:
            continue
        numeric_tokens = []
        for index, token in enumerate(tokens):
            if index in {mac_index, interface_index}:
                continue
            if re.fullmatch(r"\d{1,4}", token):
                value = int(token)
                if 1 <= value <= 4094:
                    numeric_tokens.append((index, value))
        preceding_vlan = [item for item in numeric_tokens if item[0] < mac_index]
        following_vlan = [item for item in numeric_tokens if item[0] > max(mac_index, interface_index)]
        if preceding_vlan:
            vlan_id = preceding_vlan[-1][1]
        elif following_vlan:
            vlan_id = following_vlan[-1][1]
        elif len(numeric_tokens) == 1:
            vlan_id = numeric_tokens[0][1]
        else:
            continue
        interface_name = interface_match.group("interface")
        entries.append(
            MacTableEntry(
                mac_address=normalized,
                vlan_id=vlan_id,
                interface_name=interface_name,
                is_trunk_candidate=bool(re.search(r"trunk|port-channel", line, re.IGNORECASE)),
            )
        )
    return entries


def _token_is_mac(token: str, target: str) -> bool:
    try:
        return normalize_mac(token) == target
    except ValueError:
        return False


def parse_lldp_neighbors(output: str) -> list[LldpNeighbor]:
    neighbors = []
    current_interface = None
    current_name = None
    current_ip = None
    current_device_type = None
    for line in output.splitlines():
        interface_match = re.search(r"(?:Local Port|Local Intf|Interface)\s*[:：]\s*(\S+)", line, re.IGNORECASE)
        name_match = re.search(r"(?:System Name|Neighbor|Chassis Name)\s*[:：]\s*(\S+)", line, re.IGNORECASE)
        ip_match = re.search(r"(?:Management Address|Management IP|IP address)\s*[:：]\s*(\d{1,3}(?:\.\d{1,3}){3})", line, re.IGNORECASE)
        device_type_match = re.search(r"MED device type\s*[:：]\s*(.+?)\s*$", line, re.IGNORECASE)
        if interface_match:
            if current_interface and current_name:
                neighbors.append(
                    LldpNeighbor(current_interface, current_name, current_ip, current_device_type)
                )
            current_interface = interface_match.group(1)
            current_name = None
            current_ip = None
            current_device_type = None
        if name_match:
            current_name = name_match.group(1)
        if ip_match:
            current_ip = ip_match.group(1)
        if device_type_match:
            current_device_type = device_type_match.group(1).strip()
    if current_interface and current_name:
        neighbors.append(LldpNeighbor(current_interface, current_name, current_ip, current_device_type))
    return neighbors


def parse_interface_is_trunk(output: str) -> bool | None:
    normalized = output.lower()
    if re.search(r"\b(?:tagging|port type|switchport mode)\s*[:：]?\s*(?:tagged|trunk)", normalized):
        return True
    if re.search(r"\b(?:tagging|port type|switchport mode)\s*[:：]?\s*(?:untagged|access)", normalized):
        return False
    return None


def parse_port_name(output: str) -> str:
    match = re.search(r"(?:Port name|Port Name|Name)\s*[:：]\s*(.*\S)\s*$", output, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""
