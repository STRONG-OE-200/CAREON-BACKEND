from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from collections import defaultdict

from room.models import Room, RoomMembership
from room.permissions import IsRoomOwner, IsRoomMemberOrOwner
from .models import *
from .serializers import *


class ScheduleReadCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ScheduleCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        room = get_object_or_404(Room, id=ser.validated_data["room_id"])
        if not IsRoomOwner().has_object_permission(request, self, room):
            return Response({"detail": "이 방에 스케줄을 생성할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        try:
            with transaction.atomic():
                schedule = ser.save()
        except IntegrityError:
            return Response({"detail": "이미 동일한 주차 스케줄이 존재합니다."}, status=status.HTTP_409_CONFLICT)
        out = ScheduleResponseSerializer(schedule).data
        return Response(out, status=status.HTTP_201_CREATED)

    def get(self, request):
        qser = ScheduleQuerySerializer(data=request.query_params)
        qser.is_valid(raise_exception=True)
        room_id = qser.validated_data["room_id"]
        week = qser.validated_data.get("week")
        only = qser.validated_data.get("only")
        expand = qser.validated_data.get("expand")

        room = get_object_or_404(Room, id=room_id)
        if not IsRoomMemberOrOwner().has_object_permission(request, self, room):
            return Response({"detail": "이 방의 스케줄을 조회할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        start_date, end_date = compute_sunday_range_from_week(week)
        schedule = Schedule.objects.filter(room_id=room_id, start_date=start_date).first()

        base = {
            "room_id": room_id,
            "week_id": schedule.id if schedule else None,
            "week_range": [start_date.isoformat(), end_date.isoformat()],
            "status": schedule.status if schedule else "none",
            "is_owner": (room.owner_id == request.user.id),
        }

        if expand == "meta":
            base["meta"] = {
                "updated_at": (schedule.finalized_at or schedule.created_at).isoformat() if schedule else None,
            }
            return Response(ScheduleReadResponseSerializer(base).data, status=status.HTTP_200_OK)

        def empty_cell():
            if only is None:
                return {"isCareNeeded": False, "availableMembers": [], "confirmedMember": None}
            if only == "needed":
                return {"isCareNeeded": False}
            if only == "availability":
                return {"availableMembers": []}
            if only == "confirmed":
                return {"confirmedMember": None}

        grid = [[empty_cell() for _ in range(24)] for _ in range(7)]

        if schedule:
            if only is None or only == "needed":
                for ns in ScheduleNeededSlot.objects.filter(schedule=schedule).only("day", "hour", "needed"):
                    if "isCareNeeded" in grid[ns.day][ns.hour]:
                        grid[ns.day][ns.hour]["isCareNeeded"] = bool(ns.needed)

            if only is None or only == "availability":
                qs = (ScheduleAvailabilitySlot.objects
                      .filter(schedule=schedule)
                      .select_related("user")
                      .only("day", "hour", "user__id", "user__name", "available"))
                buckets = defaultdict(list)
                for a in qs:
                    if a.available:
                        buckets[(a.day, a.hour)].append({
                            "id": a.user_id,
                            "name": getattr(a.user, "name", str(a.user_id))
                        })
                for (d, h), members in buckets.items():
                    if "availableMembers" in grid[d][h]:
                        grid[d][h]["availableMembers"] = members

            if only is None or only == "confirmed":
                qs = (ScheduleConfirmedAssignment.objects
                      .filter(schedule=schedule)
                      .select_related("assignee")
                      .only("day", "hour", "assignee_id", "assignee__name"))
                for ca in qs:
                    if "confirmedMember" in grid[ca.day][ca.hour]:
                        cm = None
                        if ca.assignee_id:
                            cm = {"id": ca.assignee_id, "name": getattr(ca.assignee, "name", str(ca.assignee_id))}
                        grid[ca.day][ca.hour]["confirmedMember"] = cm

        base["masterGrid"] = grid
        base["meta"] = {
            "updated_at": (schedule.finalized_at or schedule.created_at).isoformat() if schedule else None,
        }
        return Response(ScheduleReadResponseSerializer(base).data, status=status.HTTP_200_OK)


class ScheduleNeededSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, week_id: int):
        schedule = get_object_or_404(Schedule, id=week_id)
        room = schedule.room
        if not IsRoomOwner().has_object_permission(request, self, room):
            return Response({"detail": "이 스케줄을 수정할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        if schedule.status == "finalized":
            return Response({"detail": "이미 확정된 스케줄은 수정할 수 없습니다."}, status=status.HTTP_409_CONFLICT)

        ser = ScheduleNeededSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        slots = ser.validated_data["slots"]

        with transaction.atomic():
            ScheduleNeededSlot.objects.filter(schedule=schedule).delete()
            ScheduleNeededSlot.objects.bulk_create([
                ScheduleNeededSlot(schedule=schedule, day=item["day"], hour=item["hour"], needed=True)
                for item in slots
            ])

        return Response(
            {"schedule_id": schedule.id, "submitted_slots": len(slots), "status": schedule.status},
            status=status.HTTP_200_OK,
        )


class ScheduleAvailabilitySubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, week_id: int):
        schedule = get_object_or_404(Schedule, id=week_id)
        room = schedule.room
        if not IsRoomMemberOrOwner().has_object_permission(request, self, room):
            return Response({"detail": "이 스케줄을 수정할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        if schedule.status == "finalized":
            return Response({"detail": "이미 확정된 스케줄은 수정할 수 없습니다."}, status=status.HTTP_409_CONFLICT)
        if ScheduleAvailabilitySubmission.objects.filter(schedule=schedule, user=request.user).exists():
            sub = ScheduleAvailabilitySubmission.objects.get(schedule=schedule, user=request.user)
            return Response(
                {"detail": f"이미 제출을 완료했습니다. submitted_at={sub.submitted_at.isoformat()}"},
                status=status.HTTP_409_CONFLICT,
            )

        ser = ScheduleAvailabilitySubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        slots = ser.validated_data["slots"]

        try:
            with transaction.atomic():
                ScheduleAvailabilitySlot.objects.filter(schedule=schedule, user=request.user).delete()
                ScheduleAvailabilitySlot.objects.bulk_create([
                    ScheduleAvailabilitySlot(
                        schedule=schedule,
                        user=request.user,
                        day=item["day"],
                        hour=item["hour"],
                        available=True,
                    )
                    for item in slots
                ])
                ScheduleAvailabilitySubmission.objects.create(schedule=schedule, user=request.user)
        except IntegrityError:
            return Response(
                {"detail": "동시에 제출이 시도되어 충돌이 발생했습니다. 다시 시도해 주세요."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {"schedule_id": schedule.id, "user_id": request.user.id, "submitted_slots": len(slots), "status": schedule.status},
            status=status.HTTP_200_OK,
        )


class ScheduleAvailabilityMembersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, week_id: int):
        schedule = get_object_or_404(Schedule, id=week_id)
        room = schedule.room
        if not IsRoomMemberOrOwner().has_object_permission(request, self, room):
            return Response({"detail": "이 스케줄을 조회할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        members, seen = [], set()
        owner = room.owner
        if owner and owner.id not in seen:
            members.append(owner)
            seen.add(owner.id)
        for m in RoomMembership.objects.filter(room=room).select_related("user").only("user__id", "user__name"):
            if m.user_id not in seen:
                members.append(m.user)
                seen.add(m.user_id)

        user_ids = [u.id for u in members]

        sub_qs = (ScheduleAvailabilitySubmission.objects
                  .filter(schedule=schedule, user_id__in=user_ids)
                  .values("user_id", "submitted_at"))
        submitted_at_map = {row["user_id"]: row["submitted_at"] for row in sub_qs}

        cnt_qs = (ScheduleAvailabilitySlot.objects
                  .filter(schedule=schedule, user_id__in=user_ids, available=True)
                  .values("user_id").annotate(cnt=Count("id")))
        count_map = {row["user_id"]: row["cnt"] for row in cnt_qs}

        data_members = []
        for u in members:
            row = {"id": u.id, "name": getattr(u, "name", None), "submitted": u.id in submitted_at_map}
            if row["submitted"]:
                row["submitted_at"] = submitted_at_map[u.id].isoformat()
                row["slots"] = count_map.get(u.id, 0)
            data_members.append(row)

        return Response({"schedule_id": schedule.id, "members": data_members}, status=status.HTTP_200_OK)


class ScheduleFinalizeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, week_id: int):
        schedule = get_object_or_404(Schedule, id=week_id)
        room = schedule.room

        if not IsRoomOwner().has_object_permission(request, self, room):
            return Response(
                {"detail": "이 스케줄을 확정할 권한이 없습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if schedule.status == "finalized":
            return Response(
                {"detail": "이미 확정된 스케줄입니다."},
                status=status.HTTP_409_CONFLICT,
            )

        ser = ScheduleFinalizeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assignments = ser.validated_data["assignments"]

        member_ids = set(RoomMembership.objects.filter(room=room).values_list("user_id", flat=True))
        if room.owner_id:
            member_ids.add(room.owner_id)

        needed_map = {
            (n.day, n.hour): True
            for n in ScheduleNeededSlot.objects.filter(schedule=schedule, needed=True).only("day", "hour")
        }

        explicit_map = {}
        for item in assignments:
            key = (item["day"], item["hour"])
            assignee_id = item["assignee_id"]

            if key not in needed_map:
                return Response(
                    {"detail": f"Needed가 아닌 칸에 배정할 수 없습니다: day={key[0]}, hour={key[1]}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if assignee_id not in member_ids:
                return Response(
                    {"detail": f"유효하지 않은 담당자 ID가 포함되어 있습니다: {assignee_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            explicit_map[key] = assignee_id

        avail_qs = (
            ScheduleAvailabilitySlot.objects
            .filter(schedule=schedule, available=True)
            .only("day", "hour", "user_id")
        )
        buckets = {}
        for a in avail_qs:
            k = (a.day, a.hour)
            if k not in needed_map:
                continue
            buckets.setdefault(k, []).append(a.user_id)

        auto_map = {}
        for k, users in buckets.items():
            if k in explicit_map:
                continue
            if len(users) == 1:
                uid = users[0]
                if uid in member_ids:
                    auto_map[k] = uid

        final_pairs = [(d, h, uid) for (d, h), uid in {**explicit_map, **auto_map}.items()]

        now = timezone.now()
        try:
            with transaction.atomic():
                ScheduleConfirmedAssignment.objects.filter(schedule=schedule).delete()
                ScheduleConfirmedAssignment.objects.bulk_create([
                    ScheduleConfirmedAssignment(
                        schedule=schedule,
                        day=d,
                        hour=h,
                        assignee_id=uid,
                        finalized_by=request.user,
                        finalized_at=now,
                    )
                    for (d, h, uid) in final_pairs
                ])
                schedule.status = "finalized"
                schedule.finalized_at = now
                schedule.save(update_fields=["status", "finalized_at"])
        except Exception:
            return Response(
                {"detail": "저장 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "schedule_id": schedule.id,
                "status": schedule.status,
                "assigned_slots": len(final_pairs),
                "finalized_by": request.user.id,
                "finalized_at": schedule.finalized_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )

class ScheduleImportPreviousView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, week_id: int):
        target = get_object_or_404(Schedule, id=week_id)
        room = target.room

        # 방장만 허용
        if not IsRoomOwner().has_object_permission(request, self, room):
            return Response({"detail": "이 스케줄을 확정할 권한이 없습니다."},
                            status=status.HTTP_403_FORBIDDEN)

        # 타깃이 이미 확정이면 거절
        if target.status == "finalized":
            return Response({"detail": "이미 확정된 스케줄에는 복사할 수 없습니다."},
                            status=status.HTTP_409_CONFLICT)

        ser = ScheduleImportPreviousSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        source_week_id = ser.validated_data.get("source_week_id")

        if source_week_id:
            source = get_object_or_404(Schedule, id=source_week_id)
            if source.room_id != room.id:
                return Response({"detail": "소스 주차와 타깃 주차의 방이 다릅니다."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            # 직전 주 자동 탐색 (같은 room, start_date - 7일)
            prev_start = target.start_date - timedelta(days=7)
            source = Schedule.objects.filter(room=room, start_date=prev_start).first()
            if not source:
                return Response({"detail": "직전 주 스케줄을 찾을 수 없습니다."},
                                status=status.HTTP_404_NOT_FOUND)

        # 소스는 반드시 확정본이어야 함
        if source.status != "finalized":
            return Response({"detail": "소스 주차가 확정 상태가 아닙니다."},
                            status=status.HTTP_409_CONFLICT)

        # 소스 확정 슬롯 불러오기
        src_qs = (ScheduleConfirmedAssignment.objects
                  .filter(schedule=source)
                  .only("day", "hour", "assignee_id"))

        # 저장(교체)
        now = timezone.now()
        try:
            with transaction.atomic():
                ScheduleConfirmedAssignment.objects.filter(schedule=target).delete()
                ScheduleConfirmedAssignment.objects.bulk_create([
                    ScheduleConfirmedAssignment(
                        schedule=target,
                        day=row.day,
                        hour=row.hour,
                        assignee_id=row.assignee_id,
                        finalized_by=request.user,
                        finalized_at=now,
                    )
                    for row in src_qs
                ])

                target.status = "finalized"
                target.finalized_at = now
                target.save(update_fields=["status", "finalized_at"])
        except Exception:
            return Response({"detail": "복사 중 오류가 발생했습니다."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "source_week_id": source.id if source_week_id or source else None,
                "target_week_id": target.id,
                "status": target.status,
                "copied_assignments": src_qs.count(),
            },
            status=status.HTTP_200_OK,
        )

class ScheduleHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qser = ScheduleHistoryQuerySerializer(data=request.query_params)
        qser.is_valid(raise_exception=True)
        room_id = qser.validated_data["room_id"]
        limit = qser.validated_data["limit"]

        room = get_object_or_404(Room, id=room_id)
        if not IsRoomMemberOrOwner().has_object_permission(request, self, room):
            return Response({"detail": "이 방의 스케줄을 조회할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        qs = (Schedule.objects
              .filter(room_id=room_id)
              .order_by("-start_date")[:limit])

        items = []
        for s in qs:
            iso_year, iso_week, _ = s.start_date.isocalendar()
            items.append({
                "week": f"{iso_year}-W{iso_week:02d}",
                "status": s.status,
                "start_date": s.start_date,
                "end_date": s.end_date,
            })

        out = {"room_id": room_id, "history": items}
        return Response(ScheduleHistoryResponseSerializer(out).data, status=status.HTTP_200_OK)