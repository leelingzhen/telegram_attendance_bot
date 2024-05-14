
from src.Database.Services.EventService import EventService, EventServicing
from src.Models.User import User
from src.Models.Event import Event
from src.Enum.Enum import AccessCategory

from datetime import date
from abc import ABC, abstractmethod


class EventProviding(ABC):

    @abstractmethod
    def events(self, from_date: date, access: AccessCategory) -> list[Event]:
        pass
    
    
class EventProvider(EventProviding):
    
    event_service: EventServicing
    
    def __init__(self, event_service: EventServicing = EventService()):
        """

        @type event_service: EventServicing
        """
        self.event_service = event_service
        
    def events(self, from_date: date, access: AccessCategory) -> list[Event]:
        """

        @rtype: object
        """
        event_id = int(from_date.strftime("%Y%m%d%H%M"))
        events = self.event_service.get_after(event_id, access)
        
        return events
    