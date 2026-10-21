from rest_framework import serializers

from apps.households.models import Household, HouseholdInvite, HouseholdMembership


class MemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)

    class Meta:
        model = HouseholdMembership
        fields = ("id", "username", "first_name", "role", "joined_at")


class HouseholdSerializer(serializers.ModelSerializer):
    members = MemberSerializer(source="memberships", many=True, read_only=True)

    class Meta:
        model = Household
        fields = ("id", "name", "created_at", "members")


class InviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseholdInvite
        fields = ("id", "token", "expires_at", "used_at", "created_at")
        read_only_fields = fields
