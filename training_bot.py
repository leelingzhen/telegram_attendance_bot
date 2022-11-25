import logging
import os
import helpers
import json
import sqlite3

from datetime import date, datetime
from functools import wraps
from ics import Calendar, Event

from telegram import (
        Update,
        ForceReply,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        ChatAction,
        MessageEntity,
        )
from telegram.bot import Bot, BotCommand
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
    db = sqlite3.connect(CONFIG['database'], check_same_thread=False)

#enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

#typing wrapper
def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func

def secure(access=2):
    def decorator(func):
    #admin restrictions
        @wraps(func)
        def wrapped(update, context, *args, **kwargs):
            user = update.effective_user
            with sqlite3.connect(CONFIG["database"]) as db:
                db.row_factory = lambda cursor, row:row[0]
                user_clearance = db.execute("SELECT control_id FROM access_control WHERE player_id = ?", (user.id,)).fetchone()
            if user_clearance < access:
                print("WARNING: Unauthorized access denied for @{}.".format(user.username))
                update.message.reply_text(
                        text='you do not have access to this function, please contact adminstrators'
                        )
                return  # quit function
            return func(update, context, *args, **kwargs)
        return wrapped
    return decorator

@send_typing_action
def start(update: Update, context: CallbackContext)-> None:
    user = update.effective_user
    
    if update.message is not None:
        chat_id = update.message.chat.id
        telegram_user = update.message.chat.username
        first_name = update.message.chat.first_name
    with sqlite3.connect(CONFIG["database"]) as db:
        player_profile = db.execute("SELECT id, name, telegram_user, language_pack FROM players WHERE id = ?", (chat_id,)).fetchone()

        if player_profile is None:
            db.execute("BEGIN TRANSACTION")
            db_insert = [chat_id, telegram_user]
            db.execute("INSERT INTO players(id, telegram_user) VALUES (?, ?)", db_insert)

            #insert into access control
            db_insert = [chat_id, 0]
            db.execute("INSERT INTO access_control (player_id, control_id ) VALUES (?,?)", db_insert)
            db.commit()
            update.message.reply_text("Hello new player! please register yourself by using /register")

            return None

        player_access = db.execute("SELECT control_id FROM access_control WHERE player_id = ?", (chat_id,)).fetchone()[0]
        if player_access == 0:
            update.message.reply_text("Hello new player! please register yourself by using /register")
            return None

        elif player_access > 0:
            language_pack = player_profile[3]
            update.message.reply_text("Hello please use the commands to talk to me!")
        logger.info('user %s has talked to the bot', user.first_name)
    return None

