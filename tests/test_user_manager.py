import unittest
import sqlite3
import os

from src.user_manager import UserManager, AdminUser, PlayerAccessRecord
import src.Database.sqlite


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

        self.db = src.Database.sqlite.SqliteUserManager()

        self.user_instance = UserManager(self.user)
        # self.user_instance.access = 2

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

    def test_push_update_user(self):
        player_data = dict(self.db.get_user_by_id(1234567))
        player_data['name'] = 'yacob'
        player_data['notification'] = 0

        self.user_instance.name = 'yacob'
        self.user_instance.notification = 0
        self.user_instance.push_update_user()
        updated_player_data = self.db.get_user_by_id(1234567)

        self.user_instance.name = "Jacob Jason"
        self.user_instance.notification = 1
        self.user_instance.push_update_user()

        self.assertDictEqual(player_data, dict(updated_player_data))

    def test_cache_user_player_record(self):
        new_user = UserManager(self.new_user)
        new_user.cache_new_user()
        check_record = self.db.get_user_by_id(568910)

        self.db.delete_user_by_id(568910)
        self.db.delete_user_access(568910)
        self.assertIsNotNone(check_record, "adding to db failure")

    def test_parse_access_control_description(self):
        position = self.user_instance.parse_access_control_description()
        self.assertEqual(position, "Member",
                         "needs to return Member for access = 4")


class TestAdminManager(unittest.TestCase):

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

        self.db = src.Database.sqlite.SqliteUserManager()

        self.user_instance = AdminUser(self.user)
        # self.user_instance.access = 2

    def test_get_access_levels_admin(self):
        self.user_instance.access = 1
        not_super = self.user_instance.get_access_levels()
        self.user_instance.access = 100
        super = self.user_instance.get_access_levels()

        self.assertGreater(len(super), len(not_super),
                           'super users get more access to more access levels')

    def test_generate_player_access_record(self):
        user_record = PlayerAccessRecord(self.user['id'])
        position = self.db.get_position(user_record.access)
        self.assertEqual(position, user_record.position)

    def test_push_player_record(self):
        user_record = PlayerAccessRecord(self.user['id'])
        user_record.new_access = 5
        self.user_instance.push_player_access(user_record)
        new_user_record = PlayerAccessRecord(self.user['id'])
        user_record.new_access = 4
        self.user_instance.push_player_access(user_record)
        self.assertEqual(new_user_record.access, 5)


if __name__ == "__main__":
    unittest.main()
