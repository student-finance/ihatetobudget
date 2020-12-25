import unittest

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

not_implemented = unittest.skip("Not implemented")


class WithUserMixin:
    def setUp(self):
        self.user_credentials = user_credentials = dict(
            username="username", password="password"
        )
        User.objects.create_user(email="", **user_credentials)


# Requires WithUserMixin
class TestLoginRequiredMixin:
    def test_login_required(self):
        client = Client()
        self.assertEqual(
            client.get(reverse("index"), follow=True).redirect_chain, []
        )
        client.login(**self.user_credentials)
        self.assertEqual(
            client.get(reverse("index"), follow=True).redirect_chain,
            [(reverse("sheets:index"), 302)],
        )
