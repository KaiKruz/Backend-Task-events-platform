from __future__ import annotations

from rest_framework import permissions

from accounts.models import AccountRole


class IsVerifiedSeeker(permissions.BasePermission):
    """
    Seeker role, email verified, and (for object checks on Enrollment) ownership.
    """

    message = "Only verified seekers may access this resource."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        profile = getattr(user, "account_profile", None)
        if profile is None:
            return False
        return profile.email_verified and profile.role == AccountRole.SEEKER

    def has_object_permission(self, request, view, obj) -> bool:
        from events.models import Enrollment

        if isinstance(obj, Enrollment):
            return obj.seeker_id == request.user.pk
        return True


class IsVerifiedFacilitator(permissions.BasePermission):
    message = "Only verified facilitators may access this resource."

    def has_permission(self, request, view) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        profile = getattr(user, "account_profile", None)
        if profile is None:
            return False
        return profile.email_verified and profile.role == AccountRole.FACILITATOR


class IsEventOwner(permissions.BasePermission):
    message = "You may only access events you created."

    def has_object_permission(self, request, view, obj) -> bool:
        return getattr(obj, "created_by_id", None) == request.user.pk
