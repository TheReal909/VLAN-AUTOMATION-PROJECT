from tempfile import TemporaryDirectory
from pathlib import Path
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from inventory.models import Facility, Switch


class ImportSwitchInventoryTests(TestCase):
    def _make_workbook(self, path: Path):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "combined inventory"
        sheet.append([
            "facility_code", "facility_name", "facility_status", "address", "city", "state", "zip",
            "switch_name", "hostname", "management_ip", "model_family", "fastiron_version",
            "closet_role", "upstream_switch", "solarwinds_location",
        ])
        common = ["F12345", "Test Facility", "Active", "1 Example Way", "Test City", "UT", "84000"]
        sheet.append(common + ["MDF-01", "mdf-01.example.test", "192.0.2.101", "ICX7150", "10.0", "mdf", "", "F12345"])
        sheet.append(common + ["IDF-01", "idf-01.example.test", "192.0.2.102", "ICX7150", "10.0", "idf", "", "F12345"])
        sheet.append(common + ["IDF-02", "idf-02.example.test", "192.0.2.103", "ICX7150", "10.0", "idf", "", "F12345"])
        workbook.save(path)

    def test_default_is_dry_run_and_apply_imports_selected_topology(self):
        with TemporaryDirectory() as directory:
            workbook_path = Path(directory) / "inventory.xlsx"
            self._make_workbook(workbook_path)

            call_command(
                "import_switch_inventory",
                workbook_path,
                "--facility",
                "F12345",
                stdout=StringIO(),
            )
            self.assertEqual(Facility.objects.count(), 0)

            call_command(
                "import_switch_inventory",
                workbook_path,
                "--facility",
                "F12345",
                "--apply",
                stdout=StringIO(),
            )

        self.assertEqual(Facility.objects.get(code="F12345").switches.count(), 3)
        self.assertEqual(Switch.objects.filter(facility__code="F12345", closet_role=Switch.ClosetRole.MDF).count(), 1)
        self.assertEqual(Switch.objects.filter(facility__code="F12345", closet_role=Switch.ClosetRole.IDF).count(), 2)
