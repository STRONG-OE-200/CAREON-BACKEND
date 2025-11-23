from django.urls import path

from .views import RoomEventListCreateAPIView, EventDetailAPIView

urlpatterns = [
    # /rooms/{room_id}/calendar/events
    path(
        "rooms/<int:room_id>/calendar/events",
        RoomEventListCreateAPIView.as_view(),
        name="room-calendar-events",
    ),
    # /calendar/events/{event_id}
    path(
        "calendar/events/<int:event_id>",
        EventDetailAPIView.as_view(),
        name="calendar-event-detail",
    ),
]
