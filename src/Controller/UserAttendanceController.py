from abc import ABC, abstractmethod

from src.Database.Services.UserAttendanceService import UserAttendanceServicing, UserAttendanceService
from src.Models.Attendance import Attendance


class UserAttendanceControlling(ABC):

    @abstractmethod
    def is_exists(self, event_id: int, user_id: int) -> bool:
        pass
    @abstractmethod
    def fetch_attendance(self, event_id: int, user_id: int) -> Attendance:
        pass

    @abstractmethod
    def update_attendance(self, attendance: Attendance):
        pass


class UserAttendanceController(UserAttendanceControlling):

    _attendance_service: UserAttendanceServicing

    def __init__(self, attendance_service: UserAttendanceServicing = UserAttendanceService()):
        self._attendance_service = attendance_service

    def is_exists(self, event_id: int, user_id: int) -> bool:
        return self._attendance_service.is_record_exists(event_id=event_id, user_id=user_id)

    def fetch_attendance(self, event_id: int, user_id: int) -> Attendance:
        attendances = self._attendance_service.get_attendance(event_id=event_id, user_id=user_id)
        return attendances[0]

    def update_attendance(self, attendance: Attendance):
        self._attendance_service.update([attendance])