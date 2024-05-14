from sqlalchemy import select
from sqlalchemy.sql import exists

from src.Database.DatabaseSession.DatabaseSessionProviding import (DatabaseSessionProviding,
                                                                   Sqlite3SessionProvider)
from src.Models.User import User
from src.Models.Access import Access
from src.Enum.Enum import AccessCategory

from abc import ABC, abstractmethod


class AccessServicing(ABC):

    @abstractmethod
    def insert(self, access: AccessCategory):
        pass

    @abstractmethod
    def get_access_of(self, user_id: int) -> AccessCategory:
        pass

    @abstractmethod
    def update(self, access: Access):
        pass

    @abstractmethod
    def delete(self, access: Access):
        pass


class AccessService(AccessServicing):

    def __init__(self, session_provider: DatabaseSessionProviding = Sqlite3SessionProvider()):
        self.database_session_provider = session_provider

    def insert(self, access: Access):
        with self.database_session_provider.make_session() as session:
            session.begin()
            session.add(access)
            session.commit()
        return

    def get_access_of(self, user_id: int) -> AccessCategory:
        with self.database_session_provider.make_session() as session:

            statement = select(Access).where(Access.user_id == user_id)
            access = session.scalars(statement).one()

        return AccessCategory.enum_from_int(access.control_id)

    def update(self, access: Access):
        with self.database_session_provider.make_session() as session:
            session.begin()
            session.merge(access)
            session.commit()

        return

    def delete(self, access: Access):
        with self.database_session_provider.make_session() as session:
            session.begin()
            session.delete(access)
            session.commit()

        return