@secure(access=2)
@send_typing_action
def choosing_date_low_access(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    logger.info("user %s is choosing date...", user.first_name)
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        player_access = db.execute("SELECT control_id FROM access_control WHERE player_id = ?", (user.id,)).fetchone()[0]
        event_id = date.today().strftime('%Y%m%d%H%M')
        event_data = db.execute("SELECT id, event_type FROM events WHERE id > ? AND access_control <= ? ORDER BY id", (event_id, player_access)).fetchall()

    context.user_data["event_data"] = event_data
    context.user_data["page"] = 0

    reply_markup = InlineKeyboardMarkup(helpers.date_buttons(event_data, 0))
    # if there are no queried trainings
    if event_data == list():
        update.message.reply_text("There are no more further planned events. Enjoy your break!🏝🏝")
        return ConversationHandler.END 

    update.message.reply_text( 
            text="Choose Date:",
            reply_markup=reply_markup
            )
    return 1

@secure(access=4)
@send_typing_action
def choosing_date_high_access(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    logger.info("user %s is choosing date...", user.first_name)
    with sqlite3.connect(CONFIG['database']) as db:
        player_access = db.execute("SELECT control_id FROM access_control WHERE player_id = ?", (user.id,)).fetchone()[0]
        db.row_factory = sqlite3.Row
        event_id = date.today().strftime('%Y%m%d%H%M')
        event_data = db.execute("SELECT id, event_type FROM events WHERE id > ? AND access_control <= ? ORDER BY id", (event_id, player_access)).fetchall()

    context.user_data["event_data"] = event_data
    context.user_data["page"] = 0

    reply_markup = InlineKeyboardMarkup(helpers.date_buttons(event_data, 0))
    # if there are no queried trainings
    if event_data == list():
        update.message.reply_text("There are no more further planned events. Enjoy your break!🏝🏝")
        return ConversationHandler.END 

    update.message.reply_text( 
            text="Choose Date:",
            reply_markup=reply_markup
            )
    return 1


def page_change(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    scroll_val = int(query.data)

    context.user_data["page"] += scroll_val
    reply_markup = InlineKeyboardMarkup(helpers.date_buttons(context.user_data["event_data"], page_num=context.user_data["page"]))
    query.edit_message_reply_markup(
            reply_markup=reply_markup
            )
    return 1

def attendance_list(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    logger.info('user %s is a kaypoh', user.first_name)
    query = update.callback_query
    query.answer()
    user = update.effective_user
    query.edit_message_text(
            text="Kaypohing..."
            )

    #retrieve selected event
    event_id = int(query.data)
    event_date = datetime.strptime(str(event_id), '%Y%m%d%H%M')
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row

        with open(os.path.join('resources','saved_sql_queries', 'available_attendance.sql')) as f:
            sql_query = f.read()
            player_data = db.execute(sql_query,(event_id, )).fetchall()
            player_data = helpers.sql_to_dict(player_data)

        with open(os.path.join('resources', 'saved_sql_queries', 'unindicated_players.sql')) as f:
            sql_query = f.read()
            unindicated_data = db.execute(sql_query, (event_id,)).fetchall()

        event = db.execute("SELECT * FROM events WHERE id = ?", (event_id, )).fetchone()

    attending_boys = ""
    for player in player_data['attending_boys']:
        attending_boys += player + "\n"
    attending_girls = ''
    for player in player_data['attending_girls']:
        attending_girls += player + "\n"
    absent = ''
    for player in player_data['absent']:
        absent += player + "\n"
    unindicated = ''
    for row in unindicated_data:
        unindicated += row['name'] + '\n'



    newline = '\n'
    text = f"""
Attendance for <b>{event['event_type']}</b> on <u>{event_date.strftime('%-d-%b-%y, %a @ %-I:%M%p')}</u> : {len(player_data['attending_boys']) + len(player_data['attending_girls'])}

Attending 👦🏻: {len(player_data['attending_boys'])}
{attending_boys}
Attending 👩🏻: {len(player_data['attending_girls'])}
{attending_girls}
Absent: {len(player_data['absent'])}
{absent}

Uninidicated: {len(unindicated_data)}
{unindicated}

    """
    query.edit_message_text(text=text, parse_mode='html')

    return ConversationHandler.END

def indicate_attendance(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_id = update.effective_user.id
    

    #retrieve date query and store
    selected_event = int(query.data)
    context.user_data["event_id"] = selected_event

    #retrieve data 
    with sqlite3.connect(CONFIG["database"]) as db:
        db.row_factory = sqlite3.Row
        attendance = db.execute("SELECT status, reason FROM attendance WHERE event_id = ? and player_id = ?", (selected_event, user_id)).fetchone()
        event_data = db.execute("SELECT * FROM events WHERE id = ?", (selected_event, )).fetchone()
        event_date = datetime.strptime(str(selected_event), "%Y%m%d%H%M")
        training_date = event_date.strftime("%-d %b, %a")
        start_time= event_date.strftime("%-I:%M%p")
        end_time = datetime.strptime(event_data["end_time"], "%H:%M").strftime("%-I:%M%p")



    if attendance is None:

        context.user_data["prev_status"] = "Not Indicated"
        prev_status = "Not Indicated"
        prev_reason = ""
    else:
        context.user_data["prev_status"] = attendance["status"]
        prev_status = "Yes" if attendance["status"] == 1 else "No"
        prev_reason = attendance["reason"]

    #store attendance into context
    context.user_data['event_data'] = event_data
    context.user_data["status"] = ""
    context.user_data["reason"] = ""

    button = [
            [InlineKeyboardButton("Yes I ❤️ Alliance", callback_data="Yas")],
            [InlineKeyboardButton("Yes but...", callback_data="Yes")],
            [InlineKeyboardButton("No (lame)", callback_data="No")],
            ]
    reply_markup = InlineKeyboardMarkup(button)

    query.edit_message_text(
            text=f"""
Your attendance is indicated as \'{prev_status}{'' if prev_reason =='' else f' ({prev_reason})'}\'

<u>Details</u>
Date: {event_date.strftime('%-d %b, %a')}
Event: {event_data['event_type']}
Time: {start_time} - {end_time}
Location : {event_data['location']}

Would you like to go for {event_data['event_type']}?
            """
            ,
            reply_markup=reply_markup,
            parse_mode='html'
            )
    return 2

def give_reason(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    context.user_data["status"] = query.data

    query.edit_message_text(
            text="Please write a comment/reason 😏"
            )
    return 2

def update_attendance(update: Update, context: CallbackContext) -> str:

    #retrieve indication of attendance
    status = context.user_data["status"]

    text = "updating your attendance..."
    
    if status == "":
        #indicated attendance is yas skipped give_reason
        query = update.callback_query
        query.answer()
        status = "Yes"
        reason = ""
        bot_message = query.edit_message_text(
                text=text
                )
    else :
        #retrieve reasons, went through give_reason
        reason = update.message.text
        bot_message = update.message.reply_text(
                text=text
                )
    #get stored data
    user = update.effective_user
    event_id = context.user_data["event_id"]
    event_data = context.user_data['event_data']

    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        start_datetime = datetime.strptime(str(event_id), "%Y%m%d%H%M")
        
        training_date = start_datetime.strftime("%-d %b, %a")
        training_time = start_datetime.strftime("%-I:%M%p")
        end_time = datetime.strptime(event_data["end_time"], "%H:%M").strftime("%-I:%M%p")

        if status == "Yes":
            bot_comment = "See you at training! 🦾🦾"
        elif status == "No":
            bot_comment = "Hope to see you soon🥲🥲"

        db.execute("BEGIN TRANSACTION")
        if context.user_data["prev_status"] == "Not Indicated":
            data = (event_id, user.id, 1 if status == "Yes" else 0, reason)
            db.execute("INSERT INTO attendance (event_id, player_id, status, reason) VALUES (?, ?, ?, ?)", data)
        else:
            data = (1 if status == "Yes" else 0, reason, event_id, user.id)
            db.execute("UPDATE attendance SET status = ?, reason = ? WHERE event_id = ? AND player_id = ?", data)
        db.commit()

        text = f"""
You have sucessfully updated your attendance! 🤖🤖\n
<u>Details</u>
Date: {training_date}
Event: {event_data['event_type']}
Time: {training_time} - {end_time}
Location : {event_data['location']}
Attendance: {status}\n\n""" 

        if reason != "":
            text += f"Comments: {reason}\n\n" 

        bot_message.edit_text(
                text=text + bot_comment,
                parse_mode='html'
                )

        announcement = db.execute('SELECT announcement FROM events WHERE id = ?', (event_id, )).fetchone()['announcement']
        access_control = db.execute('SELECT control_id FROM access_control WHERE player_id = ?', (user.id, )).fetchone()['control_id']

        if context.user_data["prev_status"] == 0 and announcement is not None:

            entity_data = db.execute('SELECT * FROM announcement_entities WHERE event_id = ?', (event_id, )).fetchall()
            announcement_entities = []
            for entity in entity_data:
                announcement_entities.append(
                        MessageEntity(
                            type=entity['entity_type'],
                            offset=entity['offset'],
                            length=entity['entity_length']
                            )
                        )
            context.bot.send_message(
                    chat_id=user.id,
                    text=announcement,
                    entities=announcement_entities,
                    )

        elif context.user_data['prev_status'] == 'Not Indicated' and access_control < 4 and announcement is not None:
            entity_data = db.execute('SELECT * FROM announcement_entities WHERE event_id = ?', (event_id, )).fetchall()
            announcement_entities = []
            for entity in entity_data:
                announcement_entities.append(
                        MessageEntity(
                            type=entity['entity_type'],
                            offset=entity['offset'],
                            length=entity['entity_length']
                            )
                        )
            context.bot.send_message(
                    chat_id=user.id,
                    text=announcement,
                    entities=announcement_entities,
                    )

    
    logger.info("User %s has filled up his/her attendance...", update.effective_user.first_name)
    return ConversationHandler.END

@secure(access=4)
@send_typing_action
def choosing_more_dates(update:Update, context: CallbackContext)-> int:
    user = update.effective_user

    logger.info("user %s used /attendance_plus...", user.first_name)
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        event_data = db.execute("SELECT id, event_type FROM events WHERE id > ?", (date.today().strftime('%Y%m%d%H%M'),)).fetchall()

    context.user_data["event_data"] = event_data
    context.user_data["chosen_events"] = list()
    # if there are no queried trainings
    if event_data == list():
        update.message.reply_text("There are no more further planned events. Enjoy your break!🏝🏝")
        return ConversationHandler.END 
    
    buttons = helpers.date_buttons(event_data, pages=False)
    reply_markup = InlineKeyboardMarkup(buttons)


    update.message.reply_text( 
            text= """
Select dates for events you want to update. Select them again to remove them from selection.

Selected Dates:

            """,
            reply_markup=reply_markup
            )
    return 1

def choosing_more_dates_cont(update:Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    #get query 
    event_id = int(query.data)

    #retrieve choosent events
    chosen_events = context.user_data["chosen_events"]
    event_data = context.user_data["event_data"]

    if event_id in chosen_events:
        chosen_events.remove(event_id)
    else:
        chosen_events.append(event_id)

    chosen_events.sort()
    context.user_data["chosen_events"] = chosen_events

    text = ''
    for element in chosen_events:
        text += datetime.strptime(str(element), '%Y%m%d%H%M').strftime('%-d-%b-%-y, %a @ %-I:%M%p') + "\n"


    #make buttons
    buttons = helpers.date_buttons(event_data, pages=False)
    buttons.append([InlineKeyboardButton(text='Confirm', callback_data='forward')])
    reply_markup = InlineKeyboardMarkup(buttons)

    query.edit_message_text(
            text =f"""
Select dates for events you want to update. Select them again to remove them from selection.

Selected Dates:
{text}

            """,
            reply_markup=reply_markup
            )

    return 1

def indicate_more(update: Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    #initialise status
    context.user_data["status"] = -1

    buttons = [
            [InlineKeyboardButton(text="Yes", callback_data="1")],
            [InlineKeyboardButton(text="No", callback_data="0")]
            ]
    reply_markup = InlineKeyboardMarkup(buttons)

    query.edit_message_text(
            text="What would you like to indicate for these events?",
            reply_markup=reply_markup
            )

    return 2

def give_reason_more(update: Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    #save the query
    context.user_data["status"] = int(query.data)

    query.edit_message_text(
            text="Please write a comment/reason 😏. The comment will be applied to all selected events."
            )
    return 2

def commit_attendance_plus(update: Update, context:CallbackContext) -> int:
    #retrieve indication of attendance
    user = update.effective_user
    status = context.user_data["status"]

    text = "updating your attendance..."
    
    if status == -1:
        #indicated attendance is yes skipped give_reason_more
        query = update.callback_query
        query.answer()
        status = 1
        reason = ""
        bot_message = query.edit_message_text(
                text=text
                )
    else :
        #retrieve reasons, went through give_reason
        reason = update.message.text
        bot_message = update.message.reply_text(
                text=text
                )
    #retrieve selected events
    chosen_events = context.user_data['chosen_events']

    #retrieve from database
    with sqlite3.connect(CONFIG['database']) as db:
        #retrieve existing data that has already been indicated 
        data = (user.id, date.today().strftime("%Y%m%d%H%M"))
        existing_events = db.execute("SELECT event_id FROM attendance WHERE player_id = ? AND event_id >= ?", data).fetchall()
        existing_events = list(sum(existing_events, ()))
        intersect_events = set(chosen_events).intersection(existing_events)

        #add to database
        db.execute("BEGIN TRANSACTION")

        #first update existing records
        if len(intersect_events) != 0: 
            data = [(status, reason, event_id, user.id) for event_id in intersect_events]
            db.executemany("UPDATE attendance SET status = ?, reason =? WHERE event_id = ? AND player_id = ?", data)

        #get events which are not in record yet
        remaining_chosen_events = set(chosen_events) - intersect_events
        if len(remaining_chosen_events) != 0:
            data = [(event_id, user.id, status, reason) for event_id in remaining_chosen_events]
            db.executemany("INSERT INTO attendance VALUES (?, ?, ?, ?)", data)
        db.commit()

    chosen_events_str = ""
    for event_id in chosen_events: 
        chosen_events_str += "    " + datetime.strptime(str(event_id), '%Y%m%d%H%M').strftime('%-d-%b-%-y, %a @ %-I:%M%p') + "\n"

    text = f"""
You have sucessfully updated your attendance for {len(chosen_events)} records!

{chosen_events_str}
    Attendance : {"Yes" if status == 1 else "No"}
    
    {'Comment/reason: ' + reason if reason != '' else ''}

    """

    bot_message.edit_text(text=text)
    logger.info("user %s has sucessfully updated attendance for %d records", user.first_name, len(chosen_events))


    return ConversationHandler.END


    

@secure(access=2)
@send_typing_action
def events(update: Update, context: CallbackContext)-> None:
    user = update.effective_user
    logger.info("User %s has started a query for his/her event schedule", user.first_name)
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row

        ## check if there are any existing events
        existing_events = db.execute("SELECT id FROM events WHERE id > ?", (date.today().strftime("%Y%m%d%H%M"), )).fetchall()
        if existing_events == list():
            update.message.reply_text("There are no future trainings planned Enjoy your break.😴😴")
            logger.info("user %s has sucessfully queried for events and there are no further events planned", user.first_name)
            return None
        player_access = db.execute("SELECT control_id FROM access_control WHERE player_id = ?", (user.id,)).fetchone()['control_id']

        registered_events = db.execute("""
        SELECT id, event_type FROM events
        JOIN attendance ON events.id = attendance.event_id
        WHERE attendance.player_id = ? 
        AND attendance.event_id >= ? 
        AND attendance.status = ?
        AND events.access_control <= ?
        ORDER BY id
                """, 
                (user.id, date.today().strftime("%Y%m%d%H%M"), 1, player_access)
                ).fetchall()

        #sorting by categories
        dict_date = {
                "Field Training" : list(),
                "Scrim" : list(),
                "Hardcourt/Track": list(),
                "Gym/Pod": list(),
                "Cohesion": list()
                }

        for row_obj in registered_events:
            event_date = datetime.strptime(str(row_obj["id"]), '%Y%m%d%H%M')
            event_type = row_obj["event_type"]
            dict_date[event_type].append(f"{event_date.strftime('%d %b, %a @ %-I:%M%p')}")

        text = ""
        for key in dict_date:
            # no registered dates of this category
            if dict_date[key] == list():
                continue
            else:
                text += f"<u>{key}</u>\n"
                for element in dict_date[key]:
                    text += element + "\n"
                text += '\n'

        
    update.message.reply_text(f"You'll 👀 Alliance on:\n\n{text}\nSee you then!🦿🦿", parse_mode='html')
    logger.info("user %s has sucessfully queried for events.", user.first_name)

    return None

@send_typing_action
def generate_ics(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    event_id = int(query.data)

    user = update.effective_user
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        event_data = db.execute("SELECT * FROM events WHERE id = ? ", (event_id, )).fetchone()
        event_date = datetime.strptime(str(event_id), "%Y%m%d%H%M")

        #text formatting
        training_date = event_date.strftime("%-d %b, %a")
        start_time= event_date.strftime("%-I:%M%p")
        end_time = datetime.strptime(event_data["end_time"], "%H:%M").strftime("%-I:%M%p")

        #calendar formatting
        calendar_start= event_date.strftime("%Y-%m-%d %H:M%S")
        calendar_end = event_date.strftime("%Y-%m-%d") + event_data["end_time"] + ":00"
        calendar = Calendar()
        calendar_event = Event(
                name=f"Alliance {event_data['event_type']}",
                begin=event_date.strftime("%Y-%m-%d %H:%M:%S"),
                end=event_date.strftime("%Y-%m-%d") + " " + event_data["end_time"] + ":00",
                location = event_data['location']
                )
        calendar.events.add(calendar_event)
    text = f"""
<u>Details</u>
Date: {event_date.strftime('%-d %b, %a')}
Event: {event_data['event_type']}
Time: {start_time} - {end_time}
Location : {event_data['location']}
"""
    query.edit_message_text(
            text=f"Save the event to your calendar with the generated ics file!\n{text}",
            parse_mode='html'
            )


    with open(f"{event_date.strftime('%-d %b, %a')}.ics", 'w') as f:
        f.writelines(calendar.serialize_iter())
    with open(f"{event_date.strftime('%-d %b, %a')}.ics", 'rb') as f:
        context.bot.send_document(user.id, f)
    os.remove(f"{event_date.strftime('%-d %b, %a')}.ics")

    logger.info("user %s has generated an ics file for %s", user.first_name, event_date.strftime("%d-%m-%y"))

    return ConversationHandler.END


   

@secure(access=4)
@send_typing_action
def settings_start(update: Update, context: CallbackContext)-> int:
    user = update.effective_user
    logger.info("User %s is accessing settings...", user.first_name)
    
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        result = db.execute("SELECT * FROM players WHERE id = ?", (user.id, )).fetchone()
        name = result["name"]
        notification = result["notification"]
        language = result["language_pack"]
        saved_username = result["telegram_user"]

    if user.username != saved_username:
        db.execute("BEGIN TRANSACTION")
        db.execute("UPDATE players SET username = ? WHERE id = ?", (user.username, user_id))
        db.commit()

    #save into context
    context.user_data["user_id"] = user.id
    context.user_data["name"] = name
    context.user_data["notification"] = notification
    context.user_data["language"] = language

    buttons = [
            [InlineKeyboardButton(text="Name", callback_data="name")],
            [InlineKeyboardButton(text="Notification settings", callback_data="notification")],
            [InlineKeyboardButton(text="Language settings", callback_data="language")]
            ]
    reply_markup = InlineKeyboardMarkup(buttons)

    update.message.reply_text(
            text=f"Current settings\nName: {name}\nNotifications: {'Yes' if notification == 1 else 'No'}\nLanguage pack: {language}\n",
            reply_markup=reply_markup
            )
    return 1

def name_change(update:Update, context:CallbackContext) -> float:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text=(
                f"""
Your name is currently set as <u>{context.user_data['name']}</u>
<b>Please use your full name</b>
text me your name if you wish to change it\n\n
otherwise /cancel to cancel the process
                """
                ),
            parse_mode="html"
            )
    return 1.1

def notification_change(update:Update, context:CallbackContext)-> float:
    query = update.callback_query
    query.answer()
    buttons = [
            [InlineKeyboardButton(text="Yes", callback_data=str(1))],
            [InlineKeyboardButton(text="No", callback_data=str(0))]
            ]
    query.edit_message_text(
            text=(
                f"""
From using this telegram bot, you will receive club announcements
reminders. By choosing yes, you are essentially indicating that
you are an <u>active player</u>

<b>Yes</b> - Receive all club announcements and event reminders
<b>No</b> - Receive only event specific announcements if you indicated 'Yes' for the said event

current selection - {'Yes'if context.user_data['notification'] == 1 else 'No'}

Choose notification setting
                """),
                parse_mode = 'html',
                reply_markup=InlineKeyboardMarkup(buttons)
                
            )
    return 1.2

def language_change(update:Update, context:CallbackContext)-> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text=f"This feature is still under development, please come back another time!"
            )
    logger.info("User %s tried to change language", context.user_data["name"])
    return ConversationHandler.END

def commit_notification_change(update:Update, context:CallbackContext)-> int:
    query = update.callback_query
    query.answer()
    
    notification_setting = int(query.data)
    with sqlite3.connect(CONFIG["database"]) as db:
        db.execute("BEGIN TRANSACTION")
        db.execute("UPDATE players SET notification = ? WHERE id = ?", (notification_setting, context.user_data["user_id"]))
        db.commit()

    query.edit_message_text(
            text=
            f""" 
You have sucessfully turned {'off' if notification_setting == 0 else 'on'} notifications

<i>You are now an {'inactive player' if notification_setting == 0 else 'active player'}</i>
            """,
            parse_mode = 'html'
            )
    logger.info("User %s has sucessfully changed notification settings and is now an %s player.", context.user_data["name"], "active" if notification_setting == 1 else "inactive")
    return ConversationHandler.END


@send_typing_action
def confirmation_name_change(update:Update, context:CallbackContext) -> float:
    buttons = [
        [InlineKeyboardButton(text="Confirm", callback_data="forward")],
        [InlineKeyboardButton(text="Edit Name", callback_data="back")]
        ]
    user = update.effective_user
    new_name = update.message.text.rstrip().lstrip()
    with sqlite3.connect(CONFIG['database']) as db:
        data = (new_name, user.id)
        similar_names = db.execute("SELECT telegram_user FROM players WHERE name = ? AND id != ?", data).fetchone()

    if similar_names is not None:
        bot_message = update.message.reply_text(
                text=f"{new_name} has already been taken by @{similar_names[0]}.\n please enter a new name!"
                )
        return 1.1


    
    context.user_data["new_name"] = new_name

    bot_message = update.message.reply_text(
            f"Your name will be:\n"
            f"<u>{new_name}</u>\n\n"
            "confirm?",
            parse_mode="html",
            reply_markup = InlineKeyboardMarkup(buttons)
            )
    return 2.1

def commit_name_change(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()

    new_name = context.user_data["new_name"]
    with sqlite3.connect(CONFIG["database"]) as db:
        db.execute("BEGIN TRANSACTION")
        db.execute("UPDATE players SET name = ? WHERE id = ?", (new_name, context.user_data["user_id"]))
        db.commit()
    
    query.edit_message_text(
            text=f"Name sucessfully changed to <u>{new_name}</u>",
            parse_mode = "html"
            )
    name = context.user_data["name"]
    
    logging.info("User %s has changed name from %s to %s", user.username, name, new_name)

    return ConversationHandler.END

@send_typing_action
def select_gender(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    with sqlite3.connect(CONFIG['database']) as db:
        player_access = db.execute("SELECT control_id FROM access_control WHERE player_id = ?", (user.id, )).fetchone()[0]
    
    if player_access >=2:
        update.message.reply_text("You are already registered.")
        return ConversationHandler.END
    if player_access ==1:
        update.message.reply_text("Your registration is pending approval.")
        return ConversationHandler.END
    
    logger.info("user %s is registering", user.first_name)
    with open(os.path.join('resources', 'messages', 'registration_introduction.txt')) as f:
        text = f.read()
    buttons=[
            [InlineKeyboardButton(text='Male 👦🏻', callback_data='Male')],
            [InlineKeyboardButton(text='Female 👩🏻', callback_data='Female')]
            ]
    update.message.reply_text(
            text = """
We will be collecting your <u>full name</u> and <u>gender</u> for the registration process.
After that a core member from Alliance will approve your registration and you will be able to join us for trainings!

Are you a...
            """,
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(buttons)
            )
    return 1

def fill_name(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    gender = query.data
    context.user_data['gender'] = gender

    query.edit_message_text(
            text="Send me your full name"
            )
    return 2

def confirm_name_registration(update:Update, context:CallbackContext) ->int:
    name = update.message.text.rstrip().lstrip()
    context.user_data["name"] = name
    buttons = [
            [InlineKeyboardButton(text="Confirm", callback_data="forward")],
            [InlineKeyboardButton(text="Edit name", callback_data="back")]
            ]
    update.message.reply_text(
            text=f"You have sent me: <u>{name}</u>\nConfirm?",
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(buttons)
            )
    return 3


def commit_registration(update:Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user = update.effective_user

    name = context.user_data['name'] 
    telegram_user = user.username
    gender = context.user_data['gender']

    bot_message = query.edit_message_text(
            text=f"registering... {name}  "
            )
    with sqlite3.connect(CONFIG['database']) as db:
        db.execute("BEGIN TRANSACTION")
        data = (name, telegram_user, gender, user.id)
        db.execute('UPDATE players SET name = ?, telegram_user = ?, gender = ? WHERE id = ?', data)
        data = (1, user.id)
        db.execute('UPDATE access_control SET control_id=? WHERE player_id = ?', data)
        db.commit()

    text = f"""
You have sucessfully been registered! Please wait for the core team to approve your registration😊😊.

Full name : {name}
telegram handle : {telegram_user}
Gender : {gender}

Please do notify either <a href="tg://user?id=161579060">Owen</a>, <a href="tg://user?id=39135211">Mandy</a> or your contact in Alliance that you have already registered too!

    """
    bot_message.edit_text(
            text=text,
            parse_mode='html'
            )
    return ConversationHandler.END

@send_typing_action
@secure(access=2)
def review_membership(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    logger.info("user %s just initiated /apply_membership", user.first_name)

    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        access_control = db.execute('''
                SELECT control_id, access_control_description.description FROM access_control 
                JOIN access_control_description ON access_control.control_id = access_control_description.id
                WHERE player_id = ?
                ''',
                (user.id, )
                ).fetchone()
        if access_control['control_id'] >= 4:
            proposition = 'an' if access_control['description'] == 'Admin' else 'a'
            update.message.reply_text(
                    f'bruh you are already {proposition} {access_control["description"]} what are you even doing here..'
                    )
            logger.info("user %s was just fking around..", user.first_name)
            return ConversationHandler.END


    with open(os.path.join("resources", 'messages', 'membership_registration_terms.txt')) as f:
        text = f.read()
    buttons = [
            [InlineKeyboardButton(text="I wanna be part of Alliance😊", callback_data="forward")],
            [InlineKeyboardButton(text="Maybe another time.", callback_data="cancel")]
            ]
    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode='html')
    return 1

def commit_membership_position(update:Update, context:CallbackContext) -> int:
    user =  update.effective_user
    query = update.callback_query
    query.answer()
    
    if query.data == "forward":
        with sqlite3.connect(CONFIG['database']) as db:
            db.execute('BEGIN TRANSACTION')
            db.execute('UPDATE access_control SET control_id = 3 WHERE player_id = ?', (user.id, ))
            db.commit()
        text = f"""
Thank you for your interest in being a club member of Alliance😇😇!!
Your commitment has been noted and is under the review of the core team 🥹
        """
        query.edit_message_text(text=text)
        logger.info("user %s is now pending alliance membership approval", user.first_name)
        return ConversationHandler.END
    else:
        query.edit_message_text("We hope to see you soon!!")
        logger.info("user %s fking alibaba one", user.first_name)
        return ConversationHandler.END


@send_typing_action
def cancel(update:Update, context: CallbackContext) -> int:
    user = update.effective_user
    update.message.reply_text(
            text="process cancelled, see you next time!"
            )
    logger.info('user %s just cancelled a process', user.first_name)
    return ConversationHandler.END

def main():
    with open(os.path.join(".secrets", "bot_credentials.json"), "r") as f:
            bot_tokens = json.load(f)

    if CONFIG["development"]:
        token = bot_tokens["dev_bot"]
    else:
        token = bot_tokens["alliance_bot"]

    commands = [
            BotCommand("start", "to start the bot"),
            BotCommand("attendance", "update attendance"),
            BotCommand("kaypoh", "your friend never go u dw go is it??"),
            BotCommand("attendance_plus", "one shot update attendance"),
            BotCommand("events", "events that you are attending"),
            BotCommand("event_details", "generate ics file for personal calendars"),
            BotCommand("settings", "access settings and refresh username if recently changed"),
            BotCommand("register", "use this command if you're a new player"),
            BotCommand("apply_membership", "use this command if you'll like to be part of Alliance!"),
            BotCommand("cancel", "cancel any process"),
            ]

    Bot(token).set_my_commands(commands)

    updater = Updater(token)

    #dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler_attendance = ConversationHandler(
            entry_points=[CommandHandler("attendance", choosing_date_low_access)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$'),
                    CallbackQueryHandler(indicate_attendance, pattern='^(\d{10}|\d{12})$')
                    ],
                2 : [
                    CallbackQueryHandler(give_reason, pattern="^No$"),
                    CallbackQueryHandler(give_reason, pattern="^Yes$"),
                    CallbackQueryHandler(update_attendance, pattern="^Yas$"),
                    MessageHandler(Filters.text & ~Filters.command ,update_attendance)
                    ],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
            )

    conv_handler_kaypoh = ConversationHandler(
            entry_points=[CommandHandler("kaypoh", choosing_date_high_access)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$'),
                    CallbackQueryHandler(attendance_list, pattern='^(\d{10}|\d{12})$')
                    ],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
            )

    conv_handler_mass_attendance = ConversationHandler(
            entry_points=[CommandHandler("attendance_plus", choosing_more_dates)],
            states={
                1 : [
                    CallbackQueryHandler(choosing_more_dates_cont, pattern='^(\d{10}|\d{12})$'),
                    CallbackQueryHandler(indicate_more, pattern='^forward$')
                    ],
                2 : [
                    CallbackQueryHandler(give_reason_more, pattern="^0$"),
                    CallbackQueryHandler(commit_attendance_plus, pattern="^1$"),
                    MessageHandler(Filters.text & ~Filters.command, commit_attendance_plus)
                    ],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
            )
    
    conv_handler_save_event = ConversationHandler(
            entry_points=[CommandHandler("event_details", choosing_date_low_access)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$'),
                    CallbackQueryHandler(generate_ics, pattern='^(\d{10}|\d{12})$')
                    ],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
            )

    conv_handler_settings = ConversationHandler(
            entry_points=[CommandHandler("settings",settings_start)],
            states={
                1 : [
                    CallbackQueryHandler(name_change, pattern="^name$"),
                    CallbackQueryHandler(notification_change, pattern="^notification$"),
                    CallbackQueryHandler(language_change, pattern="^language$")
                    ],
                1.1 : [MessageHandler(Filters.text & ~Filters.command, confirmation_name_change)],
                1.2 :[CallbackQueryHandler(commit_notification_change, pattern="^\d$")],
                2.1 : [
                CallbackQueryHandler(commit_name_change, pattern="^forward$"),
                CallbackQueryHandler(name_change, pattern="^back$")
                ],
   },
            fallbacks=[CommandHandler('cancel',cancel)],
                        )

    conv_handler_register = ConversationHandler(
            entry_points = [CommandHandler("register", select_gender)],
            states={
                1 : [
                    CallbackQueryHandler(fill_name, pattern='^Male$'),
                    CallbackQueryHandler(fill_name, pattern='Female')
                    ],
                2 : [
                    MessageHandler(Filters.text & ~Filters.command, confirm_name_registration),
                    ],
                3 : [
                    CallbackQueryHandler(commit_registration, pattern='^forward$')
                    ],
                },
            fallbacks=[CommandHandler('cancel', cancel)],
            )
    conv_handler_apply_members = ConversationHandler(
            entry_points = [CommandHandler("apply_membership", review_membership)],
            states={
                1 : [
                    CallbackQueryHandler(commit_membership_position),
                    ],
                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )


    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(conv_handler_attendance)
    dispatcher.add_handler(conv_handler_kaypoh)
    dispatcher.add_handler(conv_handler_mass_attendance)
    dispatcher.add_handler(CommandHandler("events", events))
    dispatcher.add_handler(conv_handler_register)
    dispatcher.add_handler(conv_handler_save_event)
    dispatcher.add_handler(conv_handler_settings)
    dispatcher.add_handler(conv_handler_apply_members)
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
