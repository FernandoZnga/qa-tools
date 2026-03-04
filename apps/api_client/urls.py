from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApiRequestTemplateViewSet,
    ApiRunLogViewSet,
    LoadTestRunViewSet,
    LoadTestScenarioViewSet,
    RunLoadTestAsyncView,
    RunLoadTestView,
    SendApiRequestView,
)

router = DefaultRouter()
router.register('templates', ApiRequestTemplateViewSet, basename='api-template')
router.register('run-logs', ApiRunLogViewSet, basename='api-run-log')
router.register('load-scenarios', LoadTestScenarioViewSet, basename='load-scenario')
router.register('load-runs', LoadTestRunViewSet, basename='load-run')

urlpatterns = [
    path('', include(router.urls)),
    path('send/', SendApiRequestView.as_view(), name='api-send'),
    path('load-test/run/', RunLoadTestView.as_view(), name='load-test-run'),
    path('load-test/run-async/', RunLoadTestAsyncView.as_view(), name='load-test-run-async'),
]
