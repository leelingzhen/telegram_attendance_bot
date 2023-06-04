import sqlite3
import os
# import logging
import json

from datetime import date, datetime

from telegram.bot import Bot
from telegram.error import Unauthorized, BadRequest
from src.event_manager import TrainingEventManager
import telegram.message


with open("config.json") as f:
    CONFIG = json.load(f)
    db = sqlite3.connect(
        CONFIG['database'],
        check_same_thread=False
    )


class MessageObject:
    """
    Basic message object that keeps the chat_id and message_id
    """

    def __init__(self):

        self.chat_id = None
        self.message_id = None
        self.text = None

    def render_message_elements(self, message_object: telegram.message):
        """
        fill the fields of MessageObject from telegram.message
        """
        self.chat_id = message_object.chat.id
        self.message_id = message_object.chat_id


class KaypohMessage(MessageObject, TrainingEventManager):
    def __init__(self,
                 event_id: int,
                 ):
        TrainingEventManager.__init__(self, event_id)
        with open(os.path.join("resources", "messages", "kaypoh_msg.txt")) as f:
            self.text = f.read()

        token_file = os.path.join('.secrets', 'bot_credentials.json')
        with open(token_file, 'r') as bot_token_file:
            bot_tokens = json.load(bot_token_file)

        self.is_dev = CONFIG['development']
        self.bot_token = bot_tokens['dev_bot']

        if not self.is_dev:
            self.bot_token = bot_tokens['training_bot.py']

    def fill_text_fields(self, date_time_rendered: datetime = None):
        """
        fill text fields inside message template
        """
        if not date_time_rendered:
            date_time_rendered = datetime.now()
        date_time_rendered = date_time_rendered.strftime("%-d-%b %-I:%M%p")

        sep = '\n'
        male_records, female_records, absentees, uninidcated = self.curate_attendance(
            attach_usernames=False)
        total_attendees = len(male_records) + len(female_records)
        pretty_event_date = self.event_date.strftime(
            '%-d-%b-%y, %a @ %-I:%M%p')

        self.text = self.text.replace('{event_type}', self.event_type)
        self.text = self.text.replace('{event_date}', pretty_event_date)
        self.text = self.text.replace(
            '{total_attendees}', str(total_attendees))
        self.text = self.text.replace('{n_male}', str(len(male_records)))
        self.text = self.text.replace('{males}', sep.join(male_records))
        self.text = self.text.replace('{n_female}', str(len(female_records)))
        self.text = self.text.replace('{females}', sep.join(female_records))
        self.text = self.text.replace('{n_absentees}', str(len(absentees)))
        self.text = self.text.replace('{absentees}', sep.join(absentees))
        self.text = self.text.replace('{n_unindicated}', str(len(uninidcated)))
        self.text = self.text.replace('{unindicated}', sep.join(uninidcated))
        self.text = self.text.replace(
            '{date_time_rendered}', date_time_rendered)

    def store_message_fields(self,
                             message_object: telegram.message,
                             ):
        """
        store message id and chat id into KaypohMessageObject
        """
        self.message_id = message_object.message_id
        self.chat_id = message_object.chat.id

    def record_exists(self):
        """
        based on the chat_id and event_id, check if the record exists
        """
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            data = (self.chat_id, self.id)
            record = db.execute(
                "SELECT * FROM kaypoh_messages WHERE player_id = ? and event_id = ?",
                data).fetchone()

        return record is not None

    def add_new_record(self):
        with sqlite3.connect(CONFIG['database']) as db:
            data = (self.chat_id, self.message_id, self.id)
            db.execute(
                'INSERT INTO kaypoh_messages(player_id, message_id, event_id) VALUES (?, ?, ?)', data)

    def update_record(self):
        with sqlite3.connect(CONFIG['database']) as db:
            data = (self.message_id, self.chat_id, self.id)
            db.execute(
                'UPDATE kaypoh_messages SET message_id = ? WHERE player_id = ? and event_id = ?', data)

    def push_record(self):

        if self.record_exists():
            self.update_record()
        else:
            self.add_new_record()

    def update_message(self):
        bot_messenger = Bot(token=self.bot_token)
        try:
            bot_messenger.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=self.text,
                parse_mode='html'
            )
        except BadRequest:
            return "message not changed"
        except Unauthorized:
            return "no such chat found"


class KaypohMessageHandler(KaypohMessage):
    def __init__(self, event_id, rendered_date: datetime = None):
        KaypohMessage.__init__(self, event_id)
        if not rendered_date:
            rendered_date = datetime.now()
        self.records = None
        self.fill_text_fields(rendered_date)

    def get_records(self):
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            self.records = db.execute('SELECT * FROM kaypoh_messages WHERE event_id = ?',
                                      (self.id, )).fetchall()

    def update_all_message_instances(self):
        """
        update all instances of kaypoh messages
        """
        self.get_records()
        for row in self.records:
            self.chat_id = row['player_id']
            self.message_id = row['message_id']
            self.update_message()
