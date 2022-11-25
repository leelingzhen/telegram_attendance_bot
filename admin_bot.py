import logging
import os
import helpers
import json
import sqlite3

from datetime import date, datetime, timedelta
from functools import wraps

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
            if user_clearance < 5:
                print("WARNING: Unauthorized access denied for @{}.".format(user.username))
                update.message.reply_text(
                        text='you do not have access to this bot, please contact adminstrators'
                        )
                return
            elif user_clearance < access:
                print("WARNING: Unauthorized access denied for @{}.".format(user.username))
                update.message.reply_text(
                        text='you do not have access to this function, please contact adminstrators'
                        )
                return  # quit function
            return func(update, context, *args, **kwargs)
        return wrapped
    return decorator


@secure(access=5)
@send_typing_action
def start(update: Update, context: CallbackContext)-> None:
    
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

            return None

    context.bot.send_message(
            chat_id=chat_id,
            text="Hello please use the commands to talk to me!"
            )
    return None

@secure(access=5)
@send_typing_action
def choosing_date(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    logger.info("user %s is choosing date...", user.first_name)
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        event_data = db.execute("SELECT id, event_type FROM events WHERE id > ? ORDER BY id", (date.today().strftime('%Y%m%d%H%M'), )).fetchall()

    context.user_data["event_data"] = event_data
    context.user_data["page"] = 0

    reply_markup = InlineKeyboardMarkup(helpers.date_buttons(event_data, 0))
    # if there are no queried trainings
    if event_data == list():
        update.message.reply_text("There are no more further planned events. Please add a new one using!/add_event")
        return ConversationHandler.END 

    update.message.reply_text( 
            text="Choose event:",
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

def reply_attendance_list(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        text="generating attendance list..."
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
        unindicated += row['name'] + " - @" + row['telegram_user'] + '\n'


    text = f"""
Attendance for <b>{event['event_type']}</b> on <u>{event_date.strftime('%-d-%b-%y, %a @ %-I:%M%p')}</u> : {len(player_data['attending_boys']) + len(player_data['attending_girls'])}

Attending boys: {len(player_data['attending_boys'])}
{attending_boys}
Attending girls: {len(player_data['attending_girls'])}
{attending_girls}
Absent: {len(player_data['absent'])}
{absent}
Not Indicated: {len(unindicated_data)}
{unindicated}

    """
    query.edit_message_text(text=text, parse_mode='html')
    user = update.effective_user
    logger.info("user %s has sucessfully queried attendance on event %s", user.first_name, event_date.strftime("%d-%m-%Y"))

    return ConversationHandler.END

@secure(access=5)
@send_typing_action
def announce_all(update:Update, context: CallbackContext) -> int:
    logger.info("User %s initiated process: announce all", update.effective_user.first_name)
    #conversation state
    conv_state = 0
    context.user_data['conv_state'] = conv_state

    update.message.reply_text(
            'You will be sending an annoucement to all active players in alliance through @alliance_training_bot. '
            'Send /cancel to cancel the process\n\n'
            'Please send me your message here!'
            )

    context.user_data['conv_state'] += 1
    return context.user_data['conv_state']

@send_typing_action
def confirm_message(update:Update, context: CallbackContext) -> int:
    buttons = [
            [InlineKeyboardButton(text="Confirm", callback_data="forward")],
            [InlineKeyboardButton(text="Edit Message", callback_data="back")]
            ]

    #getting announcement message and entities, then storing
    announcement = update.message.text
    announcement_entities = update.message.entities
    context.user_data['announcement'] = announcement
    context.user_data['announcement_entities'] = announcement_entities
    bot_message = update.message.reply_text(
            'You have sent me: \n\n',
            )
    update.message.reply_text(
            text=announcement ,
            entities=announcement_entities
            )
    update.message.reply_text(
            text="Confirm message?",
            reply_markup=InlineKeyboardMarkup(buttons)
            )

    context.user_data['conv_state'] += 1
    return context.user_data['conv_state']

@send_typing_action
def edit_msg(update:Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            'Please send me your message here again!'
            )

    context.user_data['conv_state'] -= 1
    return context.user_data['conv_state']


def write_message(update:Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    event_id = int(query.data)
    event_date = datetime.strptime(str(event_id), '%Y%m%d%H%M')
    with sqlite3.connect(CONFIG['database']) as db:
        event_type = db.execute("SELECT event_type FROM events WHERE id = ?", (event_id, )).fetchone()[0]
    
     
    context.user_data['event_date'] = event_date
    context.user_data['event_id'] = event_id
    context.user_data['event_type'] = event_type
    query.edit_message_text(
            f"You have choosen <u>{event_type}</u> on <u>{event_date.strftime('%d-%b, %a @ %-I:%M%p')}</u>.\n\n"
            "Write your message to players who are <u>attending</u> and <u>active players who have not indicated</u> attendance here. "
            "If you have choosen an earlier date, you can send <b>training summaries</b> to players who attended too!",
            parse_mode="HTML"
            )
    context.user_data['conv_state'] = 2
    return context.user_data['conv_state']


@send_typing_action
def send_event_message(update:Update, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    #getting relevant data
    event_id = context.user_data['event_id']
    event_date = context.user_data['event_date']
    event_type = context.user_data['event_type']

    attached_str = event_type + ' on ' + event_date.strftime('%d-%b, %a @ %-I:%M%p')
    comment = f"Message for {attached_str}"

    admin_msg=query.edit_message_text(
                "saving event announcement...\n"
                )
    msg = f"{context.user_data['announcement']}\n\n{comment}\n\n- @{user.username}"
    msg_entities = context.user_data['announcement_entities']
    msg_entities.append(
            MessageEntity(
                type="italic",
                offset=len(context.user_data['announcement']) + 2,
                length=len(comment)
                )
            )

    with sqlite3.connect(CONFIG['database']) as db:
        db.execute('BEGIN TRANSACTION')
        entity_data = list()
        for entity in msg_entities:
            data = (event_id, entity.type, entity.offset, entity.length)
            entity_data.append(data)

        existing_announcement = db.execute('SELECT event_id FROM announcement_entities WHERE event_id= ?', (event_id,)).fetchall()
        # remove existing entities
        if len(existing_announcement) > 0:
            db.execute("DELETE FROM announcement_entities WHERE event_id = ?", (event_id, ))

        db.executemany("INSERT INTO announcement_entities VALUES (?, ?, ?, ?)", entity_data)
        db.execute('UPDATE events SET announcement = ? WHERE id = ?', (msg, event_id))
        db.commit()
        
        admin_msg.edit_text(
            "getting players...\n"
            )
        with open(os.path.join('resources', 'saved_sql_queries', 'attending.sql')) as f:
            sql_query = f.read()
            db.row_factory = sqlite3.Row
            send_list = db.execute(sql_query,(event_id, )).fetchall()
        with open (os.path.join('resources', 'saved_sql_queries', 'unindicated_players.sql')) as f:
            sql_query = f.read()
            send_list += db.execute(sql_query, (event_id,)).fetchall()


    admin_msg.edit_text(
            "getting players... done.\n"
            f"Sending event announcements... 0/{len(send_list)}"
            )
    send_message_generator = helpers.mass_send(
            msg=msg,
            send_list=send_list,
            entities=msg_entities,
            development=CONFIG['development']
            )

    unsent_names = ''
    for i, _ in enumerate(send_list):
        unsent_name = next(send_message_generator)
        if unsent_name != "":
            unsent_names += ' @' + unsent_name +","
        admin_msg.edit_text(f"Sending event announcements... {i+1}/{len(send_list)}")


    admin_msg.edit_text(
            "Sending event announcements complete. list of uncompleted sends: \n\n" + unsent_names,
            )

    logger.info("User %s sucessfully sent event messages", user.first_name)
    return ConversationHandler.END

@send_typing_action
def send_message(update:Update, context:CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user = update.effective_user
    msg = context.user_data['announcement'] + f"\n\n\n\n- @{update.effective_user.username}"
    msg_entities= context.user_data['announcement_entities']

    #query data
    admin_msg_text = "getting active players..."
    admin_msg = query.edit_message_text(text=admin_msg_text)
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        with open(os.path.join('resources', 'saved_sql_queries', 'club_members.sql')) as f:
            sql = f.read()
        active_players = db.execute(sql).fetchall()


    admin_msg_text +="done.\nSending announcements... 0/{len(active_players)}"
    send_message_generator = helpers.mass_send(
            msg=msg,
            send_list=active_players,
            entities=msg_entities,
            development=CONFIG['development']
            )
    failed_send_list = ''
    for i in range(len(active_players)):
        failed_send_user = next(send_message_generator)
        if failed_send_user != "":
            failed_send_list += "@" + failed_send_user + ', '
        admin_msg.edit_text(f"Sending announcements... {i+1}/{len(active_players)}")

    admin_msg.edit_text(
            "Sending announcements complete. list of uncompleted sends: \n\n" + failed_send_list,
            )

    logger.info("User %s sucessfully sent announcements", user.first_name)
    return ConversationHandler.END

def send_reminders(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text="getting active_players..."
            )

    event_id = int(query.data)
    event_date = datetime.strptime(str(event_id), '%Y%m%d%H%M')
 
    #getting unindicated data
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        with open(os.path.join('resources', "saved_sql_queries", 'unindicated_players.sql')) as f:
            sql_query = f.read()
            unindicated_data = db.execute(sql_query, (event_id, )).fetchall()
            event_type = db.execute('SELECT event_type FROM events WHERE id = ?', (event_id, )).fetchone()


    #parsing message from file
    query.edit_message_text(
            text="Parsing gsheets... done.\nCrafting reminder message...\n"
            )
    attached_str = event_date.strftime('%d-%b-%y, %A') + ' (' + event_type["event_type"] + ')'
    remind_msg = helpers.read_msg_from_file(os.path.join("resources", 'messages', 'not_indicated.txt'), attached_str)

    query.edit_message_text(
            text=f"Parsing gsheets... done.\nCrafting reminder message... done.\nSending messages... 0/{len(unindicated_data)}\n"
            )
    send_message_generator = helpers.mass_send(
            msg=remind_msg,
            send_list=unindicated_data,
            parse_mode='HTML',
            development=CONFIG['development']
            )
    unsent_names = ''
    for i, _ in enumerate(unindicated_data):
        unsent_name = next(send_message_generator)
        if unsent_name != "":
            unsent_names += ' @' + unsent_name +","
        query.edit_message_text(
                text=f"Parsing gsheets... done.\nCrafting reminder message... done.\nSending messages... {i + 1}/{len(unindicated_data)}\n"
                )


    query.edit_message_text(
            text=f"Reminders have been sent sucessfully for {attached_str}\n\nUnsucessful sends: \n{unsent_names}"
            )

    logger.info("reminders sent successfuly by User %s", update.effective_user.first_name)
    return ConversationHandler.END

@secure(access=5)
@send_typing_action
def choosing_date_administration(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    logger.info("user %s has started /event_adminstration...", user.first_name)
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        event_data = db.execute("SELECT id, event_type FROM events WHERE id > ? ORDER BY id", (date.today().strftime('%Y%m%d%H%M'), )).fetchall()

    context.user_data["event_data"] = event_data

    buttons = helpers.date_buttons(event_data, pages=False)
    buttons.append(
                [
                    InlineKeyboardButton(text="Add Event", callback_data='add'),
                ]
            )

    reply_markup = InlineKeyboardMarkup(buttons)
    # if there are no queried trainings
    if event_data == list():
        update.message.reply_text("There are no more further planned events. Please add a new one using!/event_adminstration")
        return ConversationHandler.END 

    update.message.reply_text( 
            text="Choose event:",
            reply_markup=reply_markup
            )
    return 1



@secure(access=5)
def initialise_event_date(update:Update, context:CallbackContext)-> int:

    query = update.callback_query
    query.answer()
    user = update.effective_user

    if query.data == "add":
        context.user_data['event_data'] = {}
        context.user_data['event_creation'] = True
        query.edit_message_text(
                text=f"Text me the starting datetime of the event in the format dd-mm-yyyy@HHMM\n\nEg. {datetime.now().strftime('%d-%m-%Y@%H%M')} "
                )
        return 2

    else:
        context.user_data['event_creation'] = False
        event_id = int(query.data)
        with sqlite3.connect(CONFIG['database']) as db:
            db.row_factory = sqlite3.Row
            event_data = db.execute('SELECT * FROM events WHERE id = ?', (event_id, )).fetchone()
            event_data = dict(event_data)
            context.user_data['event_data'] = event_data
        buttons = [
                [InlineKeyboardButton(text="Edit event", callback_data='edit')], 
                [InlineKeyboardButton(text="Remove event", callback_data='remove')]
                ]
        reply_markup = InlineKeyboardMarkup(buttons)
        query.edit_message_text(
                text="What would you like to do?",
                reply_markup=reply_markup
                )
        return 2

@secure(access=5)
@send_typing_action
def first_event_menu(update:Update, context:CallbackContext)-> int:
    event_data = context.user_data['event_data']

    buttons =[
                [InlineKeyboardButton(text="Event datetime", callback_data='start')],
                [InlineKeyboardButton(text="Ending time", callback_data='end_time')],
                [InlineKeyboardButton(text="Event type", callback_data='type')],
                [InlineKeyboardButton(text='Location', callback_data='location')],
                [InlineKeyboardButton(text='Access', callback_data='access')],
                ]

    if event_data == {}:
        try:
            event_date = datetime.strptime(update.message.text, "%d-%m-%Y@%H%M")

        except ValueError:
            update.message.reply_text(
                    text="There seems to be something wrong with the format, text me the date again in this format dd-mm-yyyy@HHMM"
                    )
            return 2

        else:
            event_id = int(event_date.strftime("%Y%m%d%H%M"))
            context.user_data['original_id'] = event_id
            event_data = {
                    'id' : event_id,
                    'event_type' : "Field Training",
                    'event_date' : event_date.strftime("%Y-%m-%d"),
                    'start_time' : event_date.strftime("%H:%M"),
                    'end_time' : (event_date + timedelta(hours=2)).strftime("%H:%M"),
                    'location' : str(),
                    'announcement' : str(),
                    'access_control' : 2
                    }
            context.user_data['event_data'] = event_data

            buttons.append(
                    [
                        #InlineKeyboardButton(text='Announce', callback_data='announce'),
                        InlineKeyboardButton(text="Confirm Changes", callback_data="forward")
                        ]
                    )
            bot_message = update.message.reply_text(text="initialising event...")
    else:
        query = update.callback_query
        query.answer()
        bot_message = query.edit_message_text("initialising event...")
        event_date = datetime.strptime(str(event_data['id']), '%Y%m%d%H%M')
        context.user_data['original_id'] = event_data['id']

        if query.data == 'edit':
           buttons.append([InlineKeyboardButton(text="Confirm Changes", callback_data="forward")])
        elif query.data == 'remove':
            buttons = [
                    [InlineKeyboardButton(text="Confirm Deletion?", callback_data="delete")],
                    ]

    reply_markup = InlineKeyboardMarkup(buttons)
    bot_message.edit_text(
            text=f"""
event date : {event_date.strftime('%d-%m-%y, %a')}
start : {event_data['start_time']}
end : {event_data['end_time']}
type of event : {event_data['event_type']}
location : {event_data['location']}
access : {event_data['access_control']}
                    """,
            reply_markup=reply_markup
            )
    return 3

@secure(access=5)
@send_typing_action
def event_menu(update:Update, context:CallbackContext)-> int:
    prev_form = context.user_data['form'] # data is 'query' or 'datetime' or 'time'
    text = ''
    buttons =[
                [InlineKeyboardButton(text="Event datetime", callback_data='start')],
                [InlineKeyboardButton(text="Ending time", callback_data='end_time')],
                [InlineKeyboardButton(text="Event type", callback_data='type')],
                [InlineKeyboardButton(text='Location', callback_data='location')],
                [InlineKeyboardButton(text='Access', callback_data='access')],
                [
                    #InlineKeyboardButton(text="Announce", callback_data='announce'), 
                    InlineKeyboardButton(text='Confirm Changes', callback_data='forward')
                    ]
                ]
    if prev_form == "rejected":
        query = update.callback_query
        query.answer()
        bot_message = query.edit_message_text('returning to event menu...')

    elif prev_form == 'query':
        query = update.callback_query
        query.answer()
        bot_message = query.edit_message_text('parsing new changes...')
        data_update = query.data.split(',')
        if data_update[0] == 'access_control':
            context.user_data['event_data'][data_update[0]] = int(data_update[1])
        else:
            context.user_data['event_data'][data_update[0]] = data_update[1]
            

        
    else:

        bot_message = update.message.reply_text('parsing new changes...')
        if prev_form == "datetime":
            try:
                event_date = datetime.strptime(update.message.text, "%d-%m-%Y@%H%M")

            except ValueError:
                text = "<b>Format seems to be wrong. Please try again.</b>\n\n "
            else:
                context.user_data['event_data']['id'] = int(event_date.strftime("%Y%m%d%H%M"))
                context.user_data['event_data']['event_date'] = event_date.strftime("%Y-%m-%d")
                context.user_data['event_data']['start_time'] = event_date.strftime("%H:%M")

        elif prev_form == "time":
            try:
                event_time = datetime.strptime(update.message.text, "%H%M")
            except ValueError:
                text = "<b>Format seems to be wrong. Please try again.</b>\n\n "
            else:
                context.user_data['event_data']['end_time'] = event_time.strftime("%H:%M")

        elif prev_form == 'location':
            context.user_data['event_data']['location'] = update.message.text

            
    event_data = context.user_data['event_data']
    event_date = datetime.strptime(str(event_data['id']), '%Y%m%d%H%M')

    text+=f"""
event date : {event_date.strftime('%d-%m-%y, %a')}
start : {event_data['start_time']}
end : {event_data['end_time']}
type of event : {event_data['event_type']}
location : {event_data['location']}
access : {event_data['access_control']}
                    """
    reply_markup = InlineKeyboardMarkup(buttons)
    bot_message.edit_text(
            text=text,
            parse_mode='html',
            reply_markup=reply_markup
            )

    # clear form
    context.user_data['form'] = ''
    return 3

def change_datetime(update:Update, context:CallbackContext) -> str:
    context.user_data['form'] = 'datetime'
    event_id = context.user_data['event_data']['id']
    event_date = datetime.strptime(str(event_id),'%Y%m%d%H%M')
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text=f"""
Text me the starting datetime of the event in the format dd-mm-yyyy@HHMM

Note:
It is <u><b>not recommended</b></u> to change the starting date and time of an event. Only do so after a consensus on a schedule changed has been reached.

<i>Otherwise, affected players attending the event will not know of the schedule change but their attendance will still reflect as per previous schedule</i>
\n\nEg. original datetime: <code>{event_date.strftime('%d-%m-%Y@%H%M')}</code>""",
            parse_mode='html'
                    )

    return "event_menu"

def change_time(update:Update, context:CallbackContext) -> str:
    context.user_data['form'] = 'time'
    query = update.callback_query
    query.answer()
    query.edit_message_text(f"Text me the ending time of the event in the format HHMM\n\n For eg. time now: {datetime.now().strftime('%H%M')}")

    return "event_menu"

def formatting_error(update:Update, context:CallbackContext) -> int:
    update.message.reply_text(
            "Format seems to be wrong please try again "
            )
    return 'event_menu'


def edit_type(update:Update, context:CallbackContext) -> str:
    context.user_data['form'] = 'query'
    query = update.callback_query
    query.answer()

    buttons = [
           [InlineKeyboardButton(text='Field Training', callback_data='event_type,Field Training')],
           [InlineKeyboardButton(text='Scrim', callback_data='event_type,Scrim')],
           [InlineKeyboardButton(text='Hardcourt/Track', callback_data='event_type,Hardcourt/Track')],
           [InlineKeyboardButton(text='Gym/Pod', callback_data='event_type,Gym/Pod')],
           [InlineKeyboardButton(text='Cohesion', callback_data='event_type,Cohesion')],
            ]
    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text(
            text=f"""
Select the type of event:
(You may use Scrim to indicate tournament availability as well)

            """,
            reply_markup=reply_markup
            )
    return "event_menu"

def edit_location(update:Update, context:CallbackContext) -> str:
    context.user_data['form'] = 'location'
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text=f"""
Text the location of the event.
Generic location titles or google map links are accepted
            """
            )

    return "event_menu"

def edit_access(update:Update, context:CallbackContext) -> str:
    context.user_data['form'] = 'query'
    query = update.callback_query
    query.answer()
    buttons = [
           [InlineKeyboardButton(text='Guest (2)', callback_data='access_control,2')],
           [InlineKeyboardButton(text='Club Members (4)', callback_data='access_control,4')],
           [InlineKeyboardButton(text='Core (5)', callback_data='access_control,5')],
            ]
    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text(
            text="Choose the access level for the event, members of higher access control can participate in events of lower access control\n\n for eg. Club members can participate in events with 'Guest' level access",
            reply_markup=reply_markup
            )

    return "event_menu"

def delete_event(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    event_id = context.user_data['event_data']['id']
    event_date = datetime.strptime(str(event_id), "%Y%m%d%H%M")
    with sqlite3.connect(CONFIG['database']) as db:
        db.execute("BEGIN TRANSACTION")
        db.execute("DELETE FROM events WHERE id = ?", (event_id, ))
        db.execute("DELETE FROM attendance WHERE event_id = ?", (event_id, ))
        db.commit()

    query.edit_message_text("event has been delete sucessfully.")
    logger.info("user %s has deleted event on %s", user.first_name, event_date.strftime("%d-%m-%y"))
    return ConversationHandler.END


def commit_event_changes(update:Update, context:CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    user = update.effective_user

    event_id = context.user_data['event_data']['id']
    original_id = context.user_data['original_id']

    with sqlite3.connect(CONFIG['database']) as db:
        #first check if there are duplicated events
        existing_events = db.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchall()
        event_data = context.user_data['event_data']

        db.execute("BEGIN TRANSACTION")
        if context.user_data['event_creation']:
            if len(existing_events) > 0:
                buttons = [[InlineKeyboardButton(text='Return to menu', callback_data='^back$')]]
                context.user_data['form'] = 'rejected'
                query.edit_message_text(
                        text="There already exists an event at this time and date. please edit starting datetime",
                        reply_markup=InlineKeyboardMarkup(buttons)
                        )
                return "event_menu"

            query.edit_message_text('creating new event...')
            data = [
                            event_data['id'], 
                            event_data['event_type'],
                            event_data['event_date'],
                            event_data['start_time'],
                            event_data['end_time'],
                            event_data['location'],
                            None,
                            event_data['access_control'],
                            ]
            db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)", data)
        else:

            if original_id != event_id and len(existing_events) > 0:
                buttons = [[InlineKeyboardButton(text='Return to menu', callback_data='^back$')]]
                context.user_data['form'] = 'rejected'
                query.edit_message_text(
                        text="There already exists an event at this time and date. please edit starting datetime",
                        reply_markup=InlineKeyboardMarkup(buttons)
                        )
                return "event_menu"

            query.edit_message_text('updating event...')
            data = [
                    event_data['id'],
                    event_data['event_type'],
                    event_data['event_date'],
                    event_data['start_time'],
                    event_data['end_time'],
                    event_data['location'],
                    event_data['access_control'],
                    original_id
                    ]
            db.execute("UPDATE events SET id = ?, event_type = ?, event_date = ?, start_time = ?, end_time = ?, location = ?, access_control = ? WHERE id = ?", data)

            #update id change on attendance
            db.execute("UPDATE attendance SET event_id = ? WHERE event_id = ?", (event_data['id'], original_id))
        db.commit()
    query.edit_message_text(
            text="event sucessfully added/updated! Announce new event or changes by /announce_event!"
            )
    logger.info("user %s has successfully updated an event", user.first_name)
        
    return ConversationHandler.END

@secure(access=6)
@send_typing_action
def choose_access_level(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    logger.info("user %s is started /access_control_administration", user.first_name)
    
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        user_access = db.execute('SELECT control_id FROM access_control WHERE player_id = ? ', (user.id, )).fetchone()['control_id']
        if user_access == 7:
            access_data = db.execute('SELECT * FROM access_control_description WHERE id <= ? ORDER BY id', (user_access, )).fetchall()
        else:
            access_data = db.execute('SELECT * FROM access_control_description WHERE id < ? ORDER BY id', (user_access, )).fetchall()

    if user_access < 7:
        access_data = access_data[1:]

    buttons = list()
    for row in access_data:
        button = InlineKeyboardButton(text=row['description'], callback_data=str(row['id']))
        buttons.append([button])

    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text(
            text='Pick level of access control:',
            reply_markup=reply_markup
            )
    
    return 1

@secure(access=6)
def choose_access_level_again(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        user_access = db.execute('SELECT control_id FROM access_control WHERE player_id = ? ', (user.id, )).fetchone()['control_id']
        if user_access == 7:
            access_data = db.execute('SELECT * FROM access_control_description WHERE id <= ? ORDER BY id', (user_access, )).fetchall()
        else:
            access_data = db.execute('SELECT * FROM access_control_description WHERE id < ? ORDER BY id', (user_access, )).fetchall()

    if user_access < 7:
        access_data = access_data[1:]

    buttons = list()
    for row in access_data:
        button = InlineKeyboardButton(text=row['description'], callback_data=str(row['id']))
        buttons.append([button])

    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text(
            text='Pick position:',
            reply_markup=reply_markup
            )
    
    return 1


@secure(access=6)
def choose_players(update:Update, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    try:
        selected_access = int(query.data)
    except ValueError:
        selected_access = context.user_data['selected_access']
    context.user_data['selected_access'] = selected_access

    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        player_data = db.execute("""
                SELECT id, name, telegram_user, access_control.control_id FROM players
                JOIN access_control ON players.id = access_control.player_id
                WHERE control_id = ?
                ORDER BY
                name
                """,
                (selected_access, )
                ).fetchall()

    buttons = list()
    for row in player_data:
        button = InlineKeyboardButton(text=row['name'], callback_data=str(row['id']))
        buttons.append([button])
    buttons.append([InlineKeyboardButton(text="Back", callback_data='back')])
    reply_markup=InlineKeyboardMarkup(buttons)

    query.edit_message_text(
            text="Choose player",
            reply_markup=reply_markup
            )

    return 2

@secure(access=6)
def change_player_access(update:Update, context:CallbackContext) -> int:
    query =  update.callback_query
    query.answer()
    try:
        selected_player_id = int(query.data)
    except ValueError:
        selected_player_id = context.user_data['selected_player_id']

    context.user_data['selected_player_id'] = selected_player_id
    selected_access = context.user_data['selected_access']
    buttons = [
            [InlineKeyboardButton(text="Upgrade", callback_data='1')],
            [InlineKeyboardButton(text="Downgrade", callback_data='-1')],
            [InlineKeyboardButton(text="Kick", callback_data="0")],
            ]
    with sqlite3.connect(CONFIG['database']) as db:
        db.row_factory = sqlite3.Row
        player_data = db.execute("""
                SELECT id, name, telegram_user, gender FROM players
                WHERE id = ?
                """,
                (selected_player_id, )).fetchone()

        position = db.execute("SELECT description FROM access_control_description WHERE id = ?", (selected_access, )).fetchone()['description']
        context.user_data['player_data'] = player_data
        context.user_data['position'] = position


    buttons = [
        [InlineKeyboardButton(text="Upgrade", callback_data='1')],
        [InlineKeyboardButton(text="Downgrade", callback_data='-1')],
        [InlineKeyboardButton(text="Kick", callback_data="0")],
        ]

    reply_markup = InlineKeyboardMarkup(buttons)
    text = f"""
Player : {player_data['name']}
handle : @{player_data['telegram_user']}
gender : {player_data['gender']}
position : {position}

What would you like to do?

    """
    query.edit_message_text(
            text=text,
            reply_markup=reply_markup
            )

    return 3


@secure(access=6)
def review_access_change(update:Updater, context:CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    move = int(query.data)

    selected_player_id = context.user_data['selected_player_id']
    selected_access = context.user_data['selected_access']
    player_data = context.user_data['player_data']
    position = context.user_data['position']

    if move == 0:
        new_selected_access = move
    else:
        new_selected_access = selected_access + move
    context.user_data['new_selected_access'] = new_selected_access

    with sqlite3.connect(CONFIG['database']) as db:
        new_position = db.execute('SELECT description FROM access_control_description WHERE id = ?', (new_selected_access,)).fetchone()[0]
        context.user_data['new_position'] = new_position

    buttons = [
            [InlineKeyboardButton(text='Confirm position', callback_data='^forward$')],
            ]
    reply_markup = InlineKeyboardMarkup(buttons)
    text = f"""
Player : {player_data['name']}
handle : @{player_data['telegram_user']}
gender : {player_data['gender']}
position : {position}
new position : {new_position}

Confirm new position for {player_data['name']}?
    """
    query.edit_message_text(
            text=text,
            reply_markup=reply_markup
            )
    return 4
    

@secure(access=6)
def commit_access_change(update:Updater, context:CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    selected_player_id = context.user_data['selected_player_id']
    selected_access = context.user_data['selected_access']
    new_selected_access = context.user_data['new_selected_access']
    old_pos = context.user_data['position']
    new_pos = context.user_data['new_position']
    with sqlite3.connect(CONFIG['database']) as db:
        player_name = db.execute('SELECT name FROM players WHERE id = ?', (selected_player_id, )).fetchone()[0]
        db.execute('BEGIN TRANSACTION')
        db.execute('UPDATE access_control SET control_id = ? WHERE player_id = ?', (new_selected_access, selected_player_id))
        db.commit()
    query.edit_message_text(text=f"{player_name} is now {new_pos}")
    logger.info("user %s sucessfully changed the access control of %s from %s to %s", user.first_name, player_name, old_pos, new_pos)
    return ConversationHandler.END

@send_typing_action
def cancel(update:Update, context: CallbackContext) -> int:
    user = update.effective_user

    context.bot.send_message(
            chat_id=user.id,
            text="process cancelled, see you next time!"
            )
    logger.info("user %s has cancelled a process", user.first_name)
    return ConversationHandler.END

def main():
    with open(os.path.join(".secrets", "bot_credentials.json"), "r") as f:
            bot_tokens = json.load(f)

    if CONFIG["development"]:
        admin_token = bot_tokens["admin_dev_bot"]
    else:
        admin_token = bot_tokens["admin_bot"]

    #setting command list
    commands = [
            BotCommand("start", "to start a the bot"),
            BotCommand("attendance_list", "get attendance of players for an event"),
            BotCommand("announce_all", "send message to active players through telegram bot"),
            BotCommand("announce_event", "send announcement to active players on specified training date, only absent players will not get message"),
            BotCommand("remind", "send reminders to players to update attendance on specified event"),
            BotCommand("event_administration", "add, edit or delete event"),
            BotCommand("access_control_administration", "change access control of players"),
            BotCommand("cancel", "cancel any existing operation"),
            BotCommand("help", "help"),
            ] 
    Bot(admin_token).set_my_commands(commands)

    updater = Updater(admin_token)
    dispatcher = updater.dispatcher

    conv_handler_attendance_list = ConversationHandler(
            entry_points=[CommandHandler('attendance_list', choosing_date)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$' ),
                    CallbackQueryHandler(reply_attendance_list, pattern='^(\d{10}|\d{12})$')
                    ],
                },
            fallbacks=[CommandHandler('cancel', cancel)],
            )

    conv_handler_announce = ConversationHandler(
            entry_points=[CommandHandler('announce_all', announce_all)],
            states={
                1 : [MessageHandler(Filters.text & ~Filters.command ,confirm_message)],
                2 : [
                    CallbackQueryHandler(send_message, pattern=f'^forward$'),
                    CallbackQueryHandler(edit_msg, pattern=f'^back$')
                    ],
                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )

    conv_handler_announce_event = ConversationHandler(
            entry_points=[CommandHandler('announce_event', choosing_date)],
            states={
                1 : [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$' ),
                    CallbackQueryHandler(write_message, pattern='^(\d{10}|\d{12})$'),
                    ], 
                2 : [MessageHandler(Filters.text & ~Filters.command ,confirm_message)],
                3 : [
                    CallbackQueryHandler(send_event_message, pattern=f'^forward$'),
                    CallbackQueryHandler(edit_msg, pattern=f'^back$')
                    ],

                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )
    conv_handler_remind = ConversationHandler(
        entry_points=[CommandHandler("remind", choosing_date)],
        states={
            1 : [
                CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$' ),
                CallbackQueryHandler(send_reminders, pattern='^(\d{10}|\d{12})$')
                ],
            },
        fallbacks=[CommandHandler('cancel', cancel)],
        )

    conv_handler_event_administration = ConversationHandler(
            entry_points=[CommandHandler('event_administration', choosing_date_administration)],
            states={
                1 : [
                    CallbackQueryHandler(initialise_event_date, pattern="^(\d{10}|\d{12})$"),
                    CallbackQueryHandler(initialise_event_date, pattern="add"),
                    ],
                2 : [
                    CallbackQueryHandler(first_event_menu, pattern="^edit$"),
                    CallbackQueryHandler(delete_event, pattern="^remove$"),
                    MessageHandler(Filters.text & ~Filters.command ,first_event_menu)
                    ],
                3:[
                    CallbackQueryHandler(change_datetime, pattern="^start$"),
                    CallbackQueryHandler(change_time, pattern='^end_time$'),
                    CallbackQueryHandler(edit_type, pattern='^type$'),
                    CallbackQueryHandler(edit_location, pattern='^location$'),
                    CallbackQueryHandler(edit_access, pattern='^access$'),
                    CallbackQueryHandler(commit_event_changes, pattern='^forward$'),
                    ],
                'event_menu' : [
                    CallbackQueryHandler(event_menu),
                    MessageHandler(Filters.regex('^([1-9]|([012][0-9])|(3[01]))-([0]{0,1}[1-9]|1[012])-\d\d\d\d@([0-1]?[0-9]|2?[0-3])([0-5]\d)$'), event_menu),
                    MessageHandler(Filters.regex('^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'), event_menu),
                    MessageHandler(Filters.text & ~Filters.command, event_menu),
                    ]
                },
            fallbacks=[CommandHandler('cancel', cancel)],
            )
    conv_handler_access_administration = ConversationHandler(
            entry_points=[CommandHandler('access_control_administration', choose_access_level)],
            states={
                1 : [
                    CallbackQueryHandler(choose_players)#, pattern='^\d$'),
                    ],
                2 : [
                    CallbackQueryHandler(choose_access_level_again, pattern='^back$'),
                    CallbackQueryHandler(change_player_access)#, pattern='^\d$'),
                    ],
                3 : [
                    CallbackQueryHandler(change_player_access, pattern='^back$'),
                    CallbackQueryHandler(review_access_change)#, pattern='^\d$'),
                    ],
                4: [CallbackQueryHandler(commit_access_change)],
                },
            fallbacks=[CommandHandler('cancel', cancel)]
            )


    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(conv_handler_attendance_list)
    dispatcher.add_handler(conv_handler_announce)
    dispatcher.add_handler(conv_handler_announce_event)
    dispatcher.add_handler(conv_handler_event_administration)
    dispatcher.add_handler(conv_handler_remind)
    dispatcher.add_handler(conv_handler_access_administration)
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
