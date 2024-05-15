from typing import Union

from src.Buttons import EventOptionButton, ScrollButton
from src.Enum.Enum import Direction
from src.Models.Event import Event


class SelectEventOptionsView:

    message_text: str = "Choose Date: "
    buttons:  list[Union[list[EventOptionButton], list[ScrollButton]]]

    def __init__(self, events: list[Event], current_page: int, max_page_size: int = 5 ):

        page_slice = slice(current_page * max_page_size, current_page * max_page_size + max_page_size)
        is_last_page = page_slice.stop >= len(events)

        event_buttons = list()
        for event in events:
            event_buttons.append([EventOptionButton(event)])

        scroll_buttons = list()
        if current_page != 0:
            scroll_buttons.append(ScrollButton(Direction.prev))
        if not is_last_page:
            scroll_buttons.append(ScrollButton(Direction.next))

        self.buttons = [event_buttons, scroll_buttons]


