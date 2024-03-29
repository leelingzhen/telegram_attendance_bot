import sqlite3
import os
# import logging
import json

from datetime import date, datetime

# from src.Database.sqlite import SqliteUserManager
import src.Database.sqlite
from telegram.bot import Bot
from telegram.error import Unauthorized, BadRequest
import telegram.message


with open("config.json") as f:
    CONFIG = json.load(f)
    db = sqlite3.connect(
        CONFIG['database'],
        check_same_thread=False
    )


class UserObj:
    def __init__(self, user: dict):
        self.user_id = user['id']
        self.name = user['name']
        self.telegram_user = user['telegram_user']
        self.hidden = user['hidden']
        self.gender = user['gender']
        self.notification = user['notification']


class UserManager:
    def __init__(
            self,
            user: dict = None,
            db=src.Database.sqlite.SqliteUserManager()
    ):
        """
        intialise user from telegram message context
        Args:
            user: optional if empty, it will not have telegram context fields
            db : the type of db to be used
        """
        # importing connector
        self.db = db

        if user:
            self.username = user['username']
            self.id = user['id']
            self.first_name = user['first_name']
            self.is_bot = user['is_bot']
            self.access = self.get_user_access()

        self.name = None
        self.telegram_user = None
        self.hidden = None
        self.gender = None
        self.position = None
        self.notification = None
        self.language = None

    def set_gender(self, gender: str):
        self.gender = gender

    def set_notification(self, notification):
        self.notification = notification

    def get_exisiting_name(self, name):
        user_data = self.db.get_user_by_id(
            id=self.id,
            name=name
        )
        if user_data:
            return "@" + user_data['telegram_user']
        return None

    def set_name(self, name):
        self.name = name

    def set_telegram_user(self):
        self.telegram_user = self.username

    def push_update_user(self):
        self.db.update_user(
            id=self.id,
            name=self.name,
            notification=self.notification
        )

    def push_new_user(self):
        self.db.update_user(id=self.id, name=self.name, gender=self.gender)
        self.db.update_access(user_id=self.id, new_access=1)

    def update_telegram_user(self):
        if self.telegram_user is None:
            self.retrieve_user_data()

        if not self.username_tally():
            self.set_telegram_user()
            self.db.update_user(id=self.id, telegram_user=self.telegram_user)

    def retrieve_user_data(self) -> list:
        """
        retrieve user data from the db
        returns user profiles in a list

        """
        user_profile = self.db.get_user_by_id(id=self.id)
        if user_profile is None:
            self.cache_new_user()

        self.name = user_profile['name']
        self.telegram_user = user_profile['telegram_user']
        self.hidden = user_profile['hidden']
        self.gender = user_profile['gender']
        self.notification = user_profile['notification']
        self.language = user_profile['language_pack']

        return user_profile

    def username_tally(self):
        """
        returns true if the telegram_user == username
        """
        if self.telegram_user is None:
            return True
        return self.telegram_user == self.username

    def cache_new_user(self) -> None:
        """
        updates the database when a new user uses the bot
        """
        self.db.insert_user(id=self.id, telegram_user=self.username)
        self.db.insert_access(user_id=self.id, access=0)
        return None

    def get_user_access(self) -> int:
        """
        get the access of the player
        returns an int
        """
        access = self.db.get_access(self.id)
        if not access:
            return 0
        return access['control_id']

    def parse_access_control_description(self, access=None):
        if self.access is None:
            return None
        if access is None:
            access = self.access

        position = self.db.get_position(access)
        return position

    def get_event_dates(self,
                        from_date: date = 0) -> sqlite3.Row:
        """
        get the list of dates from a date
        from_date :datetime.date
        """
        if from_date == 0:
            from_date = date.today()
        event_id = from_date.strftime('%Y%m%d%H%M')
        event_data = self.db.get_future_events(
            event_id=event_id,
            access=self.access
        )

        return event_data

    def attending_events(self, from_date: datetime = None) -> dict:
        """
        returns a dictionary of attending events
        """
        if from_date is None:
            from_date = date.today()
        event_id = from_date.strftime('%Y%m%d%H%M')

        data = self.db.get_attending_events(
            user_id=self.id,
            event_id=event_id,
            access=self.access
        )

        # sorting by categories
        dict_date = {}

        for row_obj in data:
            event_type = row_obj["event_type"]
            if event_type not in dict_date:
                dict_date[event_type] = list()

            event_date = datetime.strptime(
                str(row_obj["id"]), '%Y%m%d%H%M')
            dict_date[event_type].append(event_date)

        return dict_date


