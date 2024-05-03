from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped

from src.Database.DatabaseSession.base import Base


class AccessDescription:
    def __init__(self, id: int, description: str):
        self.id = id
        self.description = description


class AccessDescription(AccessDescription, Base):
    __tablename__ = "access_control_description"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str]

    def __repr__(self) -> str:
        return (f"AccessDescription(id={self.id!r},\
                description={self.description!r}")
