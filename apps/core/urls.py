from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EnvironmentVariableViewSet,
    EnvironmentViewSet,
    RandomDataGenerateView,
    RandomDataProvidersView,
    RandomDataView,
)

router = DefaultRouter()
router.register('environments', EnvironmentViewSet, basename='environment')
router.register('environment-variables', EnvironmentVariableViewSet, basename='environment-variable')

urlpatterns = [
    path('', include(router.urls)),
    path('random-data/', RandomDataView.as_view(), name='random-data'),
    path('random-data/generate/', RandomDataGenerateView.as_view(), name='random-data-generate'),
    path('random-data/providers/', RandomDataProvidersView.as_view(), name='random-data-providers'),
]