class PlayerAccessRecord(UserManager):
    def __init__(self, id):
        """
        initialise user from id from db
        """
        UserManager.__init__(self)

        self.id = id
        self.retrieve_user_data()
        self.access = self.get_user_access()
        self.position = self.parse_access_control_description()

        self.new_access = None
        self.new_position = None

    def set_new_access(self, access):
        self.new_access = access
        self.new_position = self.parse_access_control_description(access)


class AdminUser(UserManager):
    def __init__(self, user):
        super().__init__(user)
        token_file = os.path.join('.secrets', 'bot_credentials.json')
        with open(token_file, 'r') as bot_token_file:
            bot_tokens = json.load(bot_token_file)

        self.is_dev = CONFIG['development']
        self.bot_token = bot_tokens['dev_bot']

        if not self.is_dev:
            self.bot_token = bot_tokens['training_bot']

    def get_users_list(self,
                       only_active: bool = True,
                       only_members: bool = True
                       ) -> sqlite3.Row:
        """
        get all users in the telegram bot
        only_active: players who want to be notified and selected notfication = 1
        only_active = False would send messages to inactive players

        only_members: for players who are access member or above
        only_members = False would send messages to all guests as well

        """
        access = 4 if only_members else 2
        data = self.db.get_users_list(access=access, notification=only_members)
        return data

    def intercept_msg(self, msg, msg_entities, parse_mode):
        intercept_id = 89637568
        self.send_message_to_user(intercept_id, msg, msg_entities, parse_mode)

    def send_message_to_user(self,
                             chat_id: int,
                             msg: str,
                             msg_entities=None,
                             parse_mode=None
                             ) -> telegram.Message:
        """
        send a message to the user on the training bot
        returns none if sending in unsuccessful
        """
        bot_messenger = Bot(token=self.bot_token)
        try:
            message_object = bot_messenger.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode=parse_mode,
                entities=msg_entities
            )
        except BadRequest:
            return None
        except Unauthorized:
            return None
        else:
            return message_object

    def pin_message(self, chat_id, message_object):
        """
        pin messages after they are sent,
        chat_id refers to the user to send to
        message_object is the messsage object to be pinned in chat
        """
        bot_messenger = Bot(token=self.bot_token)
        bot_messenger.pin_chat_message(
            chat_id=chat_id,
            message_id=message_object.message_id,
            disable_notification=True
        )

    def send_message_by_list(self,
                             send_list: list,
                             msg: str,
                             msg_entities=None,
                             pin: bool = False,
                             parse_mode=None
                             ):
        """
        used to mass send multiple messages,
        send list is a list of event ids
        msg will be a plain text string
        msg_entities are used for markdown text in telegram.Message object
        pin = True will pin messages after they are being sent
        parse_mode type of markdown used, options are 'html' 'markdown'
        parse_mode will be ignored if msg_entities is not None

        """

        for row in send_list:
            telegram_user = f"@{row['telegram_user']}"
            chat_id = row['id']

            message_object = self.send_message_to_user(
                chat_id=chat_id,
                msg=msg,
                msg_entities=msg_entities,
                parse_mode=parse_mode
            )

            if message_object:
                if pin:
                    self.pin_message(chat_id, message_object)
                yield 'success'
            else:
                yield telegram_user

    def get_access_levels(self) -> sqlite3.Row:
        """
        based on the access control of the admin user,
        get the levels of access available to the user
        """
        access_data = self.db.get_access_levels()

        if self.access != 100:
            access_data = access_data[1:8]
        return access_data

    def select_players_on_access(self, access: int) -> sqlite3.Row:
        """
        return user ids and name based on the access selected
        """
        users = self.db.get_users_join_on_access(access)
        return users

    def read_msg_from_file(self, date_str: str) -> str:
        """
        reads strings from a txt file
        date_string: text to be replaced in the txt file
        """
        filename = os.path.join("resources", 'messages', 'not_indicated.txt')
        with open(filename, "r", encoding="utf-8") as text_f:
            msg = text_f.read().replace("{date}", date_str).rstrip()
        return msg

    def generate_player_access_record(self, id):
        return PlayerAccessRecord(id)

    def push_player_access(self, player: PlayerAccessRecord):
        self.db.update_access(
            user_id=player.id,
            new_access=player.new_access
        )
