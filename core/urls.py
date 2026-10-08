from django.urls import path
from .views import BannerListView

app_name = 'core'

urlpatterns = [
    path('banners/', BannerListView.as_view(), name='banners-list'),
]
