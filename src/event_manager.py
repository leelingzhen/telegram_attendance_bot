import sqlite3
# import os
# import logging
import json

from datetime import datetime, timedelta
from telegram import MessageEntity
import src.Database.sqlite


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

    def __init__(
            self,
            user_id,
            event_id,
            db=src.Database.sqlite.AttendanceTableSqlite()
    ):
        self.db = db
        self.user_id = user_id
        self.event_id = event_id
        self.exists = False
        self.status = -1
        self.reason = ""

        attendance_data = self.db.get_attendance(user_id, event_id)
        if attendance_data:
            self.exists = True
            self.status = attendance_data['status']
            self.reason = attendance_data['reason']

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
        """
        push attendance update to the db
        """

        if self.record_exists():
            self.db.update_attendance(
                user_id=self.user_id,
                event_id=self.event_id,
                status=self.status,
                reason=self.reason
            )
        else:
            self.db.insert_attendance(
                user_id=self.user_id,
                event_id=self.event_id,
                status=self.status,
                reason=self.reason
            )


class EventManager:
    """
    Event manager that has the barebones functionality of the event
    fields in this class match the fields of the table in 'events'

    pull an existing record from the db to fill up existing fields,
    other wise class fields will be all empty
    """

    def __init__(
            self,
            event_id: int,
            record_exist=False,
            db=src.Database.sqlite.SqliteEventManager()
    ):
        # DB connector
        self.db = db

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

        data = self.db.get_announcement_entities(self.id)
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
        data = self.db.get_event_by_id(self.id)
        if not data:
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

    def unindicated_members(self, event_id: int = None) -> sqlite3.Row:
        """
        returns a list of unindicated members
        """
        player_data = self.db.get_unindicated_users(
            event_id=self.id, access_cat='members')
        return player_data

    def attendance_to_str(self,
                          user_data: sqlite3.Row,
                          attach_usernames: bool = False
                          ) -> list:
        """
        change sql queries to txt for printing
        """

        formatted_attendance = list()

        for record in user_data:
            entry = record['name']

            if "reason" not in record.keys():
                pass
            elif record["reason"] != "":
                entry += f" ({record['reason']})"

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

    def compile_attendance_by_cat(
            self,
            attendance: int,
            gender: str,
            access_cat: str = 'all'
    ):
        """
        attendance can be int or none
        """
        if attendance is not None:
            data = self.db.get_users_on_attendance_access(
                event_id=self.id,
                attendance=attendance,
                gender=gender,
                access_cat=access_cat
            )
        else:
            data = self.db.get_unindicated_users(
                event_id=self.id,
                access_cat=access_cat
            )

        return self.attendance_to_str(data)

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

        male_records = self.compile_attendance_by_cat(
            attendance=1,
            gender='male',
            access_cat='all'
        )

        female_records = self.compile_attendance_by_cat(
            attendance=1,
            gender='female',
            access_cat='all'
        )

        absentees = self.compile_attendance_by_cat(
            attendance=0,
            gender='both',
            access_cat='all'
        )

        unindicated = self.compile_attendance_by_cat(
            attendance=None,
            gender='both',
            access_cat='member'
        )

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
