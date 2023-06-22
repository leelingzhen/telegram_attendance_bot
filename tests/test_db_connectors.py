from src.Database.sqlite import Sqlite
import unittest
import os
import sqlite3


class TestUserManager(unittest.TestCase):

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

        self.db = Sqlite()

    def test_read_query(self):
        test_read = self.db.read_query('members_attendance.sql')
        with open(os.path.join('src', 'Database', 'queries', 'members_attendance.sql')) as f:
            query = f.read()
        self.assertEqual(query, test_read, "not the same query")

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

    # def get_future_events(self):
    #     event_data = self.get_future_events()

    # def test_get_attendance_members(self):
    #     self.db.get_attendance_members( )


if __name__ == "__main__":
    unittest.main()
