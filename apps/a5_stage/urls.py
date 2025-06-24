from django.urls import path

from apps.a5_stage.views import (
    StageCreateView,
    StageListView,
    StageDeletedListView,
    StageRetrieveView,
    StageDeleteTemporaryView,
    StageRestoreView,
    StageUpdateView,
    StageDeleteView,
    StageDialogView,
)

app_name = "stage"

urlpatterns = [
    path("stage_create/", StageCreateView.as_view(), name="stage create"),
    path("stage_list/", StageListView.as_view(), name="stage list"),
    path(
        "stage_deleted_list/", StageDeletedListView.as_view(), name="stage deleted list"
    ),
    path("stage_retrieve/", StageRetrieveView.as_view(), name="stage retrieve"),
    path(
        "stage_temp_delete/",
        StageDeleteTemporaryView.as_view(),
        name="temp delete stage",
    ),
    path("stage_restore/", StageRestoreView.as_view(), name="stage restore"),
    path("stage_update/", StageUpdateView.as_view(), name="stage update"),
    path("stage_delete/", StageDeleteView.as_view(), name="stage delete"),
    path("stage_dialog/", StageDialogView.as_view(), name="stage dialog"),
]
