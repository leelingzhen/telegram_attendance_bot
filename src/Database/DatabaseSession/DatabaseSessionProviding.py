from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from abc import ABC, abstractmethod
import os


class DatabaseSessionProviding(ABC):

    @abstractmethod
    def make_session(self) -> Session:
        """

        @rtype: Session
        """
        pass


class Sqlite3SessionProvider(DatabaseSessionProviding):
    _path = os.path.join("resources", "attendance.db")
    _test_db_path = os.path.join("resources", "test_attendance.db")

    def __init__(self, debug: bool = False, isTest: bool = False) -> object:
        if isTest:
            self.engine = create_engine(f"sqlite:///{self._test_db_path}", echo=debug)
        else:
            self.engine = create_engine(f"sqlite:///{self._path}", echo=debug)
        self.session_maker = sessionmaker(bind=self.engine, expire_on_commit=False)

    def make_session(self) -> Session:
        session = self.session_maker()
        return session


