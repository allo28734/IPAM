"""
Service-layer tests for SSO user provisioning and role syncing.

Verifies handle_sso_login correctly:
  1. Auto-provisions new users with the correct role.
  2. Syncs existing user roles on every login.
  3. Leaves passwords untouched for existing users.
"""

from unittest.mock import patch

import pytest

from app.models.user import User
from app.services.auth_service import handle_sso_login, verify_password


# ── New user provisioning ──────────────────────────────────────


class TestSSONewUser:
    """Tests for auto-provisioning new users via SSO."""

    def test_new_user_with_admin_group(self, db):
        """A new user whose groups contain the admin group gets role='admin'."""
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.sso_admin_group = "ipam-admins"

            user = handle_sso_login(
                db,
                email="admin@corp.com",
                username="admin.user",
                user_groups=["ipam-admins", "all-users"],
            )

        assert user.id is not None
        assert user.username == "admin.user"
        assert user.email == "admin@corp.com"
        assert user.role == "admin"
        assert user.is_active is True

    def test_new_user_without_admin_group(self, db):
        """A new user without the admin group gets role='readonly'."""
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.sso_admin_group = "ipam-admins"

            user = handle_sso_login(
                db,
                email="viewer@corp.com",
                username="viewer.user",
                user_groups=["all-users"],
            )

        assert user.role == "readonly"

    def test_new_user_no_admin_group_configured(self, db):
        """When sso_admin_group is None, every user gets 'readonly'."""
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.sso_admin_group = None

            user = handle_sso_login(
                db,
                email="anyone@corp.com",
                username="anyone",
                user_groups=["ipam-admins"],
            )

        assert user.role == "readonly"

    def test_new_user_has_impossible_password(self, db):
        """Auto-provisioned users have a bcrypt hash that cannot be guessed."""
        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.sso_admin_group = None

            user = handle_sso_login(
                db, email="sso@corp.com", username="sso_user", user_groups=[]
            )

        # The hash is valid bcrypt, but no common password matches it
        assert user.hashed_password.startswith("$2b$")
        assert not verify_password("password", user.hashed_password)


# ── Existing user role syncing ─────────────────────────────────


class TestSSORoleSync:
    """Tests for syncing roles on existing users."""

    def _seed_user(self, db, role="readonly"):
        """Helper: insert a user with the given role."""
        from app.services.auth_service import hash_password

        user = User(
            username="existing.user",
            email="existing@corp.com",
            hashed_password=hash_password("original-password"),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_existing_readonly_gains_admin(self, db):
        """A readonly user who now has the admin group is promoted."""
        original = self._seed_user(db, role="readonly")
        original_password = original.hashed_password

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.sso_admin_group = "ipam-admins"

            user = handle_sso_login(
                db,
                email="existing@corp.com",
                username="existing.user",
                user_groups=["ipam-admins"],
            )

        assert user.id == original.id
        assert user.role == "admin"
        # Password must not change
        assert user.hashed_password == original_password

    def test_existing_admin_loses_admin(self, db):
        """An admin who no longer has the admin group is demoted."""
        self._seed_user(db, role="admin")

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.sso_admin_group = "ipam-admins"

            user = handle_sso_login(
                db,
                email="existing@corp.com",
                username="existing.user",
                user_groups=["all-users"],
            )

        assert user.role == "readonly"

    def test_existing_user_password_untouched(self, db):
        """SSO login never modifies the existing user's password hash."""
        original = self._seed_user(db, role="admin")
        original_hash = original.hashed_password

        with patch("app.services.auth_service.settings") as mock_settings:
            mock_settings.sso_admin_group = "ipam-admins"

            user = handle_sso_login(
                db,
                email="existing@corp.com",
                username="existing.user",
                user_groups=["ipam-admins"],
            )

        assert user.hashed_password == original_hash
