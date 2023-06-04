import sqlite3
# import os
# import logging
import json

from datetime import datetime, timedelta
from telegram import MessageEntity


with open("config.json") as f:
    CONFIG = json.load(f)
    db = sqlite3.connect(
        CONFIG['database'],
        check_same_thread=False
    )


class AttendanceManager:
    """
    Attendance record that is similar to the fields
    in the table 'attendance'

    support pulling and pushing data to the db
    """

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


class EventManager:
    """
    Event manager that has the barebones functionality of the event
    fields in this class match the fields of the table in 'events'

    pull an existing record from the db to fill up existing fields,
    other wise class fields will be all empty
    """

    def __init__(self, event_id: int, record_exist=False):
        self.id = event_id
        self.record_exist = record_exist

        self.event_date = None
        self.start_time = None
        self.end_time = None  # event end timing, type datetime
        self.event_type = None  # type str
        self.location = None  # type str
        self.announcement = None  # str
        self.announcement_entities = None  # list of telegram.Message
        self.access_control = None  # type int

    def parse_event_date(self, duration: int):
        string_id = str(self.id)
        event_date = datetime.strptime(string_id, '%Y%m%d%H%M')
        self.event_date = event_date
        self.start_time = event_date
        self.end_time = event_date + timedelta(hours=duration)
        return event_date

    def print(self):
        print(self.id)
        print(self.record_exist)
        print(self.event_date)
        print(self.start_time)
        print(self.end_time)  # event end timing, type datetime
        print(self.event_type)  # type str
        print(self.location)  # type str
        print(self.announcement)  # str
        print(self.announcement_entities)  # list of telegram.Message
        print(self.access_control)  # type int

    def set_id(self,
               id: int = None,
               event_date=None):
        """
        set the id based on a datetime object or int
        only use either of the args
        """
        if id and event_date:
            raise "Only use one of the fields"
        if event_date:
            id = event_date.strftime("%Y%m%d%H%M")
        self.id = id

    def set_event_date(self, event_date: datetime):
        """
        sets both event_date and startime fields
        """
        self.event_date = event_date
        self.start_time = event_date

    def replace_end_time(self, end_time: datetime):
        """
        used to fill event_end
        """
        event_date = self.event_date
        event_date = event_date.replace(
                hour=end_time.hour,
                minute=end_time.minute
                )
        return event_date

    def set_event_end(self, event_end: datetime):
        self.end_time = event_end

    def set_event_type(self, event_type: str):
        self.event_type = event_type

    def set_location(self, location: str):
        self.location = location

    def set_announcement(self, announcement: str):
        self.announcement = announcement

    def set_access(self, access: int):
        self.access_control = access

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

    def pull_event(self):
        """
        get the event from db
        schema of query:
            CREATE TABLE events(
                id LONGINT,
                event_type TEXT,
                event_date DATE,
                start_time TIME,
                end_time TIME DEFAULT '00:00',
                location TEXT,
                announcement TEXT,
                access_control INT DEFAULT 2,
                PRIMARY KEY(id)

        returns: bool = True if record exists
        """
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            data = db.execute(
                "SELECT * FROM events WHERE id = ?", (self.id, )).fetchone()
            if data is None:
                self.record_exist = False
                return False

            # event end timing, type datetime
            self.event_date = datetime.strptime(data["event_date"], "%Y-%m-%d")
            self.start_time = datetime.strptime(data["start_time"], "%H:%M")
            self.end_time = datetime.strptime(data["end_time"], "%H:%M")
            self.event_type = data["event_type"]
            self.announcement = data["announcement"]  # str
            self.location = data["location"]
            self.announcement_entities = None  # list of telegram.Message
            self.access_control = data["access_control"]  # type int

            self.record_exist = True
            self.correct_event_date()
            return True

    def correct_event_date(self):
        event_date = self.event_date
        event_date = event_date.replace(
            hour=self.start_time.hour,
            minute=self.start_time.minute
            )
        self.event_date = event_date
        self.start_time = event_date



class TrainingEventManager(EventManager):
    """
    Event manager used for the training bot
    an instance of this class is instantiated only if the event
    already exists in the db, where all the fields of this class are
    automatically filled

    this class has methods to query for indicated, attending, absent players
    to this instance of the class
    """

    def __init__(self, event_id, record_exist=True):

        EventManager.__init__(self, event_id, record_exist=record_exist)
        self.pull_event()
        self.generate_entities()

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

                entry = f"{entry} - {telegram_user}"

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


