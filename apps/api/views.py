from datetime import datetime

from django.http import Http404
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.week import monday_of
from apps.households.models import HouseholdInvite
from apps.households.permissions import HasHousehold, household_from_request
from apps.households.serializers import HouseholdSerializer, InviteSerializer
from apps.households.services import InviteError, accept_invite, create_invite
from apps.meal_plans.selectors import get_plan_for_week, list_history
from apps.meal_plans.serializers import MealPlanSerializer
from apps.meal_plans.services.generator import (
    ApprovedPlanProtectedError,
    InsufficientRecipesError,
    generate_week_menu,
)
from apps.meal_plans.services.planning import (
    PlanningError,
    approve_plan,
    change_entry,
)
from apps.preferences.models import RecipePreference
from apps.preferences.selectors import preferences_for_user
from apps.preferences.serializers import RecipePreferenceSerializer
from apps.recipes.models import Recipe
from apps.recipes.selectors import recipes_for_household, search_recipes
from apps.recipes.serializers import RecipeSerializer


def parse_week(value):
    try:
        return monday_of(datetime.strptime(value, "%Y-%m-%d").date())
    except (TypeError, ValueError) as exc:
        raise Http404("week_start debe ser AAAA-MM-DD.") from exc


def parse_day(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise Http404("day debe ser AAAA-MM-DD.") from exc


class RecipeListCreateView(APIView):
    permission_classes = [HasHousehold]

    def get(self, request):
        household = household_from_request(request)
        qs = search_recipes(
            household,
            query=request.query_params.get("q", ""),
            category=request.query_params.get("category", ""),
            sort=request.query_params.get("sort", "name"),
            include_archived=request.query_params.get("archived") == "1",
        )
        return Response(RecipeSerializer(qs, many=True).data)

    def post(self, request):
        household = household_from_request(request)
        serializer = RecipeSerializer(data=request.data, context={"household": household})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecipeDetailView(APIView):
    permission_classes = [HasHousehold]

    def get_recipe(self, request, pk):
        household = household_from_request(request)
        try:
            return recipes_for_household(household).get(pk=pk)
        except Recipe.DoesNotExist as exc:
            raise Http404("Receta no encontrada.") from exc

    def get(self, request, pk):
        recipe = self.get_recipe(request, pk)
        return Response(RecipeSerializer(recipe).data)

    def patch(self, request, pk):
        household = household_from_request(request)
        recipe = self.get_recipe(request, pk)
        serializer = RecipeSerializer(
            recipe, data=request.data, partial=True, context={"household": household}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MealPlanDetailView(APIView):
    permission_classes = [HasHousehold]

    def get(self, request, week_start):
        household = household_from_request(request)
        plan = get_plan_for_week(household, parse_week(week_start))
        if plan is None:
            return Response({"detail": "Sin menú para esa semana."}, status=404)
        return Response(MealPlanSerializer(plan).data)


class MealPlanGenerateView(APIView):
    permission_classes = [HasHousehold]

    def post(self, request, week_start):
        household = household_from_request(request)
        start = parse_week(week_start)
        confirm = bool(request.data.get("confirm_replace"))
        seed = request.data.get("seed")
        try:
            plan = generate_week_menu(
                household,
                start,
                request.user,
                seed=seed,
                confirm_replace=confirm,
            )
        except ApprovedPlanProtectedError as exc:
            return Response({"detail": str(exc)}, status=409)
        except InsufficientRecipesError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(MealPlanSerializer(plan).data)


class MealPlanEntryView(APIView):
    permission_classes = [HasHousehold]

    def patch(self, request, week_start, day):
        household = household_from_request(request)
        recipe_id = request.data.get("recipe_id")
        try:
            recipe = recipes_for_household(household).get(pk=recipe_id)
        except Recipe.DoesNotExist as exc:
            raise Http404("Receta no encontrada.") from exc
        try:
            change_entry(household, parse_week(week_start), parse_day(day), recipe)
        except PlanningError as exc:
            return Response({"detail": str(exc)}, status=400)
        plan = get_plan_for_week(household, parse_week(week_start))
        return Response(MealPlanSerializer(plan).data)


class MealPlanApproveView(APIView):
    permission_classes = [HasHousehold]

    def post(self, request, week_start):
        household = household_from_request(request)
        try:
            plan = approve_plan(household, parse_week(week_start))
        except PlanningError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(MealPlanSerializer(plan).data)


class MealPlanHistoryView(APIView):
    permission_classes = [HasHousehold]

    def get(self, request):
        household = household_from_request(request)
        plans = list_history(household)
        return Response(MealPlanSerializer(plans, many=True).data)


class PreferenceListView(APIView):
    permission_classes = [HasHousehold]

    def get(self, request):
        household = household_from_request(request)
        qs = preferences_for_user(request.user, household)
        return Response(RecipePreferenceSerializer(qs, many=True).data)

    def post(self, request):
        household = household_from_request(request)
        serializer = RecipePreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipe = serializer.validated_data["recipe"]
        if recipe.household_id != household.id:
            return Response({"detail": "La receta no pertenece a tu hogar."}, status=403)
        pref, _created = RecipePreference.objects.update_or_create(
            user=request.user,
            recipe=recipe,
            defaults={
                "rating": serializer.validated_data.get("rating"),
                "is_favorite": serializer.validated_data.get("is_favorite", False),
                "is_avoided": serializer.validated_data.get("is_avoided", False),
            },
        )
        return Response(RecipePreferenceSerializer(pref).data)


class HouseholdView(APIView):
    permission_classes = [HasHousehold]

    def get(self, request):
        household = household_from_request(request)
        return Response(HouseholdSerializer(household).data)

    def patch(self, request):
        household = household_from_request(request)
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": ["Indica un nombre."]}, status=400)
        household.name = name
        household.save(update_fields=["name"])
        return Response(HouseholdSerializer(household).data)


class InvitationView(APIView):
    permission_classes = [HasHousehold]

    def get(self, request):
        household = household_from_request(request)
        invites = HouseholdInvite.objects.filter(household=household).order_by("-created_at")[:10]
        payload = InviteSerializer(invites, many=True).data
        for item in payload:
            item["url"] = request.build_absolute_uri(
                reverse("households:accept_invite", args=[item["token"]])
            )
        return Response(payload)

    def post(self, request):
        household = household_from_request(request)
        membership = request.membership
        if membership.role != membership.Role.OWNER:
            return Response({"detail": "Solo la persona propietaria puede invitar."}, status=403)
        invite = create_invite(household, request.user)
        data = InviteSerializer(invite).data
        data["url"] = request.build_absolute_uri(
            reverse("households:accept_invite", args=[invite.token])
        )
        return Response(data, status=201)


class InvitationAcceptView(APIView):
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Inicia sesión."}, status=401)
        token = request.data.get("token")
        try:
            household = accept_invite(request.user, token)
        except InviteError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(HouseholdSerializer(household).data)
