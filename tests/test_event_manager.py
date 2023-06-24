import unittest

import src.event_manager
import src.Database.sqlite


class TestAttendanceManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.user_id = 1234567
        self.event_id_1 = 12345678  # absent
        self.event_id_2 = 12345676  # attending
        self.event_id_3 = 12345677  # attending with reason

        # self.user_instance.access = 2

    def test_AttendanceManager_init_exists(self):
        attendance_record = src.event_manager.AttendanceManager(
            user_id=self.user_id,
            event_id=self.event_id_1
        )
        self.assertEqual(attendance_record.exists, True)

    def test_AttendanceManager_innit_not_exists(self):
        attendance_record = src.event_manager.AttendanceManager(
            user_id=self.user_id,
            event_id=22
        )
        self.assertEqual(attendance_record.exists, False)

    def test_attendance_attending(self):
        attendance_record = src.event_manager.AttendanceManager(
            user_id=self.user_id,
            event_id=self.event_id_2
        )
        self.assertEqual(attendance_record.status, 1)

    def test_attendance_absent(self):
        attendance_record = src.event_manager.AttendanceManager(
            user_id=self.user_id,
            event_id=self.event_id_1
        )
        self.assertEqual(attendance_record.status, 0)

    def test_attendance_attending_reason(self):
        attendance_record = src.event_manager.AttendanceManager(
            user_id=self.user_id,
            event_id=self.event_id_3
        )
        self.assertIsNotNone(attendance_record.reason,
                             msg=f"reason: {attendance_record.reason}")
