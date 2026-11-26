from django.urls import path
from .views import (
    LinkCreateView, redirect_view, LinkInfoView,
    LinkDeactivateView, LinkDeleteView, LoginView
)

urlpatterns = [
    path('api/links/', LinkCreateView.as_view(), name='link-create'),
    path('api/links/<str:short_code>/', LinkInfoView.as_view(), name='link-info'),
    path('api/links/<str:short_code>/deactivate/', LinkDeactivateView.as_view(), name='link-deactivate'),
    path('api/links/<str:short_code>/delete/', LinkDeleteView.as_view(), name='link-delete'),
    path('s/<str:short_code>/', redirect_view, name='redirect'),
    path('api/login/', LoginView.as_view(), name='api_login')
]
