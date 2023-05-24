import sqlite3
import os
import logging
import json

from datetime import date, datetime
from telegram import MessageEntity


with open("config.json") as f:
    CONFIG = json.load(f)
    db = sqlite3.connect(
        CONFIG['database'],
        check_same_thread=False
    )


class AttendanceManager:
    def __init__(self, player_id, event_id):
        self.player_id = player_id
        self.event_id = event_id
        self.exists = False
        self.status = -1
        self.reason = ""

        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            data = db.execute(
                "SELECT status, reason FROM attendance WHERE event_id = ? and player_id = ?",
                (event_id, player_id)).fetchone()
            if data:
                self.exists = True
                self.status = data['status']
                self.reason = data['reason']

    def get_status(self):
        return self.status

    def record_exists(self):
        return self.exists

    def is_attending(self):
        return self.status

    def set_status(self, status: int):
        self.status = status

    def set_reason(self, reason: str):
        self.reason = reason

    def pretty_attendance(self) -> str:
        status = "Not Indicated"

        if self.status > -1:
            status = "Yes" if self.status else "No"

        reason = ""
        if self.reason:
            reason = f" ({self.reason})"

        return f"{status}{reason}"

    def print(self):
        text = f"exists: {self.exists}\n"
        text += f"status: {self.status}\n"
        text += f"reason: {self.reason}\n"
        print(text)

    def update_records(self):

        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            db.execute("BEGIN TRANSACTION")
            if self.record_exists():
                data = (self.status,
                        self.reason,
                        self.event_id,
                        self.player_id
                        )
                db.execute(
                    "UPDATE attendance SET status = ?, reason = ? WHERE event_id = ? AND player_id = ?", data)
            else:
                data = (
                    self.event_id,
                    self.player_id,
                    self.status,
                    self.reason,
                )
                db.execute(
                    "INSERT INTO attendance (event_id, player_id, status, reason) VALUES (?, ?, ?, ?)", data)
            db.commit()


