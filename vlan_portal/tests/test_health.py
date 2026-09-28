from django.test import SimpleTestCase


class HealthTests(SimpleTestCase):
    def test_root_route_redirects_anonymous_users_to_login(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/accounts/login/?next=/", fetch_redirect_response=False)
