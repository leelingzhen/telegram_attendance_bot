import unittest
import os

from src.Upgrade.upgrade_manager import UpgradeManager


class TestUpgradeManager(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.config = {
            "development": 1,
            "database": "resources/attendance.db",
            "team_name": "Alliance",
            "training_bot_name": "@alliance_training_bot",
            "use_webhook": 0,
            "training_bot_url": "",
            "admin_bot_url": "",
            "version": 2
        }

        self.cur_ver = 2.1

    def test_check_version(self):
        config = {
            "development": 1,
            "database": "resources/attendance.db",
            "team_name": "Alliance",
            "training_bot_name": "@alliance_training_bot",
            "use_webhook": 0,
            "training_bot_url": "",
            "admin_bot_url": ""
        }

        version = UpgradeManager(config=config, cur_ver=2.1)
        version.is_past_version()

        self.assertEqual(version.config['version'],
                         2, 'automatic instantiation is 2')
        self.assertTrue(version.is_past_version(),
                        'initiated as 2 and needs to be < 1')

    def test_finish_version_upgrade(self):

        version = UpgradeManager(self.config, 2.0)
        version.finish_version_upgrade(testing=True)

        self.assertTrue(os.path.isfile('test_config.json'),
                        "file should be created as test_config.json")
        os.remove('test_config.json')

    def test_update_system(self):
        version = UpgradeManager(self.config, 2.0)
        self.assertFalse(version.update_system(False))

    def test_update_system_true(self):
        version = UpgradeManager(self.config, 2.3)
        self.assertTrue(version.update_system(True))
        self.assertTrue(os.path.isfile('test_config.json'),
                        "file shold be created as test_config.json")
        os.remove('test_config.json')
