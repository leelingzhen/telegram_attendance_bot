from sqlalchemy import select
from sqlalchemy.sql import exists

from src.Database.DatabaseSession.DatabaseSessionProviding import DatabaseSessionProviding
from src.Database.DatabaseSession.DatabaseSessionProviding import Sqlite3SessionProvider
from src.Models.Event import Event
from src.Enum.Enum import AccessCategory
from abc import ABC, abstractmethod


class EventServicing(ABC):

    @abstractmethod
    def get_after(self, event_id: int, access: AccessCategory) -> list[Event]:
        pass


class EventService:
    database_session_provider: DatabaseSessionProviding

    def __init__(
            self,
            session_provider: DatabaseSessionProviding = Sqlite3SessionProvider()
    ):
        self.database_session_provider = session_provider

    def insert(self, event: Event):
        with self.database_session_provider.make_session() as session:
            session.begin()
            session.add(event)
            session.commit()

    def get(self, event_id: int) -> Event:
        with self.database_session_provider.make_session() as session:
            statement = select(Event).where(Event.id == event_id)

            event = session.execute(statement).scalar_one()

        return event

    def get_after(self, event_id: int, access: AccessCategory) -> list[Event]:
        with self.database_session_provider.make_session() as session:
            statement = (
                select(Event)
                .filter(Event.id >= event_id)
                .filter(Event.access_control < access.value)
            )
            events = session.scalars(statement).all()
        return list(events)

    def exists(self, event_id: int) -> bool:
        with self.database_session_provider.make_session() as session:
            statement = exists().where(Event.id == event_id)

            is_event_exists = session.query(statement).scalar()

        return is_event_exists

    def update(self, event: Event):

        with self.database_session_provider.make_session() as session:
            session.begin()
            session.merge(event)
            session.commit()

        return

    def delete(self, event: Event):

        with self.database_session_provider.make_session() as session:
            session.begin()
            session.delete(event)
            session.commit()
        return
