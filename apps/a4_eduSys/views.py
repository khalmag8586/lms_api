from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.exceptions import ValidationError

from rest_framework import status, generics
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.a4_eduSys.models import EduSystem
from apps.a4_eduSys.serializers import (
    EduSystemSerializer,
    EduSysIsDeletedSerializer,
    EduSysDialogSerializer,
)
from apps.a4_eduSys.filters import EduSysFilter

from lms_api.pagination import StandardResultsSetPagination
from lms_api.custom_permissions import HasPermissionOrInGroupWithPermission
from lms_api.utils import get_or_set_cache, cache_response, clear_cache_key

import uuid


class EduSysCreateView(generics.CreateAPIView):
    serializer_class = EduSystemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.add_edusystem"

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"detail": _("Educational System created successfully")},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(cache_page(60 * 10), name="dispatch")  # 10 mins
class EduSysListView(generics.ListAPIView):
    queryset = EduSystem.objects.filter(is_deleted=False).order_by("-created_at")
    serializer_class = EduSystemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.view_edusystem"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EduSysFilter
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
class EduSysDeletedListView(generics.ListAPIView):
    queryset = EduSystem.objects.filter(is_deleted=True).order_by("-created_at")
    serializer_class = EduSystemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.view_edusystem"
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EduSysFilter
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


class EduSysRetrieveView(generics.RetrieveAPIView):
    serializer_class = EduSystemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.view_edusystem"
    lookup_field = "id"

    def get_queryset(self):
        return EduSystem.objects.filter(is_deleted=False)

    def get_object(self):
        edusys_id = self.request.query_params.get("edusys_id")
        cache_key = f"user_detail_{edusys_id}"
        return get_or_set_cache(
            cache_key,
            lambda: get_object_or_404(self.get_queryset(), id=edusys_id),
            timeout=300,
        )


class EduSysDeleteTemporaryView(generics.UpdateAPIView):
    serializer_class = EduSysIsDeletedSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.delete_edusystem"

    def update(self, request, *args, **kwargs):
        edusys_ids = request.data.get("edusys_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == False:
            return Response(
                {"detail": _("These educational systems are not deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for edusys_id in edusys_ids:
            instance = get_object_or_404(EduSystem, id=edusys_id)
            if instance.is_deleted:
                return Response(
                    {
                        "detail": _(
                            "Edu sys with ID {} is already temp deleted".format(
                                edusys_id
                            )
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            clear_cache_key(f"edusys_detail_{edusys_id}")

        return Response(
            {"detail": _("Educational Systems temp deleted successfully")},
            status=status.HTTP_200_OK,
        )


class EduSysRestoreView(generics.RetrieveUpdateAPIView):

    serializer_class = EduSysIsDeletedSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.delete_edusystem"

    def update(self, request, *args, **kwargs):
        edusys_ids = request.data.get("edusys_id", [])
        partial = kwargs.pop("partial", False)
        is_deleted = request.data.get("is_deleted")

        if is_deleted == True:
            return Response(
                {"detail": _("Educational system are already deleted")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for edusys_id in edusys_ids:
            instance = get_object_or_404(EduSystem, id=edusys_id)
            if instance.is_deleted == False:
                return Response(
                    {
                        "detail": _(
                            "Educational system with ID {} is not deleted".format(
                                edusys_id
                            )
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            clear_cache_key(f"edusystem_detail_{edusys_id}")

        return Response(
            {"detail": _("Educational System restored successfully")},
            status=status.HTTP_200_OK,
        )


class EduSysUpdateView(generics.UpdateAPIView):
    serializer_class = EduSystemSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.change_edusystem"
    lookup_field = "id"

    def get_object(self):
        edusys_id = self.request.query_params.get("edusys_id")
        edusys = get_object_or_404(EduSystem, id=edusys_id)
        return edusys

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        clear_cache_key(f"edusystem_detail_{instance.id}")

        return Response(
            {"detail": _("Educational Systems Updated successfully")},
            status=status.HTTP_200_OK,
        )


class EduSysDeleteView(generics.DestroyAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPermissionOrInGroupWithPermission]
    permission_codename = "a4_eduSys.delete_edusystem"
    import uuid

    def delete(self, request, format=None):
        # data = JSONParser().parse(request)
        edusys_ids = request.data.get("edusys_id", [])
        import uuid

        if not edusys_ids:
            return Response(
                {"detail": _("No educational system IDs provided for deletion")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if each UUID is valid
        for uid in edusys_ids:
            clear_cache_key(f"edusystem_detail_{uid}")

            try:
                uuid.UUID(uid.strip())
            except ValueError:
                raise ValidationError(_("'{}' is not a valid UUID.".format(uid)))

        edusyses = EduSystem.objects.filter(id__in=edusys_ids)
        if not edusyses.exists():
            return Response(
                {"detail": _("No educational system found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        edusyses.delete()

        return Response(
            {"detail": _("Educational systems permanently deleted successfully")},
            status=status.HTTP_204_NO_CONTENT,
        )


class EduSysDialogView(generics.ListAPIView):
    serializer_class = EduSysDialogSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = EduSystem.objects.filter(is_deleted=False).order_by("-created_at")
