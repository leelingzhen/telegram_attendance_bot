from typing import Union

from telegram import InlineKeyboardButton

from src.Buttons import EventOptionButton, ScrollButton
from src.Enum.Enum import Direction
from src.Models.Event import Event


class SelectEventOptionsView:
    """
    buttons should be arranged this way in a list
    [
            [     ], # EventOptionButton
            [     ],
            [     ],
             ....
        [
            [], []
        ] # ScrollButton
    ]
    """

    message_text: str = "Choose Date: "
    buttons:  list[list[InlineKeyboardButton]]

    def __init__(self, events: list[Event], current_page: int, max_page_size: int = 5):

        page_slice = slice(current_page * max_page_size, current_page * max_page_size + max_page_size)

        is_last_page = page_slice.stop >= len(events)

        self.buttons = list()
        for event in events[page_slice]:
            self.buttons.append([EventOptionButton(event)])

        scroll_buttons = list()
        if current_page != 0:
            scroll_buttons.append(ScrollButton(Direction.prev))
        if not is_last_page:
            scroll_buttons.append(ScrollButton(Direction.next))

        self.buttons.append(scroll_buttons)


[
    [],
    [],
    [],
    [], []
]