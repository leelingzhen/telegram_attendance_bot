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


if __name__ == "__main__":
    unittest.main()
