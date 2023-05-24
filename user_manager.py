import sqlite3
import os
import logging
import json

from datetime import date, datetime

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
        self.username = user['username']
        self.id = user['id']
        self.first_name = user['first_name']
        self.is_bot = user['is_bot']
        self.access = self.get_user_access()

        self.name = None
        self.telegram_user = None
        self.hidden = None
        self.gender = None

    def retrieve_user_data(self) -> list:
        """
        retrieve user data from the db
        returns user profiles in a list

        """

        with sqlite3.connect(CONFIG["database"]) as db:
            db.row_factory = sqlite3.Row
            user_profile = db.execute(
                "SELECT * FROM players WHERE id = ?",
                (self.id,)
            ).fetchone()

            if user_profile is None:
                self.cache_new_user()

            self.name = user_profile['name']
            self.telegram_user = user_profile['telegram_user']
            self.hidden = user_profile['hidden']
            self.gender = user_profile['gender']

            return user_profile

    def cache_new_user(self) -> None:
        """
        updates the database when a new user uses the bot
        """
        with sqlite3.connect(CONFIG["database"]) as db:
            db.execute("BEGIN TRANSACTION")
            data = [self.id, self.username]
            db.execute(
                "INSERT INTO players(id, telegram_user) VALUES (?, ?)", data)

            # insert into access control
            data = [self.id, 0]
            db.execute(
                "INSERT INTO access_control (player_id, control_id ) VALUES (?,?)", data)
            db.commit()
        return None

    def get_user_access(self) -> int:
        """
        get the access of the player
        returns an int
        """
        with sqlite3.connect(CONFIG["database"]) as db:
            access = db.execute(
                "SELECT control_id FROM access_control WHERE player_id = ?", (self.id,)).fetchone()[0]
        return access

    def get_event_dates(self,
                        from_date: date = 0) -> sqlite3.Row:
        """
        get the list of dates from a date
        from_date :datetime.date
        """
        if from_date == 0:
            from_date = date.today()
        event_id = from_date.strftime('%Y%m%d%H%M')

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
            if data is None:
                return dict()

            dict_date = {
                "Field Training": list(),
                "Scrim": list(),
                "Hardcourt/Track": list(),
                "Gym/Pod": list(),
                "Cohesion": list()
            }

            for row_obj in data:
                event_date = datetime.strptime(
                    str(row_obj["id"]), '%Y%m%d%H%M')
                event_type = row_obj["event_type"]
                dict_date[event_type].append(event_date)

        return dict_date


class AdminUser(UserManager):
    def __init__(self, user):
        super().__init__(user)
        token_file = os.path.join('.secrets', 'bot_credentials.json')
        with open(token_file, 'r') as bot_token_file:
            bot_tokens = json.load(bot_token_file)

        self.is_dev = CONFIG['development']
        self.bot_token = bot_tokens['dev_bot']

        if not self.is_dev:
            self.bot_token = bot_tokens['training_bot.py']

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
            yield telegram_user

    def read_msg_from_file(self, date_str: str) -> str:
        """
        reads strings from a txt file
        date_string: text to be replaced in the txt file
        """
        filename = os.path.join("resources", 'messages', 'not_indicated.txt')
        with open(filename, "r", encoding="utf-8") as text_f:
            msg = text_f.read().replace("{date}", date_str).rstrip()
        return msg
