from django.urls import path
from .views import WeekScheduleCreateView, NeededBulkView

urlpatterns = [
    path("", WeekScheduleCreateView.as_view(), name="week-schedule-create"),
    path("<int:week_id>/needed/", NeededBulkView.as_view(), name="needed-bulk"),
]
