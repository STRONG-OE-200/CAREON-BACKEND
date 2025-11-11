from django.urls import path
from .views import RoomMetricsListCreateView, RoomMetricDetailView,RoomLogsListCreateView, LogDetailView, RoomChartsView

urlpatterns = [
    path("rooms/<int:room_id>/metrics/", RoomMetricsListCreateView.as_view(), name="room-metrics"),
    path("rooms/<int:room_id>/metrics/<int:metric_id>/", RoomMetricDetailView.as_view(), name="room-metric-detail"),
    path("rooms/<int:room_id>/logs/", RoomLogsListCreateView.as_view(), name="room-logs"),
    path("logs/<int:log_id>/", LogDetailView.as_view(), name="log-detail"),
    path("rooms/<int:room_id>/charts/", RoomChartsView.as_view(), name="room-charts"),
]
