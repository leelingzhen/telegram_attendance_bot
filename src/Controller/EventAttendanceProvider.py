from src.Database.Services.EventAttendanceService import EventAttendanceService
from src.Enum.Enum import Gender, AccessCategory
from src.Models.Access import Access
from src.Models.Attendance import Attendance
from src.Models.Event import Event
from src.Models.User import User


class EventAttendanceProvider:
    _service: EventAttendanceService
    _event: Event

    def __init__(self, event_attendance_service: EventAttendanceService, event: Event):
        self._service = event_attendance_service
        self._event = event
    
    def name_and_reason(self, is_attending: bool, gender: Gender, access: Access) -> [list[str]]:
        attendances = self._service.get_attendances(
            event_id=self._event.id,
            is_attending=is_attending,
            gender=gender,
            access_category=access)

        name_and_reasons: list[str] = []

        for attendance in attendances:
            name = attendance[0].name
            reason = attendance[2].reason
            name_reason = f"{name} ({reason})"
            attendances.append(name_reason)

        return name_and_reasons

    def long_name_and_reason(self, is_attending: bool, gender: Gender, access: Access) -> [list[str]]:
        attendances = self._service.get_attendances(
            event_id=self._event.id,
            is_attending=is_attending,
            gender=gender,
            access_category=access)

        name_and_reasons: list[str] = []

        for attendance in attendances:
            name = attendance[0].name
            telegram_user = f"@{attendance[0].telegram_user}"
            reason = attendance[2].reason
            access = str(AccessCategory.enum_from_int(attendance[1].control_id))
            long_name_reason = f"({access}) {name} ({reason} - {telegram_user})"
            attendances.append(long_name_reason)

        return name_and_reasons



