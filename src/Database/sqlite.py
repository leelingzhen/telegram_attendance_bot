import sqlite3
import os
from collections import namedtuple
from datetime import datetime, date


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


class UsersTableSqlite(Sqlite):
    """
    CRUD for Players Table
    """

    def __init__(self):
        super().__init__()
    # CREATING

    def insert_user(
        self,
        id: int,
        telegram_user: str,
        name: str = None,
        gender: str = None,  # Male or Female
        notification: int = 1,
        language_pack: str = 'default',
        hidden: int = 0
    ):
        """
        Inserts a user into the database.

        Args:
            self: The current instance of the class.
            id (int): The user's ID.
            telegram_user (str): The user's Telegram username.
            name (str, optional): The user's name. Defaults to None.
            gender (str, optional): The user's gender. Must be either "Male" or "Female". Defaults to None.
            notification (int, optional): The user's notification preference. Defaults to None.
            language_pack (str, optional): The user's language pack. Defaults to 'default'.
            hidden (int, optional): Flag indicating if the user is hidden. Defaults to 0.

        Returns:
            None

        Raises:
            None
        """
        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(
            "INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id, name, telegram_user, gender,
             notification, language_pack, hidden)
        )
        self.con.commit()

    def get_user_by_id(self, id: int, name=None):
        """
        Retrieve user information based on their ID.

        Args:
            self: The current instance of the class.
            id (int): The user's ID.
            name (str, optional): The user's name. Defaults to None.

        Returns:
            user_data (tuple or None): A tuple containing the user's data retrieved from the database.
                                      Returns None if no user is found.

        Raises:
            None

        """
        query = "SELECT * FROM players WHERE {columns}"

        values = [id]
        columns = ["id = ?"]

        if name is not None:
            values.append(name)
            columns.append("name = ?")

        columns = " AND ".join(columns)

        user_data = self.cur.execute(query.format(
            columns=columns), tuple(values)).fetchone()

        return user_data

    def delete_user_by_id(self, id):
        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute("DELETE FROM players WHERE id = ?", (id, ))
        self.con.commit()

    def update_user(self,
                    id: int,
                    name: str = None,
                    telegram_user: str = None,
                    gender: str = None,
                    notification: int = None,
                    language_pack: str = None,
                    hidden: int = None,
                    ):
        """
        Update user by ID.

        Args:
            self: The current instance of the class.
            id (int): The user's ID.
            name (str, optional): The user's name. Defaults to None.
            telegram_user (str, optional): The user's Telegram username. Defaults to None.
            gender (str, optional): The user's gender. Defaults to None.
            notification (int, optional): The user's notification preference. Defaults to None.
            language_pack (str, optional): The user's language pack. Defaults to None.
            hidden (int, optional): Flag indicating if the user is hidden. Defaults to None.

        Returns:
            None

        Raises:
            None

        """
        query = self.read_query("update_user.sql")
        update_values = []
        update_columns = []

        if name is not None:
            update_values.append(name)
            update_columns.append("name = ?")

        if telegram_user is not None:
            update_values.append(telegram_user)
            update_columns.append("telegram_user = ?")

        if gender is not None:
            update_values.append(gender)
            update_columns.append("gender = ?")

        if notification is not None:
            update_values.append(notification)
            update_columns.append("notification = ?")

        if language_pack is not None:
            update_values.append(language_pack)
            update_columns.append("language_pack = ?")

        if hidden is not None:
            update_values.append(hidden)
            update_columns.append("hidden = ?")

        if not update_values:
            return  # No fields to update

        update_values.append(id)
        update_columns = ", ".join(update_columns)

        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(query.format(
            update_columns=update_columns), tuple(update_values))
        self.con.commit()


class EventsTableSqlite(Sqlite):
    def __init__(self):
        super().__init__()

    def insert_event(
            self,
            id: int,
            event_type: str,
            event_date: str,  # "%Y-%m-%d"
            start_time: str,  # "%H:%M"
            end_time: str,  # "%H:%M"
            location: str,
            access_control: int,
            announcement: str = None
    ):
        """
        Inserts an event into the database.

        Args:
            self: The current instance of the class.
            id (int): The event's ID.
            event_type (str): The type of the event.
            event_date (str): The date of the event in the format "%Y-%m-%d".
            start_time (str): The start time of the event in the format "%H:%M".
            end_time (str): The end time of the event in the format "%H:%M".
            location (str): The location of the event.
            access_control (int): The access control level of the event.
            announcement (str, optional): Additional announcement for the event. Defaults to None.

        Returns:
            None

        Raises:
            ValueError: If the event_date, start_time, or end_time does not match the specified format.

        """
        try:
            datetime.strptime(event_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"event_date: {event_date} format needs to be '%Y-%m-%d'")

        try:
            datetime.strptime(start_time, "%H:%M")
        except ValueError:
            raise ValueError(
                f"start_time: {start_time} does not match '%H:%M"
            )

        try:
            datetime.strptime(end_time, "%H:%M")
        except ValueError:
            raise ValueError(
                f"start_time: {end_time} does not match '%H:%M"
            )

        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (id, event_type, event_date, start_time,
             end_time, location, announcement, access_control)
        )
        self.con.commit()

    def get_event_by_id(self, id: int):
        """
        gets event by id
        """
        event_data = self.cur.execute(
            "SELECT * FROM events WHERE id = ?", (id, )
        ).fetchone()

        return event_data

    # TODO
    def update_event(self):
        pass

    def delete_event_by_id(self, id):
        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute("DELETE FROM events WHERE id = ?", (id, ))
        self.con.commit()


