import src.Database.sqlite
import unittest
import os
import sqlite3

"""
test_event_id = 12345678, 12345677, 12345676
test_user_id = 1234567

"""


class TestSqlite(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.user = {
            'username': "jacobjason",
            'id': 1234567,
            'first_name': 'Jacob Jason',
            'is_bot': False,
        }

        self.db = src.Database.sqlite.Sqlite()

    def test_read_query(self):
        test_read = self.db.read_query('members_attendance.sql')
        with open(os.path.join('src', 'Database', 'queries', 'members_attendance.sql')) as f:
            query = f.read()
        self.assertEqual(query, test_read, "not the same query")


class TestUserTablesSqlite(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.user = {
            'username': "jacobjason",
            'id': 1234567,
            'first_name': 'Jacob Jason',
            'is_bot': False,
        }

        self.db = src.Database.sqlite.UsersTableSqlite()

    def test_read_user(self):
        player_data = self.db.get_user_by_id(self.user['id'])
        self.assertIsNotNone(player_data)

    def test_read_non_existing_user(self):
        player_data = self.db.get_user_by_id(0)
        self.assertIsNone(player_data)

    def test_read_2_fields_user(self):
        player_data = self.db.get_user_by_id(
            id=self.user['id'], name=self.user['first_name']
        )
        self.assertIsNotNone(player_data)

    def test_read_2_fields_not_exist_user(self):
        player_data = self.db.get_user_by_id(
            id=self.user['id'], name="xyz"
        )
        self.assertIsNone(player_data)

    def test_insert_valid_user(self):
        self.db.insert_user(
            id=666,
            telegram_user='testes',
            name='Test Adding User',
            gender='Male',
        )
        new_user = self.db.get_user_by_id(666)
        self.db.delete_user_by_id(666)
        self.assertIsNotNone(new_user)

    def test_delete_user(self):
        self.db.insert_user(
            id=666,
            telegram_user='testes',
            name='Test Adding User',
            gender='Male',
        )
        self.db.delete_user_by_id(666)
        deleted_user = self.db.get_user_by_id(666)
        self.assertIsNone(deleted_user)

    def test_insert_cached_user(self):
        self.db.insert_user(id=666, telegram_user='testes')
        new_user = self.db.get_user_by_id(666)
        self.db.delete_user_by_id(666)
        self.assertIsNone(new_user['name'])

    def test_insert_invalid_user_no_telegram_user(self):
        with self.assertRaises(TypeError):
            self.db.insert_user(1234)

    def test_insert_invalid_user_only_no_id(self):
        with self.assertRaises(TypeError):
            self.db.insert_user(telegram_user="testing")

    def test_update_user_id(self):
        self.db.update_user(id=1234567, name='yacob')
        user_data = self.db.get_user_by_id(id=1234567)
        self.db.update_user(id=1234567, name="Jacob Jason")
        self.assertEqual(user_data['name'], 'yacob')

    def test_update_user_notification(self):
        self.db.update_user(id=1234567, notification=0)
        user_data = self.db.get_user_by_id(id=1234567)
        self.db.update_user(id=1234567, notification=1)
        self.assertEqual(user_data['notification'], 0)


class TestEventsTableSqlite(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.user = {
            'username': "jacobjason",
            'id': 1234567,
            'first_name': 'Jacob Jason',
            'is_bot': False,
        }

        self.db = src.Database.sqlite.EventsTableSqlite()

    def test_read_event(self):
        event_data = self.db.get_event_by_id(12345678)
        self.assertIsNotNone(event_data)

    def test_insert_delete_event(self):
        self.db.insert_event(
            id=111,
            event_type='test type',
            event_date="1998-08-03",  # "%Y-%m-%d"
            start_time="13:00",  # "%H:%M"
            end_time="14:00",  # "%H:%M"
            location="test location",
            access_control=2,
            announcement=None
        )
        inserted_event = self.db.get_event_by_id(111)
        self.db.delete_event_by_id(111)
        deleted_event = self.db.get_event_by_id(111)
        self.assertIsNotNone(
            inserted_event, "event should be created and should exist")
        self.assertIsNone(
            deleted_event, "event should be deleted and shouldnt exist")

    def test_update_event(self):
        event_exists = self.db.get_event_by_id(12345678)

        self.db.update_event(
            original_id=12345678,
            new_id=12345679,
            event_type='test type',
            event_date="1998-08-03",  # "%Y-%m-%d"
            start_time="13:00",  # "%H:%M"
            end_time="14:00",  # "%H:%M"
            location="test location",
            access_control=2,
            announcement=None
        )
        event_shouldnt_exist = self.db.get_event_by_id(12345678)
        self.db.update_event(
            original_id=12345679,
            new_id=12345678,
            event_type='Test Type',
            event_date="1998-08-03",  # "%Y-%m-%d"
            start_time="13:00",  # "%H:%M"
            end_time="16:00",  # "%H:%M"
            location="Test Location",
            access_control=2,
            announcement='Test announcement'
        )

        self.assertIsNotNone(event_exists, "event should exist ")
        self.assertIsNone(event_shouldnt_exist, "event shouldnt exist")


class TestAttendanceTableSqlite(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.user = {
            'username': "jacobjason",
            'id': 1234567,
            'first_name': 'Jacob Jason',
            'is_bot': False,
        }

        self.db = src.Database.sqlite.AttendanceTableSqlite()

    def test_attendance_record_status(self):
        attendance = self.db.get_attendance(user_id=1234567, event_id=12345676)
        self.assertEqual(attendance['status'], 1)

    def test_attendance_record_reason(self):
        attendance = self.db.get_attendance(user_id=1234567, event_id=12345678)
        self.assertEqual(attendance['reason'], 'test_reason')

    def test_insert_attendance_record(self):
        self.db.insert_attendance(
            user_id=111,
            event_id=111,
            status=1,
            reason="test"
        )
        attendance = self.db.get_attendance(user_id=111, event_id=111)
        self.db.delete_attendance(user_id=111, event_id=111)
        deleted = self.db.get_attendance(user_id=111, event_id=111)
        self.assertIsNotNone(attendance)
        self.assertIsNone(deleted)

    def test_update_attendance_record(self):
        self.db.update_attendance(
            user_id=1234567, event_id=12345676, status=0, reason=None)
        attendance = self.db.get_attendance(user_id=1234567, event_id=12345676)
        self.db.update_attendance(
            user_id=1234567, event_id=12345676, status=1, reason=None)
        self.assertEqual(attendance['status'], 0)


class TestSqliteUserManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.user = {
            'username': "jacobjason",
            'id': 1234567,
            'first_name': 'Jacob Jason',
            'is_bot': False,
        }

        self.true_con = sqlite3.connect(
            os.path.join('resources', 'attendance.db'))
        self.true_con.row_factory = sqlite3.Row
        self.true_db = self.true_con.cursor()

        self.db = src.Database.sqlite.SqliteUserManager()

    def test_read_attendance(self):
        attendance = self.db.get_attendance(
            user_id=1234567, event_id=12345678)
        self.assertIsNotNone(attendance)

    def test_get_user_access_exists(self):
        real_access = self.true_db.execute(
            'SELECT control_id FROM access_control WHERE player_id = ?',
            (89637568,)
        ).fetchone()
        real_access = real_access['control_id']
        access = self.db.get_user_access(89637568)
        self.assertGreater(access, 0, "not greater than 0")

    def test_get_user_access_none(self):
        access = self.db.get_user_access(123)
        self.assertEqual(
            access, 0, "needs to return 0 when no access level found")

    def test_get_attending_events(self):
        data = self.db.get_attending_events(
            user_id=1234567, event_id=0, access=4)
        self.assertEqual(
            len(data), 2, "there are only 2 events that user_id 1234567 is attending")

    def test_get_access_levels(self):
        self.db.get_access_levels()

    def test_get_access_join_on_users(self):
        users = self.db.get_users_join_on_access(100)
        self.assertEqual(len(users), 1)


class TestSqliteEventManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.db = src.Database.sqlite.SqliteEventManager()

    def test_get_users_on_attendance_access(self):
        gender = 'both'
        access_cat = 'all'
        users = self.db.get_users_on_attendance_access(
            attendance=1,
            gender=gender,
            event_id=202305272000,
            access_cat=access_cat
        )
        print("")
        print(
            f"printing users from gender = {gender}, access_cat = {access_cat}")
        for item in users:
            print(item['name'])
        self.assertIsNotNone(users)

    # TODO raise erros for wrong cats

    def test_get_unindicated(self):
        access_cat = 'member'
        users = self.db.get_unindicated_users(
            event_id=202305272000,
            access_cat=access_cat
        )
        print("")
        print(f"printing unindicated users of access_cat = {access_cat}")
        for item in users:
            print(item['name'])
        self.assertIsNotNone(users)


class TestMessageTableSqlite(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.db = src.Database.sqlite.MessageTableSqlite()

    def test_get_message_event_only(self):
        data = self.db.get_msg_records(event_id=202306071930)
        self.assertEqual(
            len(data), 1, 'should only be able to query one record')

    def test_get_message_user_only(self):
        data = self.db.get_msg_records(user_id=89637568)
        self.assertGreater(len(data), 1)

    def test_get_message_user_and_event(self):
        data = self.db.get_msg_records(user_id=89637568, event_id=202306071930)
        self.assertEqual(len(data), 1)

    def test_create_msg_record(self):
        self.db.insert_msg_record(user_id=123, event_id=123, message_id=123)
        data = self.db.get_msg_records(event_id=123)
        self.db.delete_msg_record(user_id=123, event_id=123)
        deleted = self.db.get_msg_records(event_id=123)
        self.assertIsNotNone(data)
        self.assertEqual(deleted, list())
        


if __name__ == "__main__":
    unittest.main()
