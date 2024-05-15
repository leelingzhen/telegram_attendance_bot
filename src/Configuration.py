import json
import os


class Configuration:
    def __init__(
            self,
            development,
            database,
            team_name,
            training_bot_name,
            use_webhook,
            training_bot_url,
            admin_bot_url,
            version,
    ):
        self.development = development
        self.database = database
        self.team_name = team_name
        self.training_bot_name = training_bot_name
        self.use_webhook = use_webhook
        self.training_bot_url = training_bot_url
        self.admin_bot_url = admin_bot_url
        self.version = version

    @staticmethod
    def load_configuration(file_path: str = "config.json") -> "Configuration":
        with open(file_path, 'r') as file:
            json_object = json.loads(file.read())
            return Configuration(
                json_object.get("development"),
                json_object.get("database"),
                json_object.get("team_name"),
                json_object.get("training_bot_name"),
                json_object.get("use_webhook"),
                json_object.get("training_bot_url"),
                json_object.get("admin_bot_url"),
                json_object.get("version"),
            )


class BotTokens:
    def __init__(
            self,
            training_bot,
            admin_bot,
            dev_bot,
            admin_dev_bot,
    ):
        self.training_bot = training_bot
        self.admin_bot = admin_bot
        self.dev_bot = dev_bot
        self.admin_dev_bot = admin_dev_bot

    @staticmethod
    def load(file_path: str = os.path.join(".secrets", "bot_credentials.json")) -> "BotTokens":
        with open(file_path, 'r') as file:
            json_object = json.loads(file.read())
            return BotTokens(
                json_object.get("training_bot"),
                json_object.get("admin_bot"),
                json_object.get("dev_bot"),
                json_object.get("admin_dev_bot"),
            )
