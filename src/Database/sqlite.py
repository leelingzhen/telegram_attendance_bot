import sqlite3
import os
from collections import namedtuple


class Sqlite:
    """
    sqlite3 DB connector
    """

    def __init__(self, testing=False):

        self.con = sqlite3.connect(os.path.join('resources', 'attendance.db'))
        # self.con.row_factory = self.namedtuple_factory
        self.con.row_factory = sqlite3.Row
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


class SqliteUserManager(Sqlite):
    """
    sqlite3 connector for usermanager methods
    """

    def __init__(self):
        super().__init__()

    # QUERYING
    def get_user_profile(self, **kwargs):
        """
        get all the player data from the db

        params = user_id, name
        returns sqlite3.Row, fields:
            name
            telegram_user
            hidden
            gender
            notification
            language
        """
        # TODO build some custom errors
        if 'user_id' not in kwargs:
            raise SyntaxError

        if len(kwargs) == 1:

            user_data = self.cur.execute(
                "SELECT * FROM players WHERE id = ?",
                (kwargs['user_id'], )
            ).fetchone()

        if len(kwargs) == 2:
            user_data = self.cur.execute(
                "SELECT * FROM players WHERE id = ? AND name = ?",
                (kwargs['user_id'], kwargs['name'])
            ).fetchone()

        return user_data

    def get_user_access(self, user_id):
        """
        get the access control of the user
        """
        access = self.cur.execute(
            "SELECT control_id FROM access_control WHERE player_id = ?",
            (user_id,)).fetchone()
        if not access:
            return 0
        return access['control_id']

    def get_future_events(self, event_id, access):
        """
        get event records which are greater than event_id
        returns sqlite3
        """
        query = self.read_query('future_events.sql')
        event_data = self.cur.execute(query, (event_id, access)).fetchall()

        return event_data

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
