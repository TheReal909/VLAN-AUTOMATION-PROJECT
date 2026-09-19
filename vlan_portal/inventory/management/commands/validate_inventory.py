import ipaddress
import re
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from inventory.models import Switch, VlanProfile


class Command(BaseCommand):
    help = "Validate an inventory workbook without changing the database."

    def add_arguments(self, parser):
        parser.add_argument("workbook", type=Path, help="Path to the inventory XLSX workbook.")

    def handle(self, *args, **options):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise CommandError("Install openpyxl before validating XLSX files.") from exc

        workbook_path = options["workbook"]
        if not workbook_path.is_file():
            raise CommandError(f"Workbook not found: {workbook_path}")

        workbook = load_workbook(workbook_path, read_only=True, data_only=True)
        if "combined inventory" not in workbook.sheetnames:
            raise CommandError("Workbook must contain a 'combined inventory' sheet.")

        errors = []
        warnings = []
        switch_rows = self._read_switch_rows(workbook["combined inventory"], errors)
        self._validate_switch_rows(switch_rows, errors)

        vlan_rows = []
        if "VLAN Profiles" in workbook.sheetnames:
            vlan_rows = self._read_vlan_rows(workbook["VLAN Profiles"], errors)
            self._validate_vlan_rows(vlan_rows, warnings)
        else:
            warnings.append("Workbook has no 'VLAN Profiles' sheet.")

        self.stdout.write(f"Workbook: {workbook_path}")
        self.stdout.write(f"Switch rows checked: {len(switch_rows)}")
        self.stdout.write(f"VLAN profiles checked: {len(vlan_rows)}")
        self.stdout.write(f"Blocking errors: {len(errors)}")
        self.stdout.write(f"Warnings: {len(warnings)}")
        for message in errors:
            self.stdout.write(self.style.ERROR(f"ERROR: {message}"))
        for message in warnings:
            self.stdout.write(self.style.WARNING(f"WARNING: {message}"))

        if errors:
            raise CommandError("Validation failed; no database changes were made.")
        self.stdout.write(self.style.SUCCESS("Validation passed; no database changes were made."))

    @staticmethod
    def _read_switch_rows(sheet, errors):
        rows = []
        header = next(sheet.iter_rows(values_only=True), None)
        if not header:
            errors.append("'combined inventory' is empty.")
            return rows
        headers = [str(value).strip() if value is not None else "" for value in header]
        required = {
            "facility_code", "facility_name", "switch_name", "hostname", "management_ip",
            "model_family", "closet_role", "upstream_switch",
        }
        missing = sorted(required - set(headers))
        if missing:
            errors.append(f"'combined inventory' is missing columns: {', '.join(missing)}")
            return rows
        indexes = {name: headers.index(name) for name in required}
        for row_number, values in enumerate(sheet.iter_rows(values_only=True), 2):
            record = {name: values[index] if index < len(values) else None for name, index in indexes.items()}
            if (
                str(record["switch_name"] or "").strip().lower() in {"caption", "switch_name"}
                or str(record["management_ip"] or "").strip().lower() in {"ip address", "management_ip"}
                or str(record["upstream_switch"] or "").strip().lower() == "upstream_switch"
            ):
                continue
            if not any(value not in (None, "") for value in record.values()):
                continue
            record["row_number"] = row_number
            rows.append(record)
        return rows

    @staticmethod
    def _validate_switch_rows(rows, errors):
        names = Counter()
        hostnames = Counter()
        addresses = Counter()
        valid_roles = {choice[0] for choice in Switch.ClosetRole.choices}
        valid_families = {choice[0] for choice in Switch.ModelFamily.choices}
        code_pattern = re.compile(r"^F\d{5}$")

        for row in rows:
            line = row["row_number"]
            facility_code = str(row["facility_code"] or "").strip().upper()
            switch_name = str(row["switch_name"] or "").strip()
            hostname = str(row["hostname"] or "").strip().lower()
            address = str(row["management_ip"] or "").strip()
            role = str(row["closet_role"] or "").strip().lower()
            family = str(row["model_family"] or "").strip().upper()
            upstream = str(row["upstream_switch"] or "").strip()
            names[(facility_code, switch_name)] += 1
            hostnames[hostname] += 1
            addresses[address] += 1

            if not code_pattern.fullmatch(facility_code):
                errors.append(f"row {line}: invalid facility_code '{facility_code}'.")
            if not switch_name:
                errors.append(f"row {line}: switch_name is required.")
            if not hostname:
                errors.append(f"row {line}: hostname is required.")
            try:
                ipaddress.ip_address(address)
            except ValueError:
                errors.append(f"row {line}: invalid management_ip '{address}'.")
            if role not in valid_roles:
                errors.append(f"row {line}: closet_role must be MDF or IDF, got '{role}'.")
            if family not in valid_families:
                errors.append(f"row {line}: unsupported model_family '{family}'.")
            if upstream and upstream == switch_name:
                errors.append(f"row {line}: switch cannot be its own upstream_switch.")

        for key, count in names.items():
            if count > 1:
                errors.append(f"duplicate switch name in facility: {key[0]} / {key[1]} ({count} rows).")
        for value, count in hostnames.items():
            if value and count > 1:
                errors.append(f"duplicate hostname: {value} ({count} rows).")
        for value, count in addresses.items():
            if value and count > 1:
                errors.append(f"duplicate management_ip: {value} ({count} rows).")

        switch_names = {(str(row["facility_code"]).strip().upper(), str(row["switch_name"]).strip()) for row in rows}
        for row in rows:
            upstream = str(row["upstream_switch"] or "").strip()
            if upstream and (str(row["facility_code"]).strip().upper(), upstream) not in switch_names:
                errors.append(
                    f"row {row['row_number']}: upstream_switch '{upstream}' was not found in the same facility."
                )

    @staticmethod
    def _read_vlan_rows(sheet, errors):
        rows = []
        header_row = None
        for row_number, values in enumerate(sheet.iter_rows(values_only=True), 1):
            normalized = [str(value).strip() if value is not None else "" for value in values]
            if "profile_key" in normalized:
                header_row = (row_number, normalized)
                break
        if header_row is None:
            errors.append("'VLAN Profiles' has no profile_key header row.")
            return rows
        row_number, headers = header_row
        indexes = {name: headers.index(name) for name in headers if name}
        required = {"profile_key", "helpdesk_label", "vlan_id", "assignment_mode", "allow_helpdesk_port_change"}
        missing = sorted(required - set(indexes))
        if missing:
            errors.append(f"'VLAN Profiles' is missing columns: {', '.join(missing)}")
            return rows
        for current_row, values in enumerate(sheet.iter_rows(min_row=row_number + 1, values_only=True), row_number + 1):
            if not any(value not in (None, "") for value in values):
                continue
            rows.append({name: values[index] if index < len(values) else None for name, index in indexes.items()})
        return rows

    @staticmethod
    def _validate_vlan_rows(rows, warnings):
        valid_modes = {choice[0] for choice in VlanProfile.AssignmentMode.choices}
        for row in rows:
            try:
                vlan_id = int(row["vlan_id"])
            except (TypeError, ValueError):
                warnings.append(f"VLAN profile '{row.get('profile_key')}': invalid vlan_id.")
                continue
            mode = str(row["assignment_mode"] or "").strip().lower()
            allowed = str(row["allow_helpdesk_port_change"] or "").strip().lower() in {"yes", "true", "1"}
            if not 1 <= vlan_id <= 4094:
                warnings.append(f"VLAN profile '{row.get('profile_key')}': VLAN ID {vlan_id} is outside 1-4094.")
            if mode not in valid_modes:
                warnings.append(f"VLAN profile '{row.get('profile_key')}': unsupported assignment_mode '{mode}'.")
            if vlan_id == 1 and not allowed:
                warnings.append("VLAN 1: source sheet says manual changes are disabled; project policy overrides this to allowed.")