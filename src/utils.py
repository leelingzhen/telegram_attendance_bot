import sqlite3

from datetime import datetime
from telegram import (
    InlineKeyboardButton,
)


def escape_html_tags(text: str) -> str:
    html_tags = {
        "&": "&amp",
        '"': "&quote",
        "'": "&#39",
        "<": "&lt",
        ">": "&gt",
    }
    for tag in html_tags:
        text = text.replace(tag, html_tags[tag])
    return text


def date_buttons(data: sqlite3.Row, page_num=0, pages=True) -> list:
    buttons = list()

    if pages:
        for row_object in data[page_num * 5:page_num * 5 + 5]:

            date_ref = datetime.strptime(str(row_object["id"]), "%Y%m%d%H%M")
            text = f"{date_ref.strftime('%-d-%b-%-y, %a')} ({row_object['event_type']})"
            callback_data = str(row_object["id"])
            button = InlineKeyboardButton(
                text=text, callback_data=callback_data)
            buttons.append([button])

        scroll_buttons = list()

        if page_num != 0:
            scroll_buttons.append(InlineKeyboardButton(
                text="Prev", callback_data=str(-1)))
        if len(data) // 5 != page_num:
            scroll_buttons.append(InlineKeyboardButton(
                text="Next", callback_data=str(1)))

        buttons.append(scroll_buttons)

        return buttons

    else:
        for row_object in data:
            date_ref = datetime.strptime(str(row_object["id"]), "%Y%m%d%H%M")
            text = f"{date_ref.strftime('%-d-%b-%-y, %a')} ({row_object['event_type']})"
            callback_data = str(row_object["id"])
            button = InlineKeyboardButton(
                text=text, callback_data=callback_data)
            buttons.append([button])
        return buttons


def resend_announcement(prev_status, announcement, access) -> bool:
    if prev_status == 0 and announcement:
        return True
    if prev_status == -1 and access < 4 and announcement:
        return True
    return False
