from .models import *
from rest_framework import serializers


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "preview_image",
            "version",
            "is_active",
        ]


class ShopThemeSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopThemeSettings
        fields = [
            "primary_color",
            "secondary_color",
            "logo",
            "banner_image",
            "font_family",
        ]


class ShopSerializer(serializers.ModelSerializer):
    theme = ThemeSerializer(read_only=True)

    theme_id = serializers.PrimaryKeyRelatedField(
        queryset=Theme.objects.all(),
        source="theme",
        write_only=True,
        required=False,
    )

    theme_settings = ShopThemeSettingsSerializer(read_only=True)

    class Meta:
        model = Shop
        fields = [
            "id",
            "name",
            "description",
            "domain",
            "created_at",
            "theme",
            "theme_id",
            "theme_settings",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        if getattr(request.user, "owned_shop", None):
            raise serializers.ValidationError("Shop owner already has a shop.")

        shop = Shop.objects.create(owner=request.user, **validated_data)
        ShopThemeSettings.objects.create(shop=shop)
        return shop
