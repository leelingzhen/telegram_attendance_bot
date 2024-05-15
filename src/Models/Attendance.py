from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy import ForeignKey

from src.Database.DatabaseSession.base import Base
from src.Models.User import User
from src.Models.Event import Event


class Attendance:
    def __init__(
            self,
            event_id: int = None,
            user_id: int = None,
            status: int = None,
            reason: str = None,
    ):
        self.event_id = event_id
        self.user_id = user_id
        self.status = status
        self.reason = reason

    @property
    def format_attendance(self) -> str:

        if self.status == -1:
            return "Not Indicated"
        elif self.status == 1:
            return f"Yes {self.reason}"
        else:
            return f"No {self.reason}"


class Attendance(Attendance, Base):
    __tablename__ = "new_attendance"

    event_id: Mapped[int] = mapped_column(ForeignKey(Event.id), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), primary_key=True)
    status: Mapped[int]
    reason: Mapped[str]

    def __repr__(self) -> str:
        return (f"Attendance(event_id={self.event_id!r},\
                user_id={self.user_id!r},\
                status={self.status!r},\
                reason={self.reason!r}")
