import sqlite3
import os
from collections import namedtuple


class Sqlite:
    """
    sqlite3 DB connector
    """

    def __init__(self):

        self.con = sqlite3.connect(os.path.join('resources', 'attendance.db'))
        self.con.row_factory = self.namedtuple_factory
        self.cur = self.con.cursor()

    def read_query(self, q_file: str) -> str:
        """
        reads the query file from q_file
        returns the content of the file in a string
        """

        query_dir = os.path.join(
            'src', 'Database', 'queries', q_file
        )

        with open(query_dir) as f:
            query = f.read()

        return query

    def namedtuple_factory(self, cursor, row):
        fields = [column[0] for column in cursor.description]
        cls = namedtuple("Row", fields)
        return cls._make(row)

    def get_attendance_members(
            self,
            event_id: int,
            attendance: int,
            gender: str
    ):
        """
        gets the attendance from db given the event_id
        only gets members, access control > 4

        returns: sqlite3 table, fields:
            id
            name
            gender
            telegram_user
            control_id
            status
            reason
        """
        query = self.read_query("members_attendance.sql")
        data = (event_id, attendance, gender)
        player_data = self.cur.execute(query, data).fetchall()

        return player_data
