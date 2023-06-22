import sqlite3
import os
# import logging
import json

from datetime import date, datetime

from src.Database.sqlite import SqliteUserManager
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
    def __init__(self, user: dict):
        """
        intialise user from telegram message context
        """
        # importing connector
        self.db = SqliteUserManager()

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
        user_data = self.db.get_user_profile(
            user_id=self.id,
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
        with sqlite3.connect(CONFIG["database"]) as db:
            db.execute("BEGIN TRANSACTION")
            db.execute("UPDATE players SET name = ?, notification = ? WHERE id = ?",
                       (self.name, self.notification, self.id))
            db.commit()

    def push_new_user(self):
        db.execute("BEGIN TRANSACTION")
        data = (self.name, self.gender, self.id)
        db.execute('UPDATE players SET name = ?, gender = ? WHERE id = ?', data)
        data = (1, self.id)
        db.execute(
            'UPDATE access_control SET control_id=? WHERE player_id = ?', data)
        db.commit()

    def retrieve_user_data(self) -> list:
        """
        retrieve user data from the db
        returns user profiles in a list

        """
        user_profile = self.db.get_user_profile(user_id=self.id)
        if user_profile is None:
            self.cache_new_user()

        self.name = user_profile['name']
        self.telegram_user = user_profile['telegram_user']
        self.hidden = user_profile['hidden']
        self.gender = user_profile['gender']
        self.notication = user_profile['notification']
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
        self.db.insert_new_access_record(id=self.id)
        return None

    def get_user_access(self) -> int:
        """
        get the access of the player
        returns an int
        """
        access = self.db.get_user_access(self.id)

        return access

    def parse_access_control_description(self, access=None):
        if self.access is None:
            return None
        if access is None:
            access = self.access

        position = self.db.get_access_control_description(access)
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

        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            event_data = db.execute(
                "SELECT id, event_type FROM events WHERE id > ? AND access_control <= ? ORDER BY id", (event_id, self.access)).fetchall()
        return event_data

    def attending_events(self, from_date: datetime = None) -> dict:
        """
        returns a dictionary of attending events
        """
        if from_date is None:
            from_date = date.today()
        event_id = from_date.strftime('%Y%m%d%H%M')

        with sqlite3.connect(CONFIG["database"]) as db:
            db.row_factory = sqlite3.Row
            data = db.execute("""
                    SELECT id, event_type FROM events
                    JOIN attendance ON events.id = attendance.event_id
                    WHERE attendance.player_id = ?
                    AND attendance.event_id >= ?
                    AND attendance.status = ?
                    AND events.access_control <= ?
                    ORDER BY id
                                          """,
                              (self.id, event_id, 1, self.access)
                              ).fetchall()
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
        with sqlite3.connect(CONFIG["database"]) as db:
            db.row_factory = sqlite3.Row
            query = (access, only_active)
            data = db.execute("""
                SELECT * FROM players
                JOIN access_control ON players.id = access_control.player_id
                WHERE access_control.control_id >= ?
                AND players.notification >= ?
                AND players.hidden = 0
                ORDER BY
                gender DESC,
                name
                            """, query).fetchall()

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
        with sqlite3.connect(CONFIG["database"]) as db:
            db.row_factory = sqlite3.Row
            access_data = db.execute(
                'SELECT * FROM access_control_description WHERE id <= 100 ORDER BY id').fetchall()

        if self.access == 100:
            access_data = access_data[1:8]
        return access_data

    def select_players_on_access(self, access: int) -> sqlite3.Row:
        """
        return user ids and name based on the access selected
        """
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            players = db.execute("""
                    SELECT id, name FROM players
                    JOIN access_control ON players.id = access_control.player_id
                    WHERE control_id = ?
                    ORDER BY
                    name COLLATE NOCASE
                    """,
                                 (access, )
                                 ).fetchall()
        return players

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
        with sqlite3.connect(CONFIG['database']) as db:
            db.execute("UPDATE access_control SET control_id = ? WHERE player_id = ?",
                       (player.new_access, player.id))
            db.commit()
