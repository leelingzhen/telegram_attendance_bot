from src.Database.sqlite import Sqlite
import unittest
import os


class TestUserManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.user = {
            'username': "jacobjason",
            'id': 1234567,
            'first_name': 'Jacob Jason',
            'is_bot': False,
        }
        self.db = Sqlite()

    def test_read_query(self):
        test_read = self.db.read_query('members_attendance.sql')
        with open(os.path.join('src', 'Database', 'queries', 'members_attendance.sql')) as f:
            query = f.read()
        self.assertEqual(query, test_read, "not the same query")

    def test_get_user_access_exists(self):
        access = self.db.get_user_access(89637568)
        self.assertGreater(access, 0, "not greater than 0")

    def test_get_user_access_none(self):
        access = self.db.get_user_access(123)
        self.assertEqual(
            access, 0, "needs to return 0 when no access level found")

    # def get_future_events(self):
    #     event_data = self.get_future_events()

    # def test_get_attendance_members(self):
    #     self.db.get_attendance_members( )


if __name__ == "__main__":
    unittest.main()
