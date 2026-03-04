from django.urls import path

from .views import DiffPayloadView, FormatPayloadView

urlpatterns = [
    path('format/', FormatPayloadView.as_view(), name='format-payload'),
    path('diff/', DiffPayloadView.as_view(), name='diff-payload'),
]
