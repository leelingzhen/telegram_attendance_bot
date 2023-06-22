import unittest

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


if __name__ == "__main__":
    unittest.main()
