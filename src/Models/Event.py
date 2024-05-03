from sqlalchemy import Date, Time
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from src.Database.DatabaseSession.base import Base
from src.Models.AnnouncementEntity import AnnouncementEntity

class Event(Base):
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

    announcement_entities: Mapped[list[AnnouncementEntity]] = relationship(
        back_populates=AnnouncementEntity.event, cascade="all, delete-orphan"
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