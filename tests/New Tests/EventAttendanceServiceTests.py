import unittest
from src.Database.Services.EventAttendanceService import EventAttendanceService
from src.Database.DatabaseSession.DatabaseSessionProviding import Sqlite3SessionProvider
from src.Enum.Enum import Gender
from src.Enum.Enum import AccessCategory


class MyTestCase(unittest.TestCase):
    session_provider = Sqlite3SessionProvider(isTest=True)
    service = EventAttendanceService(session_provider)

    def testGetAttendance(self):
        attendances = self.service.get_attendances(
            event_id=202403231330,
            is_attending=True,
            gender=Gender.male,
            access_category=AccessCategory.all
        )

    def testNotIndicatedAttendance(self):
        attendances = self.service.get_not_indicated_attendances(
            event_id=202403231330,
            access=AccessCategory.member
        )


if __name__ == '__main__':
    unittest.main()
