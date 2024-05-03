from sqlalchemy import select, case, collate, not_
from src.Database.DatabaseSession.DatabaseSessionProviding import DatabaseSessionProviding
from src.Database.DatabaseSession.DatabaseSessionProviding import Sqlite3SessionProvider
from src.Models.User import User
from src.Models.Attendance import Attendance
from src.Models.Access import Access

from src.Enum.Enum import Gender
from src.Enum.Enum import AccessCategory


class EventAttendanceService:
    database_session_provider: DatabaseSessionProviding

    def __init__(self, session_provider: DatabaseSessionProviding = Sqlite3SessionProvider()):
        self.database_session_provider = session_provider

    def get_attendances(
            self,
            event_id: int,
            is_attending: bool,
            gender: Gender,
            access_category: AccessCategory = AccessCategory.all
    ) -> list[tuple[User, Access, Attendance]]:
        with self.database_session_provider.make_session() as session:
            statement = (
                select(
                    User,
                    Access,
                    Attendance,
                )
                .join(Attendance, User.id == Attendance.user_id)
                .join(Access, User.id == Access.user_id)
                .where(Attendance.event_id == event_id)
                .where(User.hidden == 0)
                .where(Access.control_id != 7)
                .where(Attendance.status == is_attending)
            )
            if gender != Gender.both:
                statement = statement.where(User.gender == gender.value)

            if access_category == AccessCategory.member:
                statement = statement.filter(
                    Access.control_id >= AccessCategory.member.value
                )

            elif access_category == AccessCategory.guest:
                statement = statement.filter(Access.control_id.between(2, 3))

            elif access_category == AccessCategory.all:
                statement = statement.filter(
                    Access.control_id >= AccessCategory.all.value
                )

            statement = statement.order_by(
                case((Access.control_id >= 4, 0), else_=1),
                User.name,
            )

            user_attendances = session.execute(statement).fetchall()

        return list(user_attendances)

    def get_not_indicated_attendances(
            self,
            event_id: int,
            access: AccessCategory = AccessCategory.member
    ) -> list[tuple[User, Access]]:

        with self.database_session_provider.make_session() as session:
            indicated_statement = (
                select(User.name)
                .join(Attendance, User.id == Attendance.user_id)
                .join(Access, User.id == Access.user_id)
                .where(Attendance.event_id == event_id)
            )

            statement = (
                select(
                    User,
                    Access,
                )
                .join(Access, User.id == Access.user_id)
                .where(
                    not_(User.name.in_(indicated_statement)),
                    User.notification == 1,
                    Access.control_id != 7,
                    User.hidden == 0
                )
            )

            if access == AccessCategory.member:
                statement = statement.filter(
                    Access.control_id >= AccessCategory.member.value
                )

            elif access == AccessCategory.guest:
                statement = statement.filter(Access.control_id.between(2, 3))

            elif access == AccessCategory.all:
                statement = statement.filter(Access.control_id >= 2)

            statement = statement.order_by(
                User.gender.desc(),
                collate(User.name, "NOCASE")
            )

            not_indicated_users = session.execute(statement).fetchall()

        return list(not_indicated_users)
