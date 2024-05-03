from sqlalchemy import select

from src.Database.DatabaseSession.DatabaseSessionProviding import DatabaseSessionProviding
from src.Database.DatabaseSession.DatabaseSessionProviding import Sqlite3SessionProvider
from src.Models.KaypohMessage import KaypohMessage


class KaypohService:
    database_session_provider: DatabaseSessionProviding

    def __init__(self, session_provider: DatabaseSessionProviding = Sqlite3SessionProvider()):
        self.database_session_provider = session_provider

    def insert(self, kaypoh_message: KaypohMessage):
        with self.database_session_provider.make_session() as session:
            session.begin()
            session.add(kaypoh_message)
            session.commit()

    def get_message(self, user_id: int, event_id: int) -> KaypohMessage:

        with self.database_session_provider.make_session() as session:
            statement = (
                select(KaypohMessage)
                .where(KaypohMessage.user_id == user_id)
                .where(KaypohMessage.event_id == event_id)
            )

            message = session.scalars(statement).one()
        return message

    def get_messages_by_event(self, event_id) -> list[KaypohMessage]:

        with self.database_session_provider.make_session() as session:
            statement = (
                select(KaypohMessage)
                .where(KaypohMessage.event_id) == event_id
            )

            messages = session.scalars(statement).all()
        return list(messages)

    def update(self, kaypoh_message: KaypohMessage):

        with self.database_session_provider.make_session() as session:
            session.begin()
            session.merge(kaypoh_message)
            session.commit()

    def delete(self, kaypoh_message: KaypohMessage):

        with self.database_session_provider.make_session() as session:
            session.begin()
            session.delete(kaypoh_message)
            session.commit()