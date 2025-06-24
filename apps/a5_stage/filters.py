import django_filters
from django_filters import FilterSet, OrderingFilter

from apps.a5_stage.models import Stage


class StageFilter(FilterSet):
    ordering = OrderingFilter(
        fields=(
            ("name", "name"),  # Ascending order by name
            ("-name", "name_desc"),  # Descending order by name
            ("name_ar", "name_ar"),  # Ascending order by name_ar
            ("-name_ar", "name_ar_desc"),  # Descending order by name_ar
        ),
        field_labels={
            "name": "Name (ascending)",
            "name_desc": "Name (descending)",
            "name_ar": "Name (Arabic ascending)",
            "name_ar_desc": "Name (Arabic descending)",
        },
    )

    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    name_ar = django_filters.CharFilter(field_name="name_ar", lookup_expr="icontains")

    class Meta:
        model = Stage
        fields = ["name", "name_ar"]