class AdminEventManager(TrainingEventManager, EventManager):
    """
    class instance for the manager of an event by an admin
    only in this class can you push changes to events in the db

    if the class is instantiated with records_exists=False
    an empty record is created with all fields blank

    can query for user attendance for an event like the TrainingEventManager
    """

    def __init__(self, id, record_exist=False):
        if record_exist:
            # parses all the fields
            TrainingEventManager.__init__(self, id, record_exist=record_exist)
        else:
            # keeps all the fields empty
            EventManager.__init__(self, id, record_exist=record_exist)
        self.original_id = self.id

    def new_event_parse(self,
                        event_type="Field Training",
                        access_control=2
                        ):
        """
        parse fields for uncreated events
        """
        self.parse_event_date(duration=2)
        self.set_event_type(event_type)
        self.set_access(access_control)

    def parse_event_date(self, duration: int):
        string_id = str(self.id)
        event_date = datetime.strptime(string_id, '%Y%m%d%H%M')
        self.event_date = event_date
        self.start_time = event_date
        self.end_time = event_date + timedelta(hours=duration)
        return event_date

    def set_entities(self, entities: list):
        self.announcement_entities = entities

    def update_event_records(self):
        data = [
            self.id,
            self.event_type,
            self.event_date.strftime("%Y-%m-%d"),
            self.start_time.strftime("%H:%M"),
            self.end_time.strftime("%H:%M"),
            self.location,
            self.announcement,
            self.access_control,
            self.original_id
        ]

        with sqlite3.connect(CONFIG['database']) as db:
            # updating events table
            db.execute(
                "UPDATE events SET id = ?, event_type = ?, event_date = ?, start_time = ?, end_time = ?, location = ?, announcement = ?, access_control = ? WHERE id = ?", data)

            # updating attendance table
            db.execute(
                "UPDATE attendance SET event_id = ? WHERE event_id = ?", (self.id, self.original_id))

            db.commit()

    def check_conflicts(self):
        """
        before pushing updates to the db, check if
        there are any conflicts with records
        when inserting a new event,
        we dont want to insert an event that already exists

        when updating an event to another date,
        we want to make sure the updated start
        datetime does not clash with existing records

        returns True if conflicts exist

        """

        # check conflicts when updating cur event
        if self.record_exist and self.original_id != self.id:
            with sqlite3.connect(CONFIG['database']) as db:
                db.row_factory = sqlite3.Row

                data = db.execute('SELECT * FROM events WHERE id = ?',
                                  (self.id, )).fetchall()
                if data:
                    return True

        # checking conflicts when inserting a new event
        if not self.record_exist:
            with sqlite3.connect(CONFIG['database']) as db:
                db.row_factory = sqlite3.Row
                data = db.execute('SELECT * FROM events WHERE id = ?',
                                  (self.id, )).fetchall()
                if data:
                    return True

        # at this time, the record exists but there is no change to the
        # datetime, return False
        return False

    def add_new_event(self):
        data = [
            self.id,
            self.event_type,
            self.event_date.strftime("%Y-%m-%d"),
            self.start_time.strftime("%H:%M"),
            self.end_time.strftime("%H:%M"),
            self.location,
            self.announcement,
            self.access_control,
        ]
        with sqlite3.connect(CONFIG['database']) as db:
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", data)
            db.commit()

    def push_event_announcement(self):
        with sqlite3.connect(CONFIG['database']) as db:
            data = (self.announcement, self.id)
            db.execute("UPDATE events SET announcement = ? WHERE id = ?", data)
            db.commit()

    def push_event_to_db(self):
        if self.record_exist:
            self.update_event_records()
        else:
            self.add_new_event()

    def remove_event_from_record(self):

        with sqlite3.connect(CONFIG['database']) as db:
            db.execute("BEGIN TRANSACTION")
            db.execute("DELETE FROM events WHERE id = ?", (self.original_id, ))
            db.execute("DELETE FROM attendance WHERE event_id = ?",
                       (self.original_id, ))
            db.execute(
                "DELETE FROM announcement_entities WHERE event_id = ?",
                (self.original_id, ))
            db.commit()

    def push_announcement_entities(self):
        if not self.announcement_entities:
            return
        entity_data = list()
        for entity in self.announcement_entities:

            data = (self.id, entity.type, entity.offset, entity.length)
            entity_data.append(data)

        if self.announcement_entities is None:
            self.generate_entities()

        with sqlite3.connect(CONFIG['database']) as db:
            db.execute(
                "DELETE FROM announcement_entities WHERE event_id = ?", (self.id, ))
            db.executemany(
                "INSERT INTO announcement_entities VALUES (?, ?, ?, ?)", entity_data)
            db.commit()
