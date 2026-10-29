from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.households.models import HouseholdInvite, HouseholdMembership
from apps.households.services import (
    InviteError,
    accept_invite,
    create_household_for_user,
    create_invite,
)


class HouseholdTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("allan", password="clave-segura-1")
        self.member = User.objects.create_user("naiara", password="clave-segura-1")
        self.outsider = User.objects.create_user("otro", password="clave-segura-1")
        self.household = create_household_for_user(self.owner, "Casa Allan y Naiara")

    def test_unique_membership(self):
        with self.assertRaises(Exception):
            HouseholdMembership.objects.create(
                household=self.household,
                user=self.owner,
                role=HouseholdMembership.Role.MEMBER,
            )

    def test_invite_flow(self):
        invite = create_invite(self.household, self.owner)
        accept_invite(self.member, invite.token)
        self.assertTrue(
            HouseholdMembership.objects.filter(
                household=self.household, user=self.member
            ).exists()
        )
        with self.assertRaises(InviteError):
            accept_invite(self.outsider, invite.token)

    def test_expired_invite(self):
        invite = HouseholdInvite.issue(self.household, self.owner, ttl_days=7)
        invite.expires_at = timezone.now() - timedelta(hours=1)
        invite.save()
        with self.assertRaises(InviteError):
            accept_invite(self.member, invite.token)

    def test_active_invite_can_be_copied(self):
        create_invite(self.household, self.owner)
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get("/hogar/")
        self.assertContains(response, "Copiar enlace")
        self.assertContains(response, 'id="invite-url"')

    def test_invite_signup_asks_only_for_the_account(self):
        invite = create_invite(self.household, self.owner)
        page = self.client.get(f"/cuentas/registro/?token={invite.token}")
        self.assertContains(page, f"Únete a {self.household.name}")
        self.assertContains(page, 'class="auth-actions"')
        self.assertContains(page, "Usuario")
        self.assertContains(page, "Contraseña")
        self.assertContains(page, "Correo")
        self.assertNotContains(page, "Nombre del hogar")
        self.assertNotContains(page, "Repetir contraseña")
        self.assertNotContains(page, ">Nombre<")
        self.assertNotContains(page, "150 car")
        response = self.client.post(
            "/cuentas/registro/",
            {
                "username": "invitada",
                "password1": "clave-segura-1",
                "email": "invitada@example.com",
                "invite_token": invite.token,
            },
        )
        self.assertRedirects(response, "/inicio/")
        user = User.objects.get(username="invitada")
        self.assertTrue(user.check_password("clave-segura-1"))
        self.assertEqual(user.email, "invitada@example.com")
        self.assertTrue(
            HouseholdMembership.objects.filter(
                household=self.household, user=user
            ).exists()
        )

    def test_short_invite_password_explains_why(self):
        invite = create_invite(self.household, self.owner)
        response = self.client.post(
            "/cuentas/registro/",
            {
                "username": "mario",
                "password1": "mario",
                "invite_token": invite.token,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "demasiado corta")
        self.assertContains(response, 'role="alert"')
        self.assertFalse(User.objects.filter(username="mario").exists())

    def test_settings_requires_login(self):
        response = self.client.get("/hogar/")
        self.assertEqual(response.status_code, 302)

    def test_member_cannot_see_other_household_settings_data(self):
        other_user = User.objects.create_user("vecino", password="clave-segura-1")
        other_home = create_household_for_user(other_user, "Otra casa")
        self.client.login(username="allan", password="clave-segura-1")
        response = self.client.get("/hogar/")
        self.assertContains(response, "Casa Allan y Naiara")
        self.assertNotContains(response, other_home.name)
