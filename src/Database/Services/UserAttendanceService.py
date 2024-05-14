from sqlalchemy import select, Exists
from sqlalchemy.orm import Query
from sqlalchemy.sql import exists
from src.Database.DatabaseSession.DatabaseSessionProviding import (DatabaseSessionProviding,
                                                                   Sqlite3SessionProvider)
from src.Models.Attendance import Attendance


class UserAttendanceService:
    database_session_provider: DatabaseSessionProviding

    def __init__(self, database_session_provider: DatabaseSessionProviding = Sqlite3SessionProvider()):
        self.database_session_provider = database_session_provider

    def insert(self, attendance: Attendance):
        session = self.database_session_provider.make_session()
        session.add(attendance)
        session.commit()
        session.close()

    def get_attendance(self, event_id: int = None, user_id: int = None, status: int = None) -> list[Attendance]:
        session = self.database_session_provider.make_session()

        statement = select(Attendance)

        if not event_id and not user_id and not status:
            return []
        if event_id:
            statement = statement.where(Attendance.event_id == event_id)
        if user_id:
            statement = statement.where(Attendance.user_id == user_id)
        if status:
            statement = statement.where(Attendance.status == status)
        user_attendance = session.scalars(statement).all()
        session.close()

        return list(user_attendance)

    def get_attendance_after(self, event_id: int, user_id: int) -> list[Attendance]:
        with self.database_session_provider.make_session() as session:
            statement = (
                select(Attendance)
                .where(Attendance.user_id == user_id)
                .where(Attendance.event_id >= event_id)
            )
            user_attendance = session.scalars(statement).all()
        return list(user_attendance)

    def is_record_exists(self, user_id: int, event_id: int) -> bool:
        session = self.database_session_provider.make_session()
        statement = (
            exists()
            .where(Attendance.user_id == user_id)
            .where(Attendance.event_id == event_id)
        )
        is_attendance_exists = session.query(statement).scalar()
        session.close()
        return is_attendance_exists

    def update(self, attendances: [Attendance]):
        with self.database_session_provider.make_session() as session:
            session.begin()
            for attendance in attendances:
                session.merge(attendance)

            session.commit()

    def delete(self, attendance: Attendance):
        with self.database_session_provider.make_session() as session:
            session.begin()
            session.delete(attendance)
            session.commit()

