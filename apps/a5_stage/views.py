from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.exceptions import ValidationError

from rest_framework import generics, status
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.a5_stage.models import Stage
from apps.a5_stage.serializers import (
    StageSerializer,
    StageDeletedSerializer,
    StageDialogSerializer,
)
from apps.a5_stage.filters import StageFilter

from lms_api.pagination import StandardResultsSetPagination
from lms_api.custom_permissions import HasPermissionOrInGroupWithPermission
from lms_api.utils import get_or_set_cache, cache_response, clear_cache_key


class StageCreateView(generics.CreateAPIView):
    serializer_class = StageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.add_stage"

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"detail": _("Stage created successfully")})


@method_decorator(cache_page(60 * 10), name="dispatch")  # 10 mins
class StageListView(generics.ListAPIView):
    queryset = Stage.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = StageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.view_stage"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StageFilter
    search_fields = [
        "name",
        "name_ar",
    ]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


@method_decorator(cache_page(60 * 10), name="dispatch")  # 10 mins
class StageDeletedListView(generics.ListAPIView):
    queryset = Stage.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = StageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.view_stage"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = StageFilter
    search_fields = [
        "name",
        "name_ar",
    ]
    ordering_fields = [
        "name",
        "-name",
        "name_ar",
        "-name_ar",
        "created_at",
        "-created_at",
    ]


class StageRetrieveView(generics.RetrieveAPIView):
    serializer_class = StageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.view_stage"
    lookup_field = "id"

    def get_queryset(self):
        return Stage.objects.filter(is_deleted=False)

    def get_object(self):
        stage_id = self.request.query_params.get("stage_id")
        cache_key = f"stage_detail_{stage_id}"
        return get_or_set_cache(
            cache_key,
            lambda: get_object_or_404(self.get_queryset(), id=stage_id),
            timeout=300,
        )


class StageDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = StageDeletedSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.delete_stage"

    def update(self, request, *args, **kwargs):
        stage_ids = request.data.get("stage_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These stages are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for stage_id in stage_ids:
            instance = get_object_or_404(Stage, id=stage_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "Stage with ID {} is already temp deleted".format(stage_id)
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            clear_cache_key(f"stage_detail_{stage_id}")

        return Response(
            {"detail": _("Stage temp deleted successfully")},
            status=status.HTTP_200_OK,
        )


class StageRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = StageDeletedSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.delete_stage"

    def update(self, request, *args, **kwargs):
        stage_ids = request.data.get("stage_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("Stages are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for stage_id in stage_ids:
            instance = get_object_or_404(Stage, id=stage_id)
            if instance.is_deleted == False:
                return Response(
                    {"detail": _("Stages with ID {} is not deleted".format(stage_id))},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            clear_cache_key(f"stage_detail_{stage_id}")

        return Response(
            {"detail": _("Stages restored successfully")},
            status=status.HTTP_200_OK,
        )


class StageUpdateView(generics.UpdateAPIView):
    serializer_class = StageSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.change_stage"
    lookup_field = "id"

    def get_object(self):
        stage_id = self.request.query_params.get("stage_id")
        stage = get_object_or_404(Stage, id=stage_id)
        return stage

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        clear_cache_key(f"stage_detail_{instance.id}")

        return Response(
            {"detail": _("Stage Updated successfully")},
            status=status.HTTP_200_OK,
        )


class StageDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a5_stage.delete_stage"
    import uuid

    def delete(self, request, format=None):
        # data = JSONParser().parse(request)
        stage_ids = request.data.get("stage_id", [])
        import uuid

        if not stage_ids:
            return Response(
                {"detail": _("No stage IDs provided for deletion")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if each UUID is valid
        for uid in stage_ids:
            clear_cache_key(f"stage_detail_{uid}")

            try:
                uuid.UUID(uid.strip())
            except ValueError:
                raise ValidationError(_("'{}' is not a valid UUID.".format(uid)))

        stages = Stage.objects.filter(id__in=stage_ids)
        if not stages.exists():
            return Response(
                {"detail": _("No stage found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        stages.delete()

        return Response(
            {"detail": _("Stages permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class StageDialogView(generics.ListAPIView):
    serializer_class = StageDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Stage.objects.filter(is_deleted=False).order_by("-created_at")
