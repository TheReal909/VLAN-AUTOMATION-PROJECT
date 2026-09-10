from django.test import SimpleTestCase


class HealthTests(SimpleTestCase):
    def test_root_route_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
