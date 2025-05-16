from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy import ForeignKey

from src.Database.DatabaseSession.base import Base

from src.Models.User import User
from src.Models.Event import Event

class KaypohMessage(Base):
    __tablename__ = "kaypoh_message"

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey(Event.id), primary_key=True)
    message_id: Mapped[int]

    def __repr__(self) -> str:
        return (f"KaypohMessage(user_id={self.user_id!r},\
                event_id={self.event_id!r},\
                message_id={self.message_id!r}")