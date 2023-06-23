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
            player_id=1234567, event_id=12345678)
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

    def test_get_user_profile_1_correct_kwarg(self):
        user_data = self.db.get_user_profile(user_id=1234567)
        self.assertEqual(user_data['name'], "Jacob Jason",
                         "should query Jacob Jason test user")

    def test_get_user_profile_1_wrong_kwarg(self):
        user_data = self.db.get_user_profile(
            user_id=0,
        )
        self.assertIsNone(
            user_data, 'no such record should exist for user_id = 0')

    def test_get_user_profile_2_correct_kwarg(self):
        user_data = self.db.get_user_profile(
            user_id=1234567,
            name="Jacob Jason"
        )
        self.assertEqual(user_data['telegram_user'], 'jacobjason')

    def test_get_user_profile_2_wrong_kwarg(self):
        user_data = self.db.get_user_profile(
            user_id=1234567,
            name="Lee Ling Zhen"
        )
        self.assertIsNone(
            user_data, 'no such record should exist for given kwargs')

    def test_get_user_profiles_no_kwarg(self):

        with self.assertRaises(SyntaxError):
            self.db.get_user_profile()

    # testing adding

    # def test_insert_user(self):
    #     self.db.insert_user(568910, 'test_user')
    #     new_user_record = self.true_db.execute(
    #         "SELECT * FROM players WHERE id = 568910")
    #     self.true_db.execute("DELETE FROM players WHERE id = 568910")
    #     self.true_con.commit()
    #     self.assertIsNotNone(new_user_record, "adding to db failed")
    #
    def test_adding_new_access_record(self):
        self.db.insert_new_access_record(568910)
        access_control = self.true_db.execute(
            "SELECT * FROM access_control WHERE player_id = 568910"
        )
        self.true_db.execute(
            'DELETE FROM access_control WHERE player_id = 568910')
        self.true_con.commit()
        self.assertIsNotNone(access_control)

    def test_get_access_control_description(self):
        position = self.db.get_access_control_description(2)
        self.assertEqual(position, "Guest",
                         "need to return guest for access = 2")

    # def get_future_events(self):
    #     event_data = self.get_future_events()

    # def test_get_attendance_members(self):
    #     self.db.get_attendance_members( )


if __name__ == "__main__":
    unittest.main()
