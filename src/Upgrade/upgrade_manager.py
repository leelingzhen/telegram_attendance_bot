import json
import src.Upgrade.upgrade


class UpgradeManager:
    def __init__(self, config: dict, cur_ver, testing=False):
        self.config = config
        self.cur_ver = cur_ver

        self.file_loc = 'config.json'
        self.test_file_loc = 'test_config.json'

    def is_past_version(self):
        if 'version' not in self.config:
            self.config['version'] = 2

        return self.config['version'] < self.cur_ver

    def update_system(self, testing=False) -> bool:
        """
        updates db, configs etc etc if is a past version
        returns False if not updated
        returns True is updated
        """
        if not self.is_past_version():
            return False

        src.Upgrade.upgrade.upgrade_script(
            self.config['version'], self.cur_ver, testing=testing)
        self.finish_version_upgrade(testing=testing)
        return True

    def finish_version_upgrade(self, testing=False):
        self.config['version'] = self.cur_ver

        filename = self.file_loc
        if testing:
            filename = self.test_file_loc

        with open(filename, 'w') as outfile:
            json.dump(self.config, outfile, indent=4)
