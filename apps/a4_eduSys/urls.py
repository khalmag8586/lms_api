from django.urls import path

from apps.a4_eduSys.views import (
    EduSysCreateView,
    EduSysListView,
    EduSysDeletedListView,
    EduSysRetrieveView,
    EduSysDeleteTemporaryView,
    EduSysRestoreView,
    EduSysUpdateView,
    EduSysDeleteView,
    EduSysDialogView,
)

app_name = "edusystem"

urlpatterns = [
    path("edusys_create/", EduSysCreateView.as_view(), name="create edu sys"),
    path("edusys_list/", EduSysListView.as_view(), name="all edu sys"),
    path(
        "edusys_deleted_list/",
        EduSysDeletedListView.as_view(),
        name="all deleted edu sys",
    ),
    path("edusys_retrieve/", EduSysRetrieveView.as_view(), name="retrieve edu sys"),
    path(
        "edusys_temp_delete/",
        EduSysDeleteTemporaryView.as_view(),
        name="temp delete edu sys",
    ),
    path("edusys_restore/", EduSysRestoreView.as_view(), name="restore edu sys"),
    path("edusys_update/", EduSysUpdateView.as_view(), name="edu sys update"),
    path("edusys_delete/", EduSysDeleteView.as_view(), name="edu sys delete"),
    path("edusys_dialog/", EduSysDialogView.as_view(), name="edu sys dialog"),
]
