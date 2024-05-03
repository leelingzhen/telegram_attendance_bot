
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped

from src.Database.DatabaseSession.base import Base


class User:
    def __init__(self,
                 id: int,
                 name: str,
                 telegram_user: str,
                 gender: str,
                 notification: int,
                 language_pack: str,
                 hidden: int):
        self.id = id
        self.name = name
        self.telegram_user = telegram_user
        self.gender = gender
        self.notification = notification
        self.language_pack = language_pack
        self.hidden = hidden


class User(User, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    telegram_user: Mapped[str]
    gender: Mapped[str]
    notification: Mapped[int]
    language_pack: Mapped[int]
    hidden: Mapped[int]

    def __repr__(self) -> str:
        return (f"User(id={self.id!r},\
                name={self.name!r},\
                telegram_user={self.telegram_user!r},\
                gender={self.gender!r},\
                notification={self.gender!r},\
                language_pack={self.language_pack!r},\
                hidden={self.hidden!r}")
