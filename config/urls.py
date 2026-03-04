from django.contrib import admin
from django.urls import include, path

from .views import ApiToolView, AsyncRunsView, DataGeneratorView, DiffView, FormatterView, HomeView, StressView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('formatter/', FormatterView.as_view(), name='formatter-page'),
    path('diff/', DiffView.as_view(), name='diff-page'),
    path('api/', ApiToolView.as_view(), name='api-page'),
    path('stress/', StressView.as_view(), name='stress-page'),
    path('data/', DataGeneratorView.as_view(), name='data-page'),
    path('runs/', AsyncRunsView.as_view(), name='runs-page'),
    path('admin/', admin.site.urls),
    path('api/core/', include('apps.core.urls')),
    path('api/formatter/', include('apps.formatter.urls')),
    path('api/client/', include('apps.api_client.urls')),
]
