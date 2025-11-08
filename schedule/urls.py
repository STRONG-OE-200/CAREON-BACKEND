from django.urls import path
from .views import ScheduleReadCreateView, ScheduleNeededSubmitView, ScheduleAvailabilitySubmitView, ScheduleAvailabilityMembersView,ScheduleImportPreviousView, ScheduleFinalizeView, ScheduleHistoryView
urlpatterns = [
    path("schedules/", ScheduleReadCreateView.as_view(), name="schedule-read-create"),
    path("schedules/<int:week_id>/needed/", ScheduleNeededSubmitView.as_view(), name="schedule-needed-submit"),
    path("schedules/<int:week_id>/availability/", ScheduleAvailabilitySubmitView.as_view(), name="schedule-availability-submit"),
    path("schedules/<int:week_id>/availability/members/", ScheduleAvailabilityMembersView.as_view(), name="schedule-availability-members"),
    path("schedules/<int:week_id>/finalize/", ScheduleFinalizeView.as_view(), name="schedule-finalize"),
    path("schedules/<int:week_id>/import_previous/",ScheduleImportPreviousView.as_view(),name="schedule-import-previous"),
    path("schedules/history", ScheduleHistoryView.as_view(), name="schedule-history"),
]