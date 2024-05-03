from sqlalchemy import select
from sqlalchemy.sql import exists

from src.Database.DatabaseSession.DatabaseSessionProviding import (DatabaseSessionProviding,
                                                                   Sqlite3SessionProvider)
from src.Models.User import User
from src.Models.Access import Access
from src.Enum.Enum import AccessCategory


class UserDatabaseService:
    database_session_provider: DatabaseSessionProviding = None

    def __init__(self, database_provider: DatabaseSessionProviding = Sqlite3SessionProvider()):
        self.database_session_provider = database_provider

    def insert(self, user: User):
        with self.database_session_provider.make_session() as session:
            session.add(user)
            session.commit()

    def get_user_by(self, user_id: int) -> User:

        session = self.database_session_provider.make_session()
        statement = select(User).where(User.id == user_id)
        user = session.execute(statement).scalar_one()

        session.close()
        return user

    def user_name_exists(self, name: str) -> bool:
        session = self.database_session_provider.make_session()

        # TODO make searches cases sensitive
        statement = exists().where(User.name == name)
        user_exists = self.session.query(statement).scalar()

        session.close()
        return user_exists

    def get_user_by_name(self, name: str) -> User:

        session = self.database_session_provider.make_session()

        statement = select(User).where(User.name == name)
        user = self.session.execute(statement).scalar_one()

        if user is None:
            return None

        session.close()
        return user

    def get_user_access(self, user: User) -> AccessCategory:

        with self.database_session_provider.make_session() as session:
            statement = (
                select(Access)
                .join(User, Access.user_id == User.id)
                .where(Access.user_id == user.id)
            )

            access = session.scalars(statement).one()
            access_category = AccessCategory.enum_from_int(access)

        return access_category

    def get_users_by_access(self, access: AccessCategory) -> list[User]:
        with self.database_session_provider.make_session() as session:
            statement = (
                select(User)
                .join(Access, User.id == Access.user_id)
                .where(Access.control_id == access.value)
            )
            users = session.scalars(statement).all()

        return list(users)

    def update_user(self, updated_user: User):
        session = self.database_session_provider.make_session()
        session.begin()
        session.merge(updated_user)
        session.commit()
        session.close()
        return

    def delete(self, user):
        with self.database_session_provider.make_session() as session:
            session.delete(user)
            session.commit()