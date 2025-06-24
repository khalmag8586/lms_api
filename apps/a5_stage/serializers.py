from rest_framework import serializers

from apps.a5_stage.models import Stage


class StageSerializer(serializers.ModelSerializer):
    edu_system_name = serializers.CharField(source="edu_system.name", read_only=True)
    edu_system_name_ar = serializers.CharField(
        source="edu_system.name_ar", read_only=True
    )
    created_by_user_name = serializers.CharField(
        source="created_by.name", read_only=True
    )
    created_by_user_name_ar = serializers.CharField(
        source="created_by.name_ar", read_only=True
    )
    updated_by_user_name = serializers.CharField(
        source="updated_by.name", read_only=True
    )
    updated_by_user_name_ar = serializers.CharField(
        source="updated_by.name_ar", read_only=True
    )
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Stage
        fields = [
            "id",
            "name",
            "name_ar",
            "description",
            "edu_system",
            "edu_system_name",
            "edu_system_name_ar",
            "is_active",
            "created_by",
            "created_by_user_name",
            "created_by_user_name_ar",
            "created_at",
            "updated_by",
            "updated_by_user_name",
            "updated_by_user_name_ar",
            "updated_at",
        ]

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d")

    def get_updated_at(self, obj):
        return obj.updated_at.strftime("%Y-%m-%d")


class StageDeletedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ["id", "is_deleted"]
        read_only_fields = ["id"]


class StageDialogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stage
        fields = ["id", "name", "name_ar"]
        read_only_fields = ["id"]
