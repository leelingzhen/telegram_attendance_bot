from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy import ForeignKey

from src.Database.DatabaseSession.base import Base
from src.Models.User import User
from src.Models.AccessDescription import AccessDescription


class Access:

    def __init__(self, user_id: int, control_id: int):
        self.user_id = user_id
        self.control_id = control_id


class Access(Access, Base):
    __tablename__ = "access_control"

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), primary_key=True)
    control_id: Mapped[int] = mapped_column(ForeignKey(AccessDescription.id))

    def __repr__(self) -> str:
        return (f"Access(user_id={self.user_id!r},\
                control_id={self.control_id!r}")
