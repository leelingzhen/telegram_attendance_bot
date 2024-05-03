from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

from src.Database.DatabaseSession.base import Base
from src.Models.Event import Event

class AnnouncementEntity(Base):
    __tablename__ = "new_announcement_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey(Event.id))
    entity_type: Mapped[str]
    offset: Mapped[int]
    entity_length: Mapped[int]

    event: Mapped[Event] = relationship(back_populates=Event.announcement_entities)

    def __repr__(self) -> str:
        return (f"AnnouncementEntity(id={self.id!r},\
                 event_id={self.event_id!r},\
                 entity_type={self.entity_type  !r},\
                 offset={self.offset!r},\
                 entity_length={self.entity_length!r}")