import unittest
from src.Models.Event import Event
from src.Database.DatabaseSession.DatabaseSessionProviding import Sqlite3SessionProvider
from src.Database.Services.EventService import EventDatabaseService

from datetime import date
from datetime import time


class MyTestCase(unittest.TestCase):
    session_provider = Sqlite3SessionProvider(isTest=True)
    service = EventDatabaseService(session_provider)

    def testCRUD(self):
        event = Event(
            id=205006031200,
            event_type="test_type",
            event_date= date(2050, 6, 3),
            start_time=time(12, 6),
            end_time=time(15, 0),
            location="test_location",
            announcement="test_announcement",
            access_control=2,
            description="description",
            accountable=1
        )
        self.service.insert(event)

        event_under_test = self.service.get(event_id=205006031200)
        self.assertEqual(event.id, event_under_test.id)

        event_under_test.event_type = "prank"
        self.service.update(event_under_test)
        event_under_test = self.service.get(event_id=205006031200)
        self.assertEqual("prank", event_under_test.event_type)

        self.service.delete(event_under_test)
        event_under_test_exists = self.service.exists(event_id=205006031200)
        self.assertFalse(event_under_test_exists)

    def testGetAfter(self):
        events = [
            Event(
                id=300006031200,
                event_type="test_type",
                event_date=date(3000, 6, 3),
                start_time=time(12, 6),
                end_time=time(15, 0),
                location="test_location",
                announcement="test_announcement",
                access_control=2,
                description="description",
                accountable=1
            ),
            Event(
                id=300006041200,
                event_type="test_type",
                event_date=date(2050, 6, 4),
                start_time=time(12, 6),
                end_time=time(15, 0),
                location="test_location",
                announcement="test_announcement",
                access_control=2,
                description="description",
                accountable=1
            ),
            Event(
                id=300106051200,
                event_type="test_type",
                event_date=date(2050, 6, 5),
                start_time=time(12, 6),
                end_time=time(15, 0),
                location="test_location",
                announcement="test_announcement",
                access_control=4,
                description="description",
                accountable=1
            ),
            Event(
                id=300106061200,
                event_type="test_type",
                event_date=date(2050, 6, 6),
                start_time=time(12, 6),
                end_time=time(15, 0),
                location="test_location",
                announcement="test_announcement",
                access_control=4,
                description="description",
                accountable=1
            ),
        ]

        for event in events:
            self.service.insert(event)

        all_events = self.service.get_after(300006031200)
        restricted_events = self.service.get_after(event_id=300006031200, access=4)
        after_first_event = self.service.get_after(300006041200)

        for event in events:
            self.service.delete(event)

        self.assertEqual(len(events), len(all_events))
        self.assertEqual(2, len(restricted_events))
        self.assertEqual(3, len(after_first_event))


if __name__ == '__main__':
    unittest.main()
