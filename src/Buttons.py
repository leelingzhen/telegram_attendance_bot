from datetime import datetime
from telegram import InlineKeyboardButton

from src.Enum.Enum import Direction
from src.Models.Event import Event


class EventOptionButton(InlineKeyboardButton):

    def __init__(self, event: Event, **_kwargs):

        event_datetime = datetime.strptime(str(event.id), "%Y%m%d%H%M")
        text = f"{event_datetime.strftime('%-d-%b-%-y, %a')} ({event.event_type})"
        callback_data = str(event.id)

        super().__init__(text, callback_data=callback_data, **_kwargs)


class ScrollButton(InlineKeyboardButton):

    def __init__(self, direction: Direction, **_kwargs):
        if direction == Direction.next:
            super().__init__(text="Next", callback_data="1", **_kwargs)
        elif direction == Direction.prev:
            super().__init__(text="Prev", callback_data="-1", **_kwargs)



