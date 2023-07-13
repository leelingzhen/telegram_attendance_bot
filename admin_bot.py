import logging
import os
import json
import sqlite3
import src.utils as utils
import src.Upgrade.upgrade_manager

from datetime import datetime
from functools import wraps

from src.user_manager import UserManager, AdminUser
from src.event_manager import AdminEventManager

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

# enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


# typing wrapper
def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func


def secure(access=2):
    def decorator(func):
        # admin restrictions
        @wraps(func)
        def wrapped(update, context, *args, **kwargs):
            user = update.effective_user
            user_instance = UserManager(user)
            context.user_data['user_instance'] = user_instance
            if user_instance.access < 5:
                print("WARNING: Unauthorized access denied for @{}.".format(user.username))
                update.message.reply_text(
                        text='you do not have access to this bot, please contact adminstrators'
                        )
                return
            elif user_instance.access < access:
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
def start(update: Update, context: CallbackContext) -> None:
    user_instance = context.user_data['user_instance']

    if user_instance.retrieve_user_data() is None:
        return None
    context.bot.send_message(
            chat_id=user_instance.id,
            text="Hello please use the commands to talk to me!"
            )
    return None


@secure(access=5)
@send_typing_action
def choosing_date(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_instance = UserManager(user)

    logger.info("user %s is choosing date...", user.first_name)

    event_data = user_instance.get_event_dates()

    context.user_data["event_data"] = event_data
    context.user_data["page"] = 0

    reply_markup = InlineKeyboardMarkup(utils.date_buttons(event_data, 0))
    # if there are no queried trainings
    if event_data == list():
        update.message.reply_text("There are no more further planned events. Please add a new one using!/event_administration")
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
    reply_markup = InlineKeyboardMarkup(utils.date_buttons(context.user_data["event_data"], page_num=context.user_data["page"]))
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

    # retrieve selected event
    event_id = int(query.data)
    event_instance = AdminEventManager(event_id, record_exist=True)
    male_records, female_records, absentees, unindicated = event_instance.curate_attendance(attach_usernames=True)
    total_attendees = len(male_records) + len(female_records)
    event_date = datetime.strptime(str(event_id), '%Y%m%d%H%M')
    pretty_event_date = event_date.strftime('%-d-%b-%y, %a @ %-I:%M%p')

    sep = '\n'

    text = f"""
Attendance for <b>{event_instance.event_type}</b> on <u>{pretty_event_date}</u> : {total_attendees}

Attending boys: {len(male_records)}
{sep.join(male_records)}

Attending girls: {len(female_records)}
{sep.join(female_records)}

Absent: {len(absentees)}
{sep.join(absentees)}

Not Indicated: {len(unindicated)}
{sep.join(unindicated)}
    """
    query.edit_message_text(text=text, parse_mode='html')
    user = update.effective_user
    logger.info("user %s has sucessfully queried attendance on event %s", user.first_name, event_date.strftime("%d-%m-%Y"))

    return ConversationHandler.END


@secure(access=5)
@send_typing_action
def announce_all(update: Update, context: CallbackContext) -> int:
    logger.info("User %s initiated process: announce all", update.effective_user.first_name)
    user = update.effective_user

    user_instance = AdminUser(user)

    # conversation state
    conv_state = 0
    context.user_data['conv_state'] = conv_state
    context.user_data['user_instance'] = user_instance

    update.message.reply_text(
            f'You will be sending an annoucement to all active players in {CONFIG["team_name"]} through {CONFIG["training_bot_name"]}. '
            'Send /cancel to cancel the process\n\n'
            'Please send me your message here!'
            )

    context.user_data['conv_state'] += 1
    return context.user_data['conv_state']


@send_typing_action
def confirm_message(update: Update, context: CallbackContext) -> int:
    buttons = [
            [InlineKeyboardButton(text="Confirm", callback_data="forward")],
            [InlineKeyboardButton(text="Edit Message", callback_data="back")]
            ]

    # getting announcement message and entities, then storing
    announcement = update.message.text
    announcement_entities = update.message.entities
    context.user_data['announcement'] = announcement
    context.user_data['announcement_entities'] = announcement_entities

    bot_message = update.message.reply_text(
            'You have sent me: \n\n',
            )
    update.message.reply_text(
            text=announcement,
            entities=announcement_entities
            )
    update.message.reply_text(
            text="Confirm message?",
            reply_markup=InlineKeyboardMarkup(buttons)
            )

    context.user_data['conv_state'] += 1
    return context.user_data['conv_state']


@send_typing_action
def edit_msg(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            'Please send me your message here again!'
            )

    context.user_data['conv_state'] -= 1
    return context.user_data['conv_state']


def write_message(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    event_id = int(query.data)
    e = AdminEventManager(event_id, record_exist=True)
    context.user_data['event_instance'] = e
    pretty_date = e.get_event_date().strftime('%d-%b, %a @ %-I:%M%p')

    query.edit_message_text(
            f"You have choosen <u>{e.event_type}</u> on <u>{pretty_date}</u>.\n\n"
            "Write your message to players who are <u>attending</u> and <u>active players who have not indicated</u> attendance here. "
            "If you have choosen an earlier date, you can send <b>training summaries</b> to players who attended too!",
            parse_mode="HTML"
            )
    context.user_data['conv_state'] = 2
    return context.user_data['conv_state']


@send_typing_action
def send_event_message(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_instance = AdminUser(user)
    query = update.callback_query
    query.answer()

    # getting relevant data
    event = context.user_data['event_instance']
    event.generate_entities()
    announcement = context.user_data['announcement']
    msg_entities = context.user_data['announcement_entities']

    footer = event.event_type + ' on ' + event.get_event_date().strftime('%d-%b, %a @ %-I:%M%p')
    footer = f"Message for {footer}"

    msg_entities.append(
            MessageEntity(
                type="italic",
                offset=len(announcement) + 2,
                length=len(footer)
                )
            )
    announcement = f"{announcement}\n\n{footer}\n\n- @{user_instance.username}"

    admin_msg = query.edit_message_text(
                "saving event announcement...\n"
                )

    event.set_announcement(announcement)
    event.set_entities(msg_entities)
    event.push_event_to_db()
    event.push_announcement_entities()

    admin_msg.edit_text(
        "getting players...\n"
        )
    send_list = event.compile_attendance_by_cat(
            attendance=1,
            gender='both',
            access_cat='all'
            )
    send_list += event.compile_attendance_by_cat(
            attendance=None,
            gender='both',
            access_cat="member"
            )

    # #adding team managers
    # send_list += db.execute('SELECT * FROM players JOIN access_control ON players.id = access_control.player_id WHERE access_control.control_id = 7').fetchall()

    admin_msg.edit_text(
            "getting players... done.\n"
            f"Sending event announcements... 0/{len(send_list)}"
            )
    send_message_generator = user_instance.send_message_by_list(
            send_list=send_list,
            msg=announcement,
            msg_entities=msg_entities,
            pin=True
            )

    failed_sends = list()
    for i in range(len(send_list)):
        admin_msg.edit_text(
                f"Sending event announcements... {i}/{len(send_list)}"
                )

        outcome = next(send_message_generator)
        if outcome != "success":
            failed_sends.append(outcome)

    failed_users = ', '.join(failed_sends)
    admin_msg.edit_text(
            f"Sending event announcements complete. list of uncompleted sends: \n\n{failed_users}"
            )

    logger.info("User %s sucessfully sent event messages", user.first_name)
    return ConversationHandler.END


@send_typing_action
def send_message(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user = update.effective_user
    user_instance = AdminUser(user)

    msg = context.user_data['announcement'] + f"\n\n\n\n- @{update.effective_user.username}"
    msg_entities = context.user_data['announcement_entities']

    # query data
    admin_msg_text = "getting active players..."
    admin_msg = query.edit_message_text(text=admin_msg_text)

    send_list = user_instance.get_users_list(
            only_active=True, only_members=True)

    send_message_generator = user_instance.send_message_by_list(
            send_list=send_list, msg=msg, msg_entities=msg_entities, pin=True)

    failed_list = list()
    for i in range(len(send_list)):
        admin_msg.edit_text(f"Sending announcements... {i}/{len(send_list)}")

        outcome = next(send_message_generator)
        if outcome != 'success':
            failed_list.append(outcome)

    failed_users = ", ".join(failed_list)
    admin_msg.edit_text(
            f"Sending announcements complete. list of uncompleted sends: \n\n {failed_users}")

    logger.info("User %s sucessfully sent announcements", user.first_name)
    return ConversationHandler.END


def send_reminders(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user = update.effective_user
    user_instance = AdminUser(user)

    query.edit_message_text(
            text="getting active_players..."
            )

    event_id = int(query.data)
    event_instance = AdminEventManager(event_id, record_exist=True)

    e_details = event_instance.event_date.strftime('%d-%b-%y, %A')
    e_details += f" ({event_instance.event_type})"
    msg = user_instance.read_msg_from_file(e_details)

    unindicated_players = event_instance.compile_attendance_by_cat(
            attendance=None,
            gender='both',
            access_cat='member'
            )

    send_message_generator = user_instance.send_message_by_list(
            unindicated_players, msg=msg, parse_mode='HTML'
            )

    failed_sends = list()
    for i in range(len(unindicated_players)):
        query.edit_message_text(f"sending reminders {i}/{len(unindicated_players)}")

        outcome = next(send_message_generator)
        if outcome != 'success':
            failed_sends.append(outcome)

    unsent_users = ', '.join(failed_sends)
    query.edit_message_text(
            text=f"Reminders have been sent sucessfully for {e_details}\n\nUnsucessful sends: \n{unsent_users}"
            )

    logger.info("reminders sent successfuly by User %s", update.effective_user.first_name)
    return ConversationHandler.END


@secure(access=5)
@send_typing_action
def choosing_date_administration(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_instance = AdminUser(user)

    logger.info("user %s has started /event_adminstration...", user.first_name)

    event_data = user_instance.get_event_dates()

    buttons = utils.date_buttons(event_data, pages=False)
    buttons.append(
                [
                    InlineKeyboardButton(text="Add Event", callback_data='add'),
                ]
            )

    reply_markup = InlineKeyboardMarkup(buttons)
    # if there are no queried trainings
    update.message.reply_text(
            text="Choose event:",
            reply_markup=reply_markup
            )
    return 1


@secure(access=5)
def initialise_event_date(update: Update, context: CallbackContext)-> int:

    query = update.callback_query
    query.answer()
    user = update.effective_user

    if query.data == "add":
        context.user_data['event_creation'] = True
        query.edit_message_text(
                text=f"""
Text me the starting datetime of the event in the format
dd-mm-yyyy@HHMM

<i>Tap the example to copy the format</i>

Eg. <code>{datetime.now().strftime('%d-%m-%Y@%H%M')}</code> """,
                parse_mode='html'
                )
        return 2

    else:
        context.user_data['event_creation'] = False
        event_id = int(query.data)

        event_instance = AdminEventManager(event_id, record_exist=True)
        context.user_data['event_instance'] = event_instance

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
def first_event_menu(update: Update, context: CallbackContext) -> int:

    is_new_event = context.user_data['event_creation']

    buttons = [
                [InlineKeyboardButton(text="Event datetime", callback_data='start')],
                [InlineKeyboardButton(text="Ending time", callback_data='end_time')],
                [InlineKeyboardButton(text="Event type", callback_data='type')],
                [InlineKeyboardButton(text='Description', callback_data='description')],
                [InlineKeyboardButton(text='Accountablility', callback_data='accountable')],
                [InlineKeyboardButton(text='Location', callback_data='location')],
                [InlineKeyboardButton(text='Access', callback_data='access')],
                ]

    if is_new_event:
        try:
            event_date = datetime.strptime(update.message.text, "%d-%m-%Y@%H%M")

        except ValueError:
            update.message.reply_text(
                    text="There seems to be something wrong with the format, text me the date again in this format dd-mm-yyyy@HHMM"
                    )
            return 2

        else:
            event_id = int(event_date.strftime("%Y%m%d%H%M"))
            event_instance = AdminEventManager(event_id, record_exist=False)
            event_instance.new_event_parse()

            context.user_data['event_instance'] = event_instance

            buttons.append(
                    [
                        # InlineKeyboardButton(text='Announce', callback_data='announce'),
                        InlineKeyboardButton(
                            text="Confirm Changes", callback_data="forward"
                            )
                        ]
                    )
            bot_message = update.message.reply_text(text="initialising event...")
    else:
        query = update.callback_query
        query.answer()
        event_instance = context.user_data['event_instance']
        bot_message = query.edit_message_text("initialising event...")

        if query.data == 'edit':
            buttons.append([InlineKeyboardButton(
                text="Confirm Changes", callback_data="forward")]
                           )
        elif query.data == 'remove':
            buttons = [
                    [InlineKeyboardButton(
                        text="Confirm Deletion?", callback_data="delete")
                     ],
                    ]

    reply_markup = InlineKeyboardMarkup(buttons)
    bot_message.edit_text(
            text=f"""
event date : {event_instance.event_date.strftime('%d-%m-%y, %a')}
start : {event_instance.pretty_start()}
end : {event_instance.pretty_end()}
type of event : {event_instance.event_type}
location : {event_instance.location}
access : {event_instance.access_control}
accountable event : {'Yes' if event_instance.accountable else 'No'}
description:
{event_instance.description}
                    """,
            reply_markup=reply_markup
            )
    return 3


@secure(access=5)
@send_typing_action
def event_menu(update: Update, context: CallbackContext) -> int:
    is_query = context.user_data['is_query']
    prev_form = context.user_data['form']  # data is 'query' or 'datetime' or 'time'
    event_instance = context.user_data['event_instance']

    text = ''
    buttons = [
                [InlineKeyboardButton(text="Event datetime", callback_data='start')],
                [InlineKeyboardButton(text="Ending time", callback_data='end_time')],
                [InlineKeyboardButton(text="Event type", callback_data='type')],
                [InlineKeyboardButton(text='Location', callback_data='location')],
                [InlineKeyboardButton(text='Description', callback_data='description')],
                [InlineKeyboardButton(text='Accountablility', callback_data='accountable')],
                [InlineKeyboardButton(text='Access', callback_data='access')],
                [
                    #InlineKeyboardButton(text="Announce", callback_data='announce'), 
                    InlineKeyboardButton(text='Confirm Changes', callback_data='forward')
                    ]
                ]

    if is_query:
        query = update.callback_query
        query.answer()
        bot_message = query.edit_message_text('parsing new changes...')
        data = query.data
    else:
        bot_message = update.message.reply_text('parsing new changes...')
        data = update.message.text

    if prev_form == "rejected":
        bot_message.edit_text('returning to event menu...')

    elif prev_form == 'event_type':
        event_instance.set_event_type(data)

    elif prev_form == 'access':
        event_instance.set_access(int(data))

    elif prev_form == 'accountable':
        event_instance.set_accountable(int(data))

    elif prev_form == 'description':
        event_instance.set_description(data)

    elif prev_form == "datetime":
        try:
            event_date = datetime.strptime(update.message.text, "%d-%m-%Y@%H%M")

        except ValueError:
            text = "<b>Format seems to be wrong. Please try again.</b>\n\n "
        else:
            event_instance.set_event_date(event_date)
            event_instance.set_id(event_date=event_date)

    elif prev_form == "time":
        try:
            event_time = datetime.strptime(update.message.text, "%H%M")
        except ValueError:
            text = "<b>Format seems to be wrong. Please try again.</b>\n\n "
        else:
            event_time = event_instance.replace_end_time(event_time)
            event_instance.set_event_end(event_time)

    elif prev_form == 'location':
        event_instance.set_location(update.message.text)

    context.user_data['event_instance'] = event_instance

    text += f"""
event date : {event_instance.event_date.strftime('%d-%m-%y, %a')}
start : {event_instance.pretty_start()}
end : {event_instance.pretty_end()}
type of event : {event_instance.event_type}
location : {event_instance.location}
access : {event_instance.access_control}
accountable event : {'Yes' if event_instance.accountable else 'No'}
description:
{event_instance.description}
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


def change_datetime(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = False
    context.user_data['form'] = 'datetime'
    event_instance = context.user_data['event_instance']
    pretty_date = event_instance.event_date.strftime("%d-%m-%Y@%H%M")

    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text=f"""
Text me the starting datetime of the event in the format dd-mm-yyyy@HHMM

Note:
It is <u><b>not recommended</b></u> to change the starting date and time of an event. Only do so after a consensus on a schedule changed has been reached.

<i>Otherwise, affected players attending the event will not know of the schedule change but their attendance will still reflect as per previous schedule</i>
\n\nEg. original datetime: <code>{pretty_date}</code>""",
            parse_mode='html'
                    )

    return "event_menu"


def change_time(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = False
    context.user_data['form'] = 'time'
    query = update.callback_query
    event_instance = context.user_data['event_instance']
    query.answer()

    cur_time = event_instance.end_time.strftime('%H%M')
    query.edit_message_text(f"""
Text me the ending time of the event in the format HHMM

End time currently set to: <code>{cur_time}</code>""",
                            parse_mode='html'
                            )
    return "event_menu"


def formatting_error(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
            "Format seems to be wrong please try again "
            )
    return 'event_menu'


def edit_type(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = True
    context.user_data['form'] = 'event_type'
    query = update.callback_query
    query.answer()

    buttons = [
           [InlineKeyboardButton(text='Field Training', callback_data='Field Training')],
           [InlineKeyboardButton(text='Scrim', callback_data='Scrim')],
           [InlineKeyboardButton(text='Hardcourt/Track', callback_data='Hardcourt/Track')],
           [InlineKeyboardButton(text='Gym/Pod', callback_data='Gym/Pod')],
           [InlineKeyboardButton(text='Cohesion', callback_data='Cohesion')],
           [InlineKeyboardButton(text='Custom', callback_data='Custom')]
            ]
    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text(
            text="""
Select the type of event: (You may use Scrim to indicate tournament availability as well)

            """,
            reply_markup=reply_markup
            )
    return 3.1


def handle_edit_type(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = False
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            "Write custom tag"
            )
    return "event_menu"


def edit_location(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = False
    context.user_data['form'] = 'location'
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text="""
Text the location of the event.
Generic location titles or google map links are accepted
            """
            )

    return "event_menu"


def edit_access(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = True
    context.user_data['form'] = 'access'
    query = update.callback_query
    query.answer()
    buttons = [
           [InlineKeyboardButton(text='Guest (2)', callback_data='2')],
           [InlineKeyboardButton(text='Club Members (4)', callback_data='4')],
           [InlineKeyboardButton(text='Core (5)', callback_data='5')],
            ]
    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text(
            text="""
Choose the access level for the event, members of higher
access control can participate in events of lower access control

for eg. Club members can participate in events with 'Guest' level access""",
            reply_markup=reply_markup
            )

    return "event_menu"

def edit_description(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = False
    context.user_data['form'] = 'description'
    event_instance = context.user_data['event_instance']
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text=f"""
Write a description for the event
current description:
<code>{event_instance.description}</code>
            """,
            parse_mode='html'
            )
    return "event_menu"


def edit_accountable(update: Update, context: CallbackContext) -> str:
    context.user_data['is_query'] = True
    context.user_data['form'] = 'accountable'
    event_instance = context.user_data['event_instance']
    query = update.callback_query
    query.answer()
    buttons = [
            [InlineKeyboardButton(text='Yes', callback_data='1')],
            [InlineKeyboardButton(text="No", callback_data='0')]
            ]

    query.edit_message_text(
            text=f"""
Accountability for an event.
'Yes' -> users will be prompted for a reason if indicating 'No' for this event
'No' ->  users will not be prompted for reason if indicating 'No'

current selection : {'Yes' if event_instance.accountable else 'No'}
            """,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='html'
            )
    return "event_menu"


def delete_event(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    event_instance = context.user_data['event_instance']

    event_instance.remove_event_from_record()

    query.edit_message_text("event has been delete sucessfully.")
    logger.info(
            "user %s has deleted event on %s", user.first_name,
            event_instance.event_date.strftime("%d-%m-%y")
            )
    return ConversationHandler.END


def commit_event_changes(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    user = update.effective_user
    event_instance = context.user_data['event_instance']

    if event_instance.check_conflicts():
        buttons = [[InlineKeyboardButton(text='Return to menu', callback_data='^back$')]]
        context.user_data['form'] = 'rejected'
        query.edit_message_text(
                text="There already exists an event at this time and date. please edit starting datetime",
                reply_markup=InlineKeyboardMarkup(buttons)
                )
        return "event_menu"
    event_instance.push_event_to_db()

    query.edit_message_text(
            text="event sucessfully added/updated! Announce new event or changes by /announce_event!"
            )
    logger.info("user %s has successfully updated an event", user.first_name)
    return ConversationHandler.END


@secure(access=6)
@send_typing_action
def choose_access_level(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_instance = AdminUser(user)

    logger.info("user %s is started /access_control_administration", user.first_name)
    access_data = user_instance.get_access_levels()

    buttons = list()
    for row in access_data:
        button = InlineKeyboardButton(text=row['description'], callback_data=str(row['id']))
        buttons.append([button])

    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text(
            text='''
<u>Guests:</u>
Access to updating attendance
Will <b>only</b> receive event announcements to events they have indicated that they are attending

No access to /kaypoh, and club announcements from /announce_all


<u>Members: </u>
Acess to all functions in the training bot
No access to admin bot


<u>Core:</u>
Access to all functions in training bot
Acesss to /event_administration in admin bot

No access to /access_control_administration

<i>Similar to the function of Excos in an organisation</i>


<u>Admin:</u>
Full level of access


<u>Team Manager:</u>
Full level of access, same as admin.
But will not accounted for in attendance


Pick position:
            ''',
            reply_markup=reply_markup,
            parse_mode='html'
            )
    
    return 1

@secure(access=6)
def choose_access_level_again(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()

    user_instance = AdminUser(user)
    access_data = user_instance.get_access_levels()
    
    buttons = list()
    for row in access_data:
        button = InlineKeyboardButton(text=row['description'], callback_data=str(row['id']))
        buttons.append([button])

    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text(
            text='''
<u>Guests:</u>
Access to updating attendance
Will <b>only</b> receive event announcements to events they have indicated that they are attending

No access to /kaypoh, and club announcements from /announce_all


<u>Members: </u>
Acess to all functions in the training bot
No access to admin bot


<u>Core:</u>
Access to all functions in training bot
Acesss to /event_administration in admin bot

No access to /access_control_administration

<i>Similar to the function of Excos in an organisation</i>


<u>Admin:</u>
Full level of access


<u>Team Manager:</u>
Full level of access, same as admin.
But will not accounted for in attendance


Pick position:
            ''',
            reply_markup=reply_markup,
            parse_mode='html'
            )
    
    return 1


@secure(access=6)
def choose_players(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()

    user_instance = AdminUser(user)

    try:
        selected_access = int(query.data)
    except ValueError:
        selected_access = context.user_data['selected_access']
    context.user_data['selected_access'] = selected_access

    player_data = user_instance.select_players_on_access(selected_access)

    buttons = list()
    for row in player_data:
        button = InlineKeyboardButton(text=row['name'], callback_data=str(row['id']))
        buttons.append([button])
    buttons.append([InlineKeyboardButton(text="Back", callback_data='back')])
    reply_markup = InlineKeyboardMarkup(buttons)

    query.edit_message_text(
            text=
            '''
<u>Guests:</u>
Access to updating attendance
Will <b>only</b> receive event announcements to events they have indicated that they are attending

No access to /kaypoh, and club announcements from /announce_all


<u>Members: </u>
Acess to all functions in the training bot
No access to admin bot


<u>Core:</u>
Access to all functions in training bot
Acesss to /event_administration in admin bot

No access to /access_control_administration

<i>Similar to the function of Excos in an organisation</i>


<u>Admin:</u>
Full level of access


<u>Team Manager:</u>
Full level of access, same as admin.
But will not accounted for in attendance


Pick position:
            ''',
            reply_markup=reply_markup,
            parse_mode='html'
            )

    return 2

@secure(access=6)
def change_player_access(update:Update, context:CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()
    user_instance = AdminUser(user)


    try:
        selected_player_id = int(query.data)
    except ValueError:
        selected_player_id = context.user_data['selected_player_id']

    selected_player = user_instance.generate_player_access_record(
            selected_player_id
            )

    context.user_data['selected_player_id'] = selected_player_id
    context.user_data['selected_player'] = selected_player
    selected_access = context.user_data['selected_access']
    buttons = [
            [InlineKeyboardButton(text="Guest", callback_data='2')],
            [InlineKeyboardButton(text="Member", callback_data='4')],
            [InlineKeyboardButton(text="Core", callback_data='5')],
            [InlineKeyboardButton(text='Admin', callback_data='6')],
            [InlineKeyboardButton(text='Team Manager', callback_data='7')],
            [InlineKeyboardButton(text="Kick", callback_data="0")],
            ]
    reply_markup = InlineKeyboardMarkup(buttons)

    text = f"""
player : {selected_player.name}
handle : @{selected_player.telegram_user}
gender : {selected_player.gender}
position : {selected_player.position}

What is the new position for this player?

    """
    query.edit_message_text(
            text=text,
            reply_markup=reply_markup
            )

    return 3


@secure(access=6)
def review_access_change(update: Updater, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    selected_player = context.user_data['selected_player']

    new_selected_access = int(query.data)
    selected_player.set_new_access(new_selected_access)

    context.user_data['selected_player'] = selected_player

    buttons = [
            [InlineKeyboardButton(text='Confirm position', callback_data='^forward$')],
            ]
    reply_markup = InlineKeyboardMarkup(buttons)
    text = f"""
player : {selected_player.name}
handle : @{selected_player.telegram_user}
gender : {selected_player.gender}
position : {selected_player.position}
new position : {selected_player.new_position}

Confirm new position for {selected_player.name}?
    """
    query.edit_message_text(
            text=text,
            reply_markup=reply_markup
            )
    return 4


@secure(access=6)
def commit_access_change(update: Updater, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()

    user_instance = AdminUser(user)
    selected_player = context.user_data['selected_player']

    user_instance.push_player_access(selected_player)

    query.edit_message_text(text=f"{selected_player.name} is now {selected_player.new_position}")
    logger.info("user %s sucessfully changed the access control of %s from %s to %s",
                user.first_name, selected_player.name, selected_player.position, selected_player.new_position)
    return ConversationHandler.END


@send_typing_action
def cancel(update: Update, context: CallbackContext) -> int:
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

    # upgrade if there is
    version = src.Upgrade.upgrade_manager.UpgradeManager(
            config=CONFIG, cur_ver=2.11
            )
    updated = version.update_system()
    if updated:
        logger.info("system has been updated. to %.2f", version.cur_ver)
    else:
        logger.info("no updates found. continuing...")



    # setting command list
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
                1: [
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
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$'),
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
            1: [
                CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$' ),
                CallbackQueryHandler(send_reminders, pattern='^(\d{10}|\d{12})$')
                ],
            },
        fallbacks=[CommandHandler('cancel', cancel)],
        )

    conv_handler_event_administration = ConversationHandler(
            entry_points=[CommandHandler('event_administration', choosing_date_administration)],
            states={
                1: [
                    CallbackQueryHandler(initialise_event_date, pattern="^(\d{10}|\d{12})$"),
                    CallbackQueryHandler(initialise_event_date, pattern="add"),
                    ],
                2: [
                    CallbackQueryHandler(first_event_menu, pattern="^edit$"),
                    CallbackQueryHandler(delete_event, pattern="^remove$"),
                    MessageHandler(Filters.text & ~Filters.command ,first_event_menu)
                    ],
                3: [
                    CallbackQueryHandler(change_datetime, pattern="^start$"),
                    CallbackQueryHandler(change_time, pattern='^end_time$'),
                    CallbackQueryHandler(edit_type, pattern='^type$'),
                    CallbackQueryHandler(edit_location, pattern='^location$'),
                    CallbackQueryHandler(edit_access, pattern='^access$'),
                    CallbackQueryHandler(edit_description, pattern='^description$'),
                    CallbackQueryHandler(edit_accountable, pattern='^accountable$'),
                    CallbackQueryHandler(commit_event_changes, pattern='^forward$'),
                    ],
                3.1: [
                    CallbackQueryHandler(handle_edit_type, pattern='^Custom$'),
                    CallbackQueryHandler(
                        event_menu,
                        pattern="^(Field Training|Scrim|Hardcourt/Track|Gym/Pod|Cohesion)$"
                                         ),
                    ],
                'event_menu': [
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
