import datetime
from typing import Union

from telegram import InlineKeyboardButton

from src.Buttons import EventOptionButton, ScrollButton, ToggleReasonButton
from src.Enum.Enum import Direction
from src.Models.Event import Event
from src.Models.Attendance import Attendance
from src.Models.User import User
from src.Models.Access import Access

from abc import ABC, abstractmethod


class ViewInteracting(ABC):
    @property
    @abstractmethod
    def buttons(self):
        pass

    @property
    @abstractmethod
    def message_text(self) -> str:
        pass


class Viewing(ABC):

    @property
    @abstractmethod
    def message_text(self) -> str:
        pass


class SelectEventOptionsView(ViewInteracting):
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

    def buttons(self) -> list[list[InlineKeyboardButton]]:
        return self.buttons


class AttendanceStatusView(ViewInteracting):

    message_text: str
    buttons: list[list[InlineKeyboardButton]]

    def __init__(
            self,
            event: Event,
            attendance: Attendance,
            attach_reason: bool,
            team_name: str,
    ):

        must_attach_reason = int(bool(event.accountable) or attach_reason)
        attach_reason = int(attach_reason)

        self.buttons = [
            [ToggleReasonButton(not attach_reason)],
            [InlineKeyboardButton(f"Yes I ❤️{team_name} ", callback_data=f"1,{attach_reason}")],
            [InlineKeyboardButton("No (lame)", callback_data=f"0,{must_attach_reason}")],
        ]

        self.message_text = f"""
Your attendance is indicated as \'{attendance.format_attendance}\'

<u>Details</u>
Date: {event.event_date.strftime('%-d %b, %a')}
Event: {event.event_type}
Time: {event.format_start} - {event.format_end}
Location : {event.location}
Accountable event: {'Yes' if event.accountable else 'No'}

<u>Description</u>
{event.description}
{chr(10) + '<i>You will write your reason/comment in the next step</i>' + chr(10) if attach_reason else ''}
Would you like to go for {event.event_type}?
            """

    def message_text(self) -> str:
        return self.message_text

    def buttons(self):
        return self.buttons

class AcknowledgeAttendanceView(Viewing):
    message_text: str

    def __init__(self, event: Event, attendance: Attendance):
        encouragement = f"See you at {event.event_type}! 🦾🦾" if attendance.status else "Hope to see you soon🥲🥲"
        attach_reason = f"Comments: {attendance.reason}" if attendance.reason else ""

        self.message_text = f"""
You have successfully updated your attendance! 🤖🤖\n
<u>Details</u>
Date: {event.event_date.strftime('%-d %b, %a')}
Event: {event.event_type}
Time: {event.format_start} - {event.format_end}
Location : {event.location}
Attendance: {'Yes' if attendance.status else 'No'}

<u>Description</u>
{event.description}

{attach_reason}

{encouragement}
"""

    def message_text(self) -> str:
        return self.message_text

class KaypohMessageView(Viewing):
    message_text: str

    def __init__(self, event: Event,
                 attending_male_users: list[tuple[User, Access, Attendance]],
                 attending_female_users: list[tuple[User, Access, Attendance]],
                absent_users: list[tuple[User, Access, Attendance]],
                unindicated_users: list[tuple[User, Access]],
                 ):
        # TODO: reformat the message to something that looks better

        ## TODO when updating the message, update date time rendered
        date_time_rendered = datetime.datetime.now().strftime("%-d-%b %-I:%M%p")

        total_attendees = len(attending_male_users) + len(attending_female_users)

        self.message_text = f"""Attendance
        for <b> {event.event_type} </b> on <u> {event.event_date.strftime('%-d-%b-%y, %a @ %-I:%M%p')} </u>: {total_attendees}

        Attending 👦🏻: {len(attending_male_users)}
        { chr(10).join(str(item[0].name) for item in attending_male_users)}

        Attending 👩🏻: {len(attending_female_users)}
        { chr(10).join(str(item[0].name) for item in attending_female_users) }

        Absent: {len(absent_users)}
        { chr(10).join(str(item[0].name) for item in absent_users) }

        Uninidicated: {len(unindicated_users)}
        { chr(10).join(str(item[0].name) for item in unindicated_users) }

        <i> last updated {date_time_rendered} </i>"""

    def message_text(self) -> str:
        return self.message_text
