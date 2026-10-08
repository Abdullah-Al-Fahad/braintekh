from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import Banner
from .serializers import BannerSerializer
from .responses import success_response
from django.db.models import Q

class BannerListView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        role = request.query_params.get('role')
        banners = Banner.objects.filter(is_active=True)
        
        if role:
            banners = banners.filter(Q(role__iexact=role) | Q(role=''))
            
        serializer = BannerSerializer(banners, many=True, context={'request': request})
        return success_response(data=serializer.data)
