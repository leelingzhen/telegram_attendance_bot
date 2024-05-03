import unittest

from src.Database.DatabaseSession.DatabaseSessionProviding import (DatabaseSessionProviding,
                                                                   Sqlite3SessionProvider)
from src.Database.Services.UserAttendanceService import UserAttendanceDatabaseService
from src.Models.Attendance import Attendance


class MyTestCase(unittest.TestCase):
    session_provider: DatabaseSessionProviding = Sqlite3SessionProvider(isTest=True)
    service = UserAttendanceDatabaseService(database_session_provider=session_provider)

    def testCRUD(self):
        event_id = 12385
        user_id = 123

        attendance = Attendance(
            event_id=event_id,
            user_id=user_id,
            status=1,
            reason="test reason"
        )
        self.service.create(attendance)

        check_attendances = self.service.read(
            user_id=user_id,
            event_id=event_id
        )
        self.assertEqual(attendance.user_id, check_attendances[0].user_id)  # add assertion here

        self.service.delete(attendance)

        is_attendance_exist = self.service.is_record_exists(
            user_id=user_id,
            event_id=event_id
        )
        self.assertFalse(is_attendance_exist)

    def testManyAttendances(self):
        user_id1 = 123
        user_id2 = 234
        user_id3 = 567
        user_id4 = 890
        user_id5 = 369
        event_id = 1234

        attendance1 = Attendance(event_id=event_id, user_id=user_id1, status=1)
        attendance2 = Attendance(event_id=event_id, user_id=user_id2, status=0)
        attendance3 = Attendance(event_id=event_id, user_id=user_id3, status=1)
        attendance4 = Attendance(event_id=event_id, user_id=user_id4, status=0)
        attendance5 = Attendance(event_id=event_id, user_id=user_id5, status=0)

        all_attendance = [attendance1, attendance2, attendance3, attendance4, attendance5]

        for attendance in all_attendance:
            self.service.create(attendance)

        attendance_all = self.service.read(event_id=event_id)
        attendance_status_1 = self.service.read(event_id=event_id, status=1)

        for attendance in all_attendance:
            self.service.delete(attendance)

        self.assertEqual(5, len(attendance_all))
        self.assertEqual(2, len(attendance_status_1))

    def testMultipleUpdates_whenSomeAreNewRecords(self):
        user_id = 1234

        attendances = [
            Attendance(event_id=123, user_id=user_id, status=1),
            Attendance(event_id=234, user_id=user_id, status=1),
            Attendance(event_id=567, user_id=user_id, status=1),
            Attendance(event_id=890, user_id=user_id, status=1),
            Attendance(event_id=369, user_id=user_id, status=1),
        ]
        for attendance in attendances:
            self.service.create(attendance)

        changed_attendance = Attendance(event_id=123, user_id=user_id, status=0)
        added_attendance = Attendance(event_id=498, user_id=user_id, status=1)
        new_attendances = [
            changed_attendance,
            added_attendance
        ]

        self.service.update(new_attendances)

        attendance_under_test = self.service.read(user_id=user_id)

        for attendance in attendance_under_test:
            self.service.delete(attendance)

        self.assertEqual(6, len(attendance_under_test))
        self.assertTrue(0 == attendance_under_test[0].status)


if __name__ == '__main__':
    unittest.main()
