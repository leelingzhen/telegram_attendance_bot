import unittest
import sqlite3
import os

from src.user_manager import UserManager


class TestUserManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.user = {
            'username': "jacobjason",
            'id': 1234567,
            'first_name': 'Jacob Jason',
            'is_bot': False,
        }
        self.new_user = {
            'username': "new_user",
            'id': 568910,
            'first_name': 'New User',
            'is_bot': False,
        }
        self.con = sqlite3.connect(
            os.path.join('resources', 'attendance.db'))
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()

        self.user_instance = UserManager(self.user)

    def test_username_correct(self):
        self.assertEqual(self.user_instance.username,
                         'jacobjason', 'telegram username not equal')

    def test_get_user_access(self):
        access = self.user_instance.get_user_access()
        self.assertEqual(access, 4, "Jacon Jason has access of 4")

    def test_retrieve_user_data(self):
        self.user_instance.retrieve_user_data()
        self.assertEqual(self.user['first_name'],
                         self.user_instance.name, "name not loaded")

    def test_get_existing_name_that_exists(self):
        user_name = self.user_instance.get_exisiting_name(name="Jacob Jason")
        self.assertEqual(user_name, "@jacobjason")

    def test_get_existing_name_that_dont_exists(self):
        user_name = self.user_instance.get_exisiting_name(name="xyz")
        self.assertIsNone(user_name, 'there shouldnt be a name with xyz')

    def test_cache_user_player_record(self):
        new_user = UserManager(self.new_user)
        new_user.cache_new_user()
        check_record = self.cur.execute(
            "SELECT * FROM players WHERE id = 568910"
        ).fetchone()

        self.cur.execute("DELETE FROM players WHERE id = 568910")
        self.cur.execute("DELETE FROM access_control WHERE player_id = 568910")
        self.con.commit()
        self.assertIsNotNone(check_record, "adding to db failure")

    def test_cache_user_access_control(self):
        new_user = UserManager(self.new_user)
        new_user.cache_new_user()
        check_record = self.cur.execute(
            "SELECT * FROM access_control WHERE player_id = 568910"
        ).fetchone()
        self.cur.execute("DELETE FROM players WHERE id = 568910")
        self.cur.execute("DELETE FROM access_control WHERE player_id = 568910")
        self.con.commit()
        self.assertIsNotNone(check_record, "adding to db failure")


if __name__ == "__main__":
    unittest.main()
