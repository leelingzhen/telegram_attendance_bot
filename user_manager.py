import sqlite3
import os
import logging
import json

from datetime import date, datetime


with open("config.json") as f:
    CONFIG = json.load(f)
    db = sqlite3.connect(
        CONFIG['database'],
        check_same_thread=False
    )


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

    def retrieve_user_data(self) -> list:
        """
        retrieve user data from the db
        returns user profiles in a list
        [id, name, telegram_user, language_pack]
        """

        with sqlite3.connect(CONFIG["database"]) as db:
            user_profile = db.execute(
                "SELECT id, name, telegram_user, language_pack FROM players WHERE id = ?",
                (self.id,)
            ).fetchone()

            if user_profile is None:
                self.cache_new_user()
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
