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
        self.access_control = event["access_control"]

    def get_event_by_id(self, id: int) -> sqlite3.Row:
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            event = db.execute(
                "SELECT * FROM events WHERE id = ?", (id, )).fetchone()
        return event

    def get_member_attendance(self,
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
                    name, gender, telegram_user,
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

    def get_guest_attendance(self,
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
                    name, gender, telegram_user,
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

    def get_unindicated(self, event_id: int = None):
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

    def curate_attendance(self, attach_usernames: int = True) -> list:
        """
        queries all the attendance for the said event
        attach_usernames will attach user names to uninidcaited players

        returns a formatted list of players and reasons
        """
        male_records = list()
        female_records = list()
        absentees = list()
        unindicated = list()

        male_members = self.get_member_attendance(attendance=1, gender="Male")
        male_records = self.attendance_to_str(male_members)

        male_guests = self.get_guest_attendance(attendance=1, gender="Male")
        male_records += self.attendance_to_str(male_guests)

        female_members = self.get_member_attendance(attendance=1, gender="Female")
        female_records = self.attendance_to_str(female_members)

        female_guests = self.get_guest_attendance(
            attendance=1, gender="Female")
        female_records += self.attendance_to_str(female_guests)

        absentees = self.get_member_attendance(attendance=0, gender="Male")
        absentees += self.get_member_attendance(attendance=0, gender="Female")

        absentees = self.attendance_to_str(absentees)

        unindicated = self.get_unindicated()
        unindicated = self.attendance_to_str(
            unindicated, attach_usernames=attach_usernames)

        return male_records, female_records, absentees, unindicated
