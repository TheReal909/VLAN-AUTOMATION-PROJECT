from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from inventory.models import Facility, Switch


class SwitchCleanTests(SimpleTestCase):
    def setUp(self):
        self.facility = Facility(code="F19114", name="Test facility")
        self.mdf = Switch(
            pk=1,
            facility=self.facility,
            name="MDF-01",
            hostname="mdf-01.example.test",
            management_ip="192.0.2.1",
            closet_role=Switch.ClosetRole.MDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )

    def test_idf_can_point_to_another_idf_that_points_to_mdf(self):
        idf_01 = Switch(
            pk=2,
            facility=self.facility,
            name="IDF-01",
            hostname="idf-01.example.test",
            management_ip="192.0.2.2",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=self.mdf,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        idf_02 = Switch(
            pk=3,
            facility=self.facility,
            name="IDF-02",
            hostname="idf-02.example.test",
            management_ip="192.0.2.3",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=idf_01,
            model_family=Switch.ModelFamily.ICX_7150,
        )

        idf_02.clean()

    def test_idf_upstream_hierarchy_cannot_contain_a_cycle(self):
        idf_01 = Switch(
            pk=2,
            facility=self.facility,
            name="IDF-01",
            hostname="idf-01.example.test",
            management_ip="192.0.2.2",
            closet_role=Switch.ClosetRole.IDF,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        idf_02 = Switch(
            pk=3,
            facility=self.facility,
            name="IDF-02",
            hostname="idf-02.example.test",
            management_ip="192.0.2.3",
            closet_role=Switch.ClosetRole.IDF,
            upstream_switch=idf_01,
            model_family=Switch.ModelFamily.ICX_7150,
        )
        idf_01.upstream_switch = idf_02

        with self.assertRaisesMessage(ValidationError, "cannot contain a cycle"):
            idf_02.clean()
