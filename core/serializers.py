from rest_framework import serializers
from .models import Banner

class BannerSerializer(serializers.ModelSerializer):
    bg_gradient = serializers.SerializerMethodField()

    class Meta:
        model = Banner
        fields = [
            'id', 'title', 'subtitle', 'tag', 'bg_gradient',
            'image', 'action_text', 'action_url', 'target_project_id'
        ]

    def get_bg_gradient(self, obj):
        return [obj.bg_gradient_start, obj.bg_gradient_end]
