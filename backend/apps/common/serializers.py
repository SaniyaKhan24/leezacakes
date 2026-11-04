from rest_framework import serializers


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("ok", "unavailable"))


class SiteConfigSerializer(serializers.Serializer):
    business_name = serializers.CharField(allow_null=True)
    contact_phone = serializers.CharField(allow_null=True)
    contact_email = serializers.CharField(allow_null=True)
    whatsapp = serializers.CharField(allow_null=True)
    whatsapp_link_number = serializers.CharField(
        allow_null=True, help_text="Digits-only E.164 number for https://wa.me/<number> links."
    )
    instagram = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True)
    pickup_hours_label = serializers.CharField(allow_null=True)
    currency = serializers.CharField()
    timezone = serializers.CharField()
    is_sample = serializers.BooleanField()


class SiteConfigEnvelopeSerializer(serializers.Serializer):
    data = SiteConfigSerializer()
