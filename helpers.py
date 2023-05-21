import sqlite3
import json
import os

from datetime import datetime, date
from telegram import (
    Update,
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatAction,
)

from telegram.bot import Bot, BotCommand
from telegram.error import Unauthorized, BadRequest
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
)

with open("config.json") as f:
    CONFIG = json.load(f)


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


def list_to_string(arr: list) -> str:
    output_str = ""
    for element in arr:
        output_str += element + "\n"
    return output_str


def concat_name_and_user(arr: list):
    output = []
    for element in arr:
        output.append(element[0] + " " + element[1])

    return output


def sql_to_dict(arr: list) -> dict:
    output = {
        'attending_boys': [],
        'attending_girls': [],
        'absent': [],
    }
    guest = {
        'boys': [],
        'girls': []
    }
    for row in arr:
        if row['status'] == 1 and row['gender'] == 'Male':
            if row['control_id'] >= 4:
                reason = f" ({row['reason']})" if row['reason'] != '' else ''
                output['attending_boys'].append(row['name'] + reason)
            elif row['control_id'] >= 2 and row['control_id'] < 4:
                reason = f" ({row['reason']})" if row['reason'] != '' else ''
                if not row['telegram_user']:
                    telegram_user_name = "privated"
                else:
                    telegram_user_name = f"@{row['telegram_user']}"
                text = "(guest) " + row['name'] + ' - ' + telegram_user_name
                guest['boys'].append(text + reason)
        elif row['status'] == 1 and row['gender'] == 'Female':
            if row['control_id'] >= 4:
                reason = f" ({row['reason']})" if row['reason'] != '' else ''
                output['attending_girls'].append(row['name'] + reason)
            elif row['control_id'] >= 2 and row['control_id'] < 4:
                reason = f" ({row['reason']})" if row['reason'] != '' else ''
                if not row['telegram_user']:
                    telegram_user_name = "privated"
                else:
                    telegram_user_name = f"@{row['telegram_user']}"
                text = "(guest) " + row['name'] + ' - ' + telegram_user_name
                guest['girls'].append(text + reason)
        elif row['status'] == 0 and row['control_id'] >= 4:
            text = row['name'] + ' (' + row['reason'] + ')'
            output['absent'].append(text)
    output['attending_boys'] += guest['boys']
    output['attending_girls'] += guest['girls']
    return output


def get_tokens(filename=os.path.join('.secrets', 'bot_credentials.json')) -> dict:
    with open(filename, 'r') as bot_token_file:
        bot_tokens = json.load(bot_token_file)
    return bot_tokens


def mass_send(msg: str, send_list: sqlite3.Row, parse_mode=None, entities=None, pin_message=True, development=True) -> str:
    # getting tokens
    bot_tokens = get_tokens()
    training_bot = Bot(token=bot_tokens['training_bot'])

    # getting checking dev
    if development:
        bot_messenger = Bot(token=bot_tokens['dev_bot'])
    else:
        bot_messenger = Bot(token=bot_tokens['training_bot'])

    for row in send_list:
        try:
            message_object = bot_messenger.send_message(
                chat_id=row['id'],
                text=msg,
                parse_mode=parse_mode,
                entities=entities
            )
        except (Unauthorized, BadRequest):
            yield row['telegram_user']
        else:
            if pin_message:
                bot_messenger.pin_chat_message(
                    chat_id=row['id'],
                    message_id=message_object.message_id,
                    disable_notification=True
                )
            yield ""


def read_msg_from_file(filename, date_str: str) -> str:
    with open(filename, "r", encoding="utf-8") as text_f:
        msg = text_f.read().replace("{date}", date_str).rstrip()
    return msg


def refresh_player_profiles(update: Update, context: CallbackContext):
    user = update.effective_user

    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        player_profile = db.execute(
            "SELECT * FROM players WHERE id = ?", (user.id,)).fetchone()
        saved_username = player_profile["telegram_user"]

    if user.username != saved_username:
        db.execute("BEGIN TRANSACTION")
        db.execute("UPDATE players SET telegram_user = ? WHERE id = ?",
                   (user.username, user.id))
        db.commit()

    return None
