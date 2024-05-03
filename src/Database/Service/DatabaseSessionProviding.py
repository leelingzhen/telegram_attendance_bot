from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from abc import ABC, abstractmethod
import os


class DatabaseSessionProviding(ABC):

    @abstractmethod
    def session(self) -> Session:
        """

        @rtype: Session
        """
        pass


class Sqlite3SessionProvider(DatabaseSessionProviding):
    _path = os.path.join("resources", "attendance.db")

    def __init__(self, debug=False):
        self.engine = create_engine(f"sqlite:///{self._path}", echo=debug)

    def session(self) -> Session:
        return Session(self.engine)
