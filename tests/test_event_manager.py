import unittest

import src.event_manager
import src.Database.sqlite


class TestAttendanceManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.db = src.Database.sqlite.SqliteEventManager()
        self.user_id = 1234567
        self.event_id_1 = 12345678  # absent
        self.event_id_2 = 12345676  # attending
        self.event_id_3 = 12345677  # attending with reason

        self.event_id_hardcourt = 202306211930
        self.event_id_field_training = 202306241400
        self.event_id_cohesion = 202309022359  # has announcement entities
        self.event_id_jb = 202305272000

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

    def test_announcement_entities(self):
        event_instance = src.event_manager.EventManager(self.event_id_cohesion)
        event_instance.generate_entities()
        self.assertIsNotNone(event_instance.announcement_entities)

    def test_no_announcement_entities(self):
        event_instance = src.event_manager.EventManager(
            self.event_id_field_training)
        event_instance.generate_entities()
        self.assertEqual(event_instance.announcement_entities, list())

    def test_pull_event(self):
        event_instance = src.event_manager.EventManager(
            self.event_id_cohesion
        )
        event_instance.pull_event()
        self.assertEqual(event_instance.event_type, "Cohesion")
        self.assertEqual(event_instance.record_exist,
                         True, "record should exist")

    def test_pull_event_doesnt_exist(self):
        event_instance = src.event_manager.EventManager(
            111
        )
        event_instance.pull_event()
        self.assertEqual(event_instance.record_exist, False,
                         "record shouldnt exists for event_id = 111")

    def test_curate_attendance(self):
        event_instance = src.event_manager.TrainingEventManager(
            self.event_id_jb
        )
        male_records, female_records, absentees, unindicated = event_instance.curate_attendance(
            attach_usernames=False)
        print("")
        print("printing curated attendance")
        print(male_records)
        print(female_records)
        print(absentees)
        print(unindicated)
        self.assertIsNotNone(male_records)


class TestEventManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.db = src.Database.sqlite.SqliteEventManager()
        self.user_id = 89637568  # ling zhen
        self.event_id_hardcourt = 202306211930
        self.event_id_field_training = 202306241400
        self.event_id_cohesion = 202309022359  # has announcement entities
        self.event_id_jb = 202305272000

    def test_pull_event(self):
        event_instance = src.event_manager.EventManager(
            202305272000
        )
        event_instance.pull_event()
        self.assertTrue(event_instance.record_exist, "record should exist")
        self.assertIsNotNone(event_instance.event_date,
                             "fields should be filled up")

    def test_admin_event_instantiation(self):
        event_instance = src.event_manager.AdminEventManager(
            id=self.event_id_jb,
            record_exist=True
        )
        self.assertIsNotNone(event_instance.event_date,
                             "fields sbould be filled up")

    def test_admin_event_instatiation_not_exist(self):
        event_instance = src.event_manager.AdminEventManager(
            id=111,
        )
        self.assertFalse(event_instance.record_exist, "record shouldnt exist")
        self.assertIsNone(event_instance.event_date,
                          "fields should be empty: None")

    def test_update_event(self):
        event_instance = src.event_manager.AdminEventManager(
            id=self.event_id_jb,
            record_exist=True
        )
        event_instance.set_id(id=202305272100)
        event_instance.update_event_records()
        event_exists = self.db.get_event_by_id(202305272100)
        attendance_exist = self.db.get_attendance(89637568, 202305272100)
        event_instance.original_id = 202305272100
        event_instance.set_id(202305272000)
        event_instance.update_event_records()
        self.assertIsNotNone(event_exists)
        self.assertIsNotNone(attendance_exist)