class AttendanceTableSqlite(Sqlite):
    """
    CRUD operations for attendance
    """

    def __init__(self):
        super().__init__()

    def insert_attendance(self,
                          user_id: int,
                          event_id: int,
                          status: int,
                          reason: str
                          ):
        """
        Insert attendance record into the database.

        Args:
            self: The current instance of the class.
            user_id (int): The ID of the user attending the event.
            event_id (int): The ID of the event.
            status (int): The attendance status code.
            reason (str): The reason for the attendance.

        Returns:
            None

        Raises:
            None
        """

        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(
            'INSERT INTO attendance VALUES(?, ?, ?, ?)',
            (event_id, user_id, status, reason)
        )
        self.con.commit()

    def get_attendance(self,
                       user_id: int,
                       event_id: int
                       ):
        """
        get attendance of player on said event
        returns -> dict fields:
            event_id
            player_id
            status
            reason
        """
        attendance_data = self.cur.execute(
            "SELECT * FROM attendance WHERE player_id = ? AND event_id = ?",
            (user_id, event_id)
        ).fetchone()

        return attendance_data

    def update_attendance(
            self,
            user_id: int,
            event_id: int,
            status: int,
            reason: str
    ):
        """
        Update attendance record in the database.
        only status and reason can be updated

        Args:
            self: The current instance of the class.
            player_id (int): The ID of the player.
            event_id (int): The ID of the event.
            status (int): The new attendance status code.
            reason (str): The new reason for the attendance.

        Returns:
            None

        Raises:
            None
        """
        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(
            'UPDATE attendance SET status = ?, reason = ? WHERE event_id = ? AND player_id = ?',
            (status, reason, event_id, user_id)
        )
        self.con.commit()

    def delete_attendance(self, user_id, event_id):
        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(
            "DELETE FROM attendance WHERE player_id = ? AND event_id = ?",
            (user_id, event_id)
        )
        self.con.commit()


class AccessTableSqlite(Sqlite):
    def __init__(self):
        super().__init__()

    def insert_access(self, user_id: int, access: int):
        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(
            "INSERT INTO access_control VALUES (?, ?)",
            (user_id, access)
        )
        self.con.commit()

    def get_access(self, user_id):
        """
        get access of a user

        returns -> dict fields:
            player_id
            control_id
        """
        access_data = self.cur.execute(
            "SELECT * FROM access_control WHERE player_id = ?",
            (user_id, )).fetchone()

        return access_data

    def get_position(self, access) -> str:
        """
        get the position of an access
        """
        position = self.cur.execute(
            "SELECT * FROM access_control_description WHERE id = ?", (access, )
        ).fetchone()
        return position['description']

    def update_access(self, user_id, new_access):
        """
        Update access record in the database.
        only access can be updated

        Args:
            user_id (int): The ID of the player.
            new_access (int): the new access of the target user.

        Returns:
            None

        Raises:
            None
        """

        self.cur.execute('BEGIN TRANSACTION')
        self.cur.execute(
            "UPDATE access_control SET control_id = ? WHERE player_id = ?",
            (new_access, user_id)
        )
        self.con.commit()

    def delete_user_access(self, id):
        self.cur.execute("BEGIN TRANSACTION")
        self.cur.execute(
            "DELETE FROM access_control WHERE player_id = ?", (id, ))
        self.con.commit()


class SqliteUserManager(
        UsersTableSqlite,
        EventsTableSqlite,
        AccessTableSqlite,
        AttendanceTableSqlite
):
    """
    sqlite3 connector for User Manager methods
    """

    def __init__(self):
        super().__init__()

    # QUERYING

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

    def get_attending_events(
        self,
        user_id: int,
        event_id: int,
        access: int
    ):
        """
        Retrieve a list of events that the user is attending.

        Args:
            self: The current instance of the class.
            user_id (int): The ID of the user.
            event_id (int): The minimum event ID to filter the results.
            access (int): The access control level.

        Returns:
            data (list): A list of tuples containing the event IDs and types that match the specified criteria.

        Raises:
            None
        """
        query = self.read_query("user_attending_events.sql")
        data = self.cur.execute(
            query,
            (user_id, event_id, 1, access)
        ).fetchall()

        return data