class TrainingEventManager:
    def __init__(self, id):
        self.id = id

        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            event = db.execute(
                "SELECT * FROM events WHERE id = ?", (id, )).fetchone()
        self.event_type = event["event_type"]
        self.event_date = datetime.strptime(event["event_date"], "%Y-%m-%d")
        self.start_time = datetime.strptime(event["start_time"], "%H:%M")
        self.end_time = datetime.strptime(event["end_time"], "%H:%M")
        self.location = event["location"]
        self.announcement = event["announcement"]
        self.announcement_entities = None
        self.access_control = event["access_control"]

    def generate_entities(self):
        entities = list()

        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row

            data = db.execute(
                "SELECT * FROM announcement_entities WHERE event_id = ?", (
                    self.id, )
            ).fetchall()

            if data is None:
                return None

            for entity in data:
                entities.append(
                    MessageEntity(
                        type=entity['entity_type'],
                        offset=entity['offset'],
                        length=entity['entity_length']
                    )
                )
        self.announcement_entities = entities
        return entities

    def pretty_start(self) -> str:
        return self.start_time.strftime("%-I:%M%p")

    def pretty_end(self) -> str:
        return self.end_time.strftime("%-I:%M%p")

    def get_event_date(self) -> datetime:
        """
        return the datetime object of the event
        """
        output = self.event_date
        output = self.event_date.replace(
            hour=self.start_time.hour,
            minute=self.start_time.minute
        )

        return output

    def get_event_by_id(self, id: int) -> AttendanceManager:
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            event = db.execute(
                "SELECT * FROM events WHERE id = ?", (id, )).fetchone()
        return event

    def attendance_of_members(self,
                              attendance: int,
                              gender: str,
                              event_id: int = None,
                              ):
        """
        query attendance from db
        event_id: format %Y%m%d%H%M
        attendance: 1 for attending 0 for absentees
        gender: either Male or Female
        """
        if event_id is None:
            event_id = self.id
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            player_data = db.execute("""
                SELECT
                    id, name, gender, telegram_user,
                    access_control.control_id,
                    attendance.status, attendance.reason
                FROM players
                JOIN attendance on players.id = attendance.player_id
                JOIN access_control on players.id = access_control.player_id
                WHERE event_id = ?
                AND players.hidden = 0
                AND access_control.control_id != 7
                AND attendance.status = ?
                AND gender = ?
                AND access_control.control_id > 3
                ORDER BY
                players.name,
                players.gender DESC

                       """, (event_id, attendance, gender,)).fetchall()
        return player_data

    def attendance_of_guests(self,
                             attendance: int,
                             gender: str,
                             event_id: int = None,
                             ):
        """
        query attendance from db
        event_id: format %Y%m%d%H%M
        attendance: 1 for attending 0 for absentees
        gender: either Male or Female
        """
        if event_id is None:
            event_id = self.id
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            player_data = db.execute("""
                SELECT
                    id, name, gender, telegram_user,
                    access_control.control_id,
                    attendance.status, attendance.reason
                FROM players
                JOIN attendance on players.id = attendance.player_id
                JOIN access_control on players.id = access_control.player_id
                WHERE event_id = ?
                AND players.hidden = 0
                AND attendance.status = ?
                AND gender = ?
                AND access_control.control_id >= 2
                AND access_control.control_id <4
                ORDER BY
                players.name COLLATE NOCASE,
                players.gender DESC

                       """, (event_id, attendance, gender,)).fetchall()
        return player_data

    def unindicated_members(self, event_id: int = None) -> sqlite3.Row:
        """
        returns a list of unindicated members 
        """
        if event_id is None:
            event_id = self.id
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            player_data = db.execute("""
                    SELECT id, name, telegram_user,
                    access_control.control_id
                    FROM players
                    JOIN access_control on players.id = access_control.player_id
                    WHERE name NOT IN
                    (
                        SELECT name FROM players
                        JOIN attendance ON players.id = attendance.player_id
                        JOIN access_control ON players.id = access_control.player_id
                        WHERE event_id=?
                    )
                    AND notification == 1
                    AND access_control.control_id >= 4
                    AND access_control.control_id != 7
                    AND players.hidden = 0
                    ORDER BY
                    players.gender DESC,
                    players.name COLLATE NOCASE

                             """, (self.id, )).fetchall()
        return player_data

    def attendance_to_str(self,
                          player_data: sqlite3.Row,
                          attach_usernames: bool = False
                          ) -> list:
        """
        change sql queries to txt for printing
        """

        formatted_attendance = list()

        for record in player_data:
            entry = record['name']

            if "reason" not in record.keys():
                pass
            elif record["reason"] != "":
                entry += f"({record['reason']})"

            if record['control_id'] < 4:
                entry = f"(guest) {entry}"

            if attach_usernames or record['control_id'] < 4:
                if not record['telegram_user']:
                    telegram_user = "privated"
                else:
                    telegram_user = f"@{record['telegram_user']}"

                entry = f"{entry} - @{telegram_user}"

            formatted_attendance.append(entry)

        return formatted_attendance

    def curate_attendance(self, attach_usernames: int = True) -> tuple:
        """
        queries all the attendance for the said event
        attach_usernames will attach user names to uninidcaited players

        returns a formatted list of players and reasons
        """
        male_records = list()
        female_records = list()
        absentees = list()
        unindicated = list()

        male_members = self.attendance_of_members(attendance=1, gender="Male")
        male_records = self.attendance_to_str(male_members)

        male_guests = self.attendance_of_guests(attendance=1, gender="Male")
        male_records += self.attendance_to_str(male_guests)

        female_members = self.attendance_of_members(
            attendance=1, gender="Female")
        female_records = self.attendance_to_str(female_members)

        female_guests = self.attendance_of_guests(
            attendance=1, gender="Female")
        female_records += self.attendance_to_str(female_guests)

        absentees = self.attendance_of_members(attendance=0, gender="Male")
        absentees += self.attendance_of_members(attendance=0, gender="Female")
        absentees += self.attendance_of_guests(attendance=0, gender="Male")
        absentees += self.attendance_of_guests(attendance=0, gender="Female")

        absentees = self.attendance_to_str(absentees)

        unindicated = self.unindicated_members()
        unindicated = self.attendance_to_str(
            unindicated, attach_usernames=attach_usernames)

        return male_records, female_records, absentees, unindicated


class AdminEventManager(TrainingEventManager):
    def __init__(self, id, exists=True):
        super().__init__(id)
        self.exists = exists

    def update_announcement_entities(self, msg, entity_data=None):

        new_entity_data = list()
        for entity in entity_data:
            data = (self.id, entity.type, entity.offset, entity.length)
            new_entity_data.append(data)

        if self.announcement_entities is None:
            self.generate_entities()

        # change implementation of this
        # want to have a method to update the record as a whole
        # might have to change the definition of TrainingEventManager Class
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row

            db.execute("DELETE FROM announcement_entities WHERE event_id = ?", (self.id, ))

            if new_entity_data:
                db.executemany("INSERT INTO announcement_entities VALUES (?, ?, ?, ?)", new_entity_data)
            db.execute('UPDATE events SET announcement = ? WHERE id = ?', (msg, self.id))
            db.commit()


 
