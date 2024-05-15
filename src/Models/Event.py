from datetime import datetime, time

from sqlalchemy import Date, Time
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from src.Database.DatabaseSession.base import Base

class Event:
    id: int
    event_type: str
    event_date: Date
    start_time: Time
    end_time: Time
    location: str
    announcement: str
    access_control: int
    description: str
    accountable: int

    @property
    def event_date(self) -> datetime:
        return datetime.strptime(str(id), "%Y%m%d%H%M")

    @property
    def format_start(self) -> str:
        return self.start_time.strftime("%-I:%M%p")

    @property
    def format_end(self) -> str:
        return self.end_time.strftime("%-I:%M%p")

class Event(Event, Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str]
    event_date = mapped_column(Date)
    start_time = mapped_column(Time)
    end_time = mapped_column(Time)
    location: Mapped[str]
    announcement: Mapped[str]
    access_control: Mapped[int] = mapped_column(default=2)
    description: Mapped[str]
    accountable: Mapped[int] = mapped_column(default=1)

    announcement_entities: Mapped[list["AnnouncementEntity"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (f"Event(id={self.id!r},\
                event_type={self.event_type!r},\
                event_date={self.event_date!r},\
                start_time={self.start_time!r},\
                end_time={self.end_time!r},\
                location={self.location!r},\
                announcement={self.announcement!r},\
                access_control={self.access_control!r},\
                description={self.description!r},\
                accountable={self.accountable!r}")

class AnnouncementEntity(Base):
    __tablename__ = "new_announcement_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey(Event.id))
    entity_type: Mapped[str]
    offset: Mapped[int]
    entity_length: Mapped[int]

    event: Mapped["Event"] = relationship(back_populates="announcement_entities")

    def __repr__(self) -> str:
        return (f"AnnouncementEntity(id={self.id!r},\
                 event_id={self.event_id!r},\
                 entity_type={self.entity_type  !r},\
                 offset={self.offset!r},\
                 entity_length={self.entity_length!r}")
