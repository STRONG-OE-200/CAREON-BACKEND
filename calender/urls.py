from django.urls import path

from .views import RoomEventListCreateAPIView, EventDetailAPIView, FileUploadAPIView

urlpatterns = [
    # /rooms/{room_id}/calendar/events
    path(
        "rooms/<int:room_id>/calender/events",
        RoomEventListCreateAPIView.as_view(),
        name="room-calender-events",
    ),
    # /calendar/events/{event_id}
    path(
        "calender/events/<int:event_id>",
        EventDetailAPIView.as_view(),
        name="calendar-event-detail",
    ),
    path(
        "files/upload",
        FileUploadAPIView.as_view(),
        name="file-upload",
    ),
]
