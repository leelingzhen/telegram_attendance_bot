import logging
import os
import helpers
import json
import sqlite3

from datetime import datetime
from functools import wraps
from src.user_manager import UserManager
from src.event_manager import TrainingEventManager, AttendanceManager
from src.message_manager import KaypohMessage, KaypohMessageHandler

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
            if user_instance.access < access:
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
    user_instance = UserManager(user)

    player_profile = user_instance.retrieve_user_data()

    if player_profile is None:
        return None

    player_access = user_instance.get_user_access()
    if player_access == 0:
        update.message.reply_text("Hello new player! please register yourself by using /register")
        return None

    elif player_access > 0:
        # language_pack = player_profile[3]
        update.message.reply_text("Hello please use the commands to talk to me!")
    logger.info('user %s has talked to the bot', user.first_name)

    return None


@secure(access=2)
@send_typing_action
def choosing_date_low_access(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_instance = UserManager(user)
    helpers.refresh_player_profiles(update, context)

    logger.info("user %s is choosing date...", user.first_name)

    event_data = user_instance.get_event_dates()

    context.user_data["event_data"] = event_data
    context.user_data["page"] = 0
    context.user_data["user_instance"] = user_instance

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
def choosing_date_high_access(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_instance = UserManager(user)
    helpers.refresh_player_profiles(update, context)

    logger.info("user %s is choosing date...", user.first_name)
    event_data = user_instance.get_event_dates()

    context.user_data["event_data"] = event_data
    context.user_data["page"] = 0
    context.user_data['user_instance'] = user_instance

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
    reply_markup = InlineKeyboardMarkup(
            helpers.date_buttons(
                context.user_data["event_data"],
                page_num=context.user_data["page"])
            )
    query.edit_message_reply_markup(
            reply_markup=reply_markup
            )
    return 1


def attendance_list(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info('user %s is a kaypoh', user.first_name)
    query = update.callback_query
    query.answer()
    user = update.effective_user
    query.edit_message_text(
            text="Kaypohing..."
            )

    # retrieve selected event
    event_id = int(query.data)

    message_instance = KaypohMessage(event_id)
    message_instance.fill_text_fields(datetime.now())

    bot_message = query.edit_message_text(
            text=message_instance.text, parse_mode='html'
            )

    message_instance.store_message_fields(bot_message)
    message_instance.push_record()

    return ConversationHandler.END


def indicate_attendance(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # retrieve date query and store
    selected_event = int(query.data)
    event_instance = TrainingEventManager(selected_event)
    user_instance = context.user_data['user_instance']

    # retrieve data
    attendance = AttendanceManager(user_instance.id, event_instance.id)
    event_date = event_instance.get_event_date()

    # store attendance into context
    context.user_data["event_instance"] = event_instance
    context.user_data['attendance'] = attendance
    context.user_data['prev_status'] = attendance.get_status()
    context.user_data["gave_reason"] = False

    button = [
            [InlineKeyboardButton(f"Yes I ❤️{CONFIG['team_name']} ", callback_data="2")],
            [InlineKeyboardButton("Yes but...", callback_data="1")],
            [InlineKeyboardButton("No (lame)", callback_data="0")],
            ]
    reply_markup = InlineKeyboardMarkup(button)

    query.edit_message_text(
            text=f"""
Your attendance is indicated as \'{attendance.pretty_attendance()}\'

<u>Details</u>
Date: {event_date.strftime('%-d %b, %a')}
Event: {event_instance.event_type}
Time: {event_instance.pretty_start()} - {event_instance.pretty_end()}
Location : {event_instance.location}

Would you like to go for {event_instance.event_type}?
            """,
            reply_markup=reply_markup,
            parse_mode='html'
            )
    return 2


def give_reason(update: Update, context: CallbackContext) -> str:
    query = update.callback_query
    query.answer()
    status = int(query.data)

    attendance = context.user_data["attendance"]
    attendance.set_status(status)

    context.user_data['attendance'] = attendance
    context.user_data["gave_reason"] = True

    query.edit_message_text(
            text="Please write a comment/reason 😏"
            )
    return 2


def update_attendance(update: Update, context: CallbackContext) -> str:

    # retrieve indication of attendance
    attendance = context.user_data['attendance']
    gave_reason = context.user_data['gave_reason']
    user_instance = context.user_data['user_instance']
    event_instance = context.user_data['event_instance']
    prev_status = context.user_data['prev_status']

    text = "updating your attendance..."
    if not gave_reason:
        # indicated attendance is yes skipped give_reason
        query = update.callback_query
        query.answer()
        attendance.set_status(1)
        attendance.set_reason("")
        bot_message = query.edit_message_text(
                text=text
                )
    else:
        # retrieve reasons, went through give_reason
        reason = update.message.text
        reason = helpers.escape_html_tags(reason)
        attendance.set_reason(reason)
        bot_message = update.message.reply_text(
                text=text
                )

    bot_comment = "Hope to see you soon🥲🥲"
    if attendance.is_attending():
        bot_comment = f"See you at {event_instance.event_type}! 🦾🦾"
    attendance.update_records()
    context.job_queue.run_once(update_kaypoh_messages, 0, context=event_instance)
    event_date = event_instance.get_event_date().strftime('%-d %b, %a')

    text = f"""
You have sucessfully updated your attendance! 🤖🤖\n
<u>Details</u>
Date: {event_date}
Event: {event_instance.event_type}
Time: {event_instance.pretty_start()} - {event_instance.pretty_end()}
Location : {event_instance.location}
Attendance: {'Yes' if attendance.status else 'No'}
"""
    if attendance.reason:
        text += f"Comments: {attendance.reason}\n\n"

    bot_message.edit_text(text=text + bot_comment, parse_mode='html')

    if helpers.resend_announcement(prev_status,
                                   event_instance.announcement,
                                   user_instance.access):

        event_instance.generate_entities()
        message_obj = context.bot.send_message(
                chat_id=user_instance.id,
                text=event_instance.announcement,
                entities=event_instance.announcement_entities,
                )
        context.bot.pin_chat_message(
                chat_id=user_instance.id,
                message_id=message_obj.message_id,
                disable_notification=True
                )

    logger.info("User %s has filled up his/her attendance...", update.effective_user.first_name)
    return ConversationHandler.END


def update_kaypoh_messages(context: CallbackContext):
    logger.info("intitiatin job queue to update kaypoh messages....")
    event_instance = context.job.context
    message_handler = KaypohMessageHandler(event_instance.id)
    message_handler.update_all_message_instances()
    n_records = message_handler.n_records()
    logger.info("completed job queue updating messages for %d records", n_records)


@secure(access=4)
@send_typing_action
def choosing_more_dates(update:Update, context: CallbackContext)-> int:
    user = update.effective_user
    helpers.refresh_player_profiles(update, context)

    user_instance = UserManager(user)

    logger.info("user %s used /attendance_plus...", user.first_name)

    event_data = user_instance.get_event_dates()

    context.user_data["event_data"] = event_data
    context.user_data["chosen_events"] = list()
    context.user_data['user_instance'] = user_instance

    # if there are no queried trainings
    if event_data == list():
        update.message.reply_text("There are no more further planned events. Enjoy your break!🏝🏝")
        return ConversationHandler.END

    buttons = helpers.date_buttons(event_data, pages=False)
    reply_markup = InlineKeyboardMarkup(buttons)

    update.message.reply_text(
            text="""
Select dates for events you want to update. Select them again to remove them from selection.

Selected Dates:

            """,
            reply_markup=reply_markup
            )
    return 1


def choosing_more_dates_cont(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # get query
    event_id = int(query.data)

    # retrieve choosent events
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

    # make buttons
    buttons = helpers.date_buttons(event_data, pages=False)
    buttons.append([InlineKeyboardButton(text='Confirm', callback_data='forward')])
    reply_markup = InlineKeyboardMarkup(buttons)

    query.edit_message_text(
            text=f"""
Select dates for events you want to update. Select them again to remove them from selection.

Selected Dates:
{text}

            """,
            reply_markup=reply_markup
            )

    return 1


def indicate_more(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # initialise status
    context.user_data["gave_reason"] = False
    context.user_data['status'] = None

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


def give_reason_more(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # save the query
    context.user_data["status"] = int(query.data)
    context.user_data["gave_reason"] = True

    query.edit_message_text(
            text="Please write a comment/reason 😏. The comment will be applied to all selected events."
            )
    return 2


def commit_attendance_plus(update: Update, context: CallbackContext) -> int:
    # retrieve indication of attendance
    user = update.effective_user
    status = context.user_data["status"]
    gave_reason = context.user_data["gave_reason"]
    user_instance = context.user_data["user_instance"]

    text = "updating your attendance..."

    if gave_reason:
        # indicated attendance is yes skipped give_reason_more
        reason = update.message.text
        reason = helpers.escape_html_tags(reason)
        bot_message = update.message.reply_text(
                text=text
                )
    else:
        query = update.callback_query
        query.answer()
        status = 1
        reason = ""
        bot_message = query.edit_message_text(
                text=text
                )

    # retrieve selected events
    chosen_events = context.user_data['chosen_events']

    date_strs = list()

    for event_id in chosen_events:
        event = TrainingEventManager(event_id)
        attendance = AttendanceManager(user_instance.id, event.id)
        attendance.set_status(status)
        attendance.set_reason(reason)
        attendance.update_records()
        event_date = event.get_event_date()
        pretty_str = event_date.strftime('%-d %b, %a @ %-I:%M%p')
        pretty_str = f"{pretty_str} ({event.event_type})"

        date_strs.append(pretty_str)

    sep = '\n'
    text = f"""
You have sucessfully updated your attendance for {len(chosen_events)} records!

{sep.join(date_strs)}

Attendance : {"Yes" if status == 1 else "No"}
{'Comment/reason: ' + reason if reason != '' else ''}
"""

    bot_message.edit_text(text=text)
    logger.info("user %s has sucessfully updated attendance for %d records", user.first_name, len(chosen_events))

    return ConversationHandler.END


@secure(access=2)
@send_typing_action
def events(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    user_instance = UserManager(user)

    logger.info("User %s has started a query for his/her event schedule", user.first_name)

    dict_date = user_instance.attending_events()
    text = ""
    for key in dict_date:
        # no registered dates of this category
        if dict_date[key] == list():
            continue
        else:
            text += f"<u>{key}</u>\n"
            for event_date in dict_date[key]:
                text += event_date.strftime('%d %b, %a @ %-I:%M%p') + "\n"
            text += '\n'

    update.message.reply_text(
            f"You'll 👀 {CONFIG['team_name']} on:\n\n{text}\nSee you then!🦿🦿",
            parse_mode='html'
            )
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

        # text formatting
        training_date = event_date.strftime("%-d %b, %a")
        start_time= event_date.strftime("%-I:%M%p")
        end_time = datetime.strptime(event_data["end_time"], "%H:%M").strftime("%-I:%M%p")

        # calendar formatting
        # calendar_start= event_date.strftime("%Y-%m-%d %H:M%S")
        # calendar_end = event_date.strftime("%Y-%m-%d") + event_data["end_time"] + ":00"
        # calendar = Calendar()
        # calendar_event = Event(
        #        name=f"Alliance {event_data['event_type']}",
        #        begin=event_date.strftime("%Y-%m-%d %H:%M:%S"),
        #        end=event_date.strftime("%Y-%m-%d") + " " + event_data["end_time"] + ":00",
        #        location = event_data['location']
        #        )
        # calendar.events.add(calendar_event)
    text = f"""
<u>Details</u>
Date: {event_date.strftime('%-d %b, %a')}
Event: {event_data['event_type']}
Time: {start_time} - {end_time}
Location : {event_data['location']}
"""
    query.edit_message_text(
            text=f"{text}",
            parse_mode='html'
            )

    # with open(f"{event_date.strftime('%-d %b, %a')}.ics", 'w') as f:
    #    f.writelines(calendar.serialize_iter())
    # with open(f"{event_date.strftime('%-d %b, %a')}.ics", 'rb') as f:
    #    context.bot.send_document(user.id, f)
    # os.remove(f"{event_date.strftime('%-d %b, %a')}.ics")

    logger.info("user %s has generated an ics file for %s", user.first_name, event_date.strftime("%d-%m-%y"))

    return ConversationHandler.END


@secure(access=4)
@send_typing_action
def settings_start(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info("User %s is accessing settings...", user.first_name)

    user_instance = UserManager(user)
    user_instance.retrieve_user_data()

    if not user_instance.username_tally():
        user_instance.set_username()

    # save into context
    # context.user_data["user_id"] = user.id
    # context.user_data["name"] = name
    # context.user_data["notification"] = notification
    # context.user_data["language"] = language
    context.user_data['user_instance'] = user_instance

    buttons = [
            [InlineKeyboardButton(text="Name", callback_data="name")],
            [InlineKeyboardButton(text="Notification settings", callback_data="notification")],
            # [InlineKeyboardButton(text="Language settings", callback_data="language")]
            ]
    reply_markup = InlineKeyboardMarkup(buttons)

    update.message.reply_text(
            text=f"""
Current settings
Name: {user_instance.name}
Notifications: {'Yes' if user_instance.notification == 1 else 'No'}
""",
            reply_markup=reply_markup
            )
    return 1


def name_change(update: Update, context: CallbackContext) -> float:
    query = update.callback_query
    query.answer()

    user_instance = context.user_data['user_instance']

    query.edit_message_text(
            text=(
                f"""
Your name is currently set as <u>{user_instance.name}</u>
<b>Please use your full name</b>
text me your name if you wish to change it\n\n
otherwise /cancel to cancel the process
                """
                ),
            parse_mode="html"
            )
    return 1.1


def notification_change(update: Update, context: CallbackContext) -> float:
    query = update.callback_query
    query.answer()
    user_instance = context.user_data['user_instance']

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

current selection - {'Yes'if user_instance.notification == 1 else 'No'}

Choose notification setting
                """),
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(buttons)
            )
    return 1.2


def language_change(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    query.edit_message_text(
            text=f"This feature is still under development, please come back another time!"
            )
    logger.info("User %s tried to change language", context.user_data["name"])
    return ConversationHandler.END


def commit_notification_change(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_instance = context.user_data['user_instance']

    notification = int(query.data)
    user_instance.set_notification(notification)
    user_instance.push_update_user()

    query.edit_message_text(
            text=
            f"""
You have sucessfully turned {'off' if notification == 0 else 'on'} notifications

<i>You are now an {'inactive player' if notification == 0 else 'active player'}</i>
            """,
            parse_mode='html'
            )
    logger.info("User %s has sucessfully changed notification settings and is now an %s player.", user_instance.name, "active" if notification == 1 else "inactive")
    return ConversationHandler.END


@send_typing_action
def confirmation_name_change(update: Update, context: CallbackContext) -> float:
    buttons = [
        [InlineKeyboardButton(text="Confirm", callback_data="forward")],
        [InlineKeyboardButton(text="Edit Name", callback_data="back")]
        ]
    new_name = update.message.text.rstrip().lstrip()

    user_instance = context.user_data['user_instance']

    exisiting_user = user_instance.get_exisiting_name(new_name)

    if exisiting_user is not None:
        bot_message = update.message.reply_text(
                text=f"{new_name} has already been taken by @{exisiting_user}.\n please enter a new name!"
                )
        return 1.1

    user_instance.set_name(new_name)

    bot_message = update.message.reply_text(
            f"Your name will be:\n"
            f"<u>{user_instance.name}</u>\n\n"
            "confirm?",
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(buttons)
            )
    return 2.1


def commit_name_change(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    query = update.callback_query
    query.answer()

    user_instance = context.user_data['user_instance']
    user_instance.push_update_user()

    query.edit_message_text(
            text=f"Name sucessfully changed to <u>{user_instance.name}</u>",
            parse_mode="html"
            )

    logging.info("User %s has changed name to %s", user.username, user_instance.name)

    return ConversationHandler.END


@send_typing_action
def select_gender(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_instance = UserManager(user)

    if user_instance.access >= 2:
        update.message.reply_text("You are already registered.")
        return ConversationHandler.END
    if user_instance.access == 1:
        update.message.reply_text("Your registration is pending approval.")
        return ConversationHandler.END

    context.user_data['user_instance'] = user_instance

    logger.info("user %s is registering", user.first_name)
    with open(os.path.join('resources', 'messages', 'registration_introduction.txt')) as f:
        text = f.read()
    buttons = [
            [InlineKeyboardButton(text='Male 👦🏻', callback_data='Male')],
            [InlineKeyboardButton(text='Female 👩🏻', callback_data='Female')]
            ]
    update.message.reply_text(
            text=text,
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(buttons)
            )
    context.user_data['conv_state'] = 0
    return 1


def fill_name(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user_instance = context.user_data['user_instance']
    gender = query.data

    user_instance.set_gender(gender)
    bot_message = query.edit_message_text("setting gender...")

    bot_message.edit_text(
            text="Send me your name with your surname!"
            )
    context.user_data['context_state'] = 1
    return 2


def confirm_name_registration(update: Update, context: CallbackContext) -> int:
    name = update.message.text.rstrip().lstrip()
    user_instance = context.user_data['user_instance']
    bot_msg = update.message.reply_text("checking name conflicts..")

    existing_user = user_instance.get_exisiting_name(name)
    if existing_user:
        bot_msg.edit_text(
                f"{name} is currently taken by {existing_user}, please enter another name"
                )
        return 2

    user_instance.set_name(name)
    context.user_data['user_instance'] = user_instance

    buttons = [
            [InlineKeyboardButton(text="Confirm", callback_data="forward")],
            [InlineKeyboardButton(text="Edit name", callback_data="back")]
            ]
    bot_msg.edit_text(
            text=f"You have sent me: <u>{name}</u>\nConfirm?",
            parse_mode='html',
            reply_markup=InlineKeyboardMarkup(buttons)
            )
    return 3


def commit_registration(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    user = update.effective_user
    user_instance = context.user_data['user_instance']
    
    bot_message = query.edit_message_text(
            text=f"registering... {user_instance.name}  "
            )
    user_instance.push_new_user()
    text = f"""
You have sucessfully been registered! Please inform the core/exco team to approve your registration😊😊.

Full name : {user_instance.name}
telegram handle : @{user.username}
Gender : {user_instance.gender}


    """
    bot_message.edit_text(
            text=text,
            parse_mode='html'
            )
    logger.info('User %s has sucessfully registered', user.first_name)
    return ConversationHandler.END

#
# @send_typing_action
# @secure(access=2)
# def review_membership(update: Update, context: CallbackContext) -> int:
#     user = update.effective_user
#     logger.info("user %s just initiated /apply_membership", user.first_name)
#
#     with sqlite3.connect(CONFIG['database']) as db:
#         db.row_factory = sqlite3.Row
#         access_control = db.execute('''
#                 SELECT control_id, access_control_description.description FROM access_control 
#                 JOIN access_control_description ON access_control.control_id = access_control_description.id
#                 WHERE player_id = ?
#                 ''',
#                 (user.id, )
#                 ).fetchone()
#         if access_control['control_id'] >= 4:
#             proposition = 'an' if access_control['description'] == 'Admin' else 'a'
#             update.message.reply_text(
#                     f'bruh you are already {proposition} {access_control["description"]} what are you even doing here..'
#                     )
#             logger.info("user %s was just fking around..", user.first_name)
#             return ConversationHandler.END
#
#
#     with open(os.path.join("resources", 'messages', 'membership_registration_terms.txt')) as f:
#         text = f.read()
#     buttons = [
#             [InlineKeyboardButton(text=f"I wanna be part of {CONFIG['team_name']}😊", callback_data="forward")],
#             [InlineKeyboardButton(text="Maybe another time.", callback_data="cancel")]
#             ]
#     reply_markup = InlineKeyboardMarkup(buttons)
#     update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode='html')
#     return 1
#
#
# def commit_membership_position(update: Update, context: CallbackContext) -> int:
#     user = update.effective_user
#     query = update.callback_query
#     query.answer()
#
#     if query.data == "forward":
#         with sqlite3.connect(CONFIG['database']) as db:
#             db.execute('BEGIN TRANSACTION')
#             db.execute('UPDATE access_control SET control_id = 3 WHERE player_id = ?', (user.id, ))
#             db.commit()
#         text = f"""
# Thank you for your interest in being a member of {CONFIG['team_name']}😇😇!!
# Your commitment has been noted and is under the review of the core team 🥹
#         """
#         query.edit_message_text(text=text)
#         logger.info("user %s is now pending membership approval", user.first_name)
#         return ConversationHandler.END
#     else:
#         query.edit_message_text("We hope to see you soon!!")
#         logger.info("user %s fking alibaba one", user.first_name)
#         return ConversationHandler.END
#

@send_typing_action
def cancel(update: Update, context: CallbackContext) -> int:
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
        token = bot_tokens["training_bot"]

    commands = [
            BotCommand("start", "to start the bot"),
            BotCommand("attendance", "update attendance"),
            BotCommand("kaypoh", "your friend never go u dw go is it??"),
            BotCommand("attendance_plus", "one shot update attendance"),
            BotCommand("events", "events that you are attending"),
            BotCommand("event_details", "Get event details"),
            BotCommand("settings", "access settings and refresh username if recently changed"),
            BotCommand("register", "use this command if you're a new player"),
            # BotCommand("apply_membership", f"use this command if you'll like to be part of {CONFIG['team_name']}!"),
            BotCommand("cancel", "cancel any process"),
            ]

    Bot(token).set_my_commands(commands)

    updater = Updater(token)

    # dispatcher to register handlers
    dispatcher = updater.dispatcher

    conv_handler_attendance = ConversationHandler(
            entry_points=[CommandHandler("attendance", choosing_date_low_access)],
            states={
                1: [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$'),
                    CallbackQueryHandler(indicate_attendance, pattern='^(\d{10}|\d{12})$')
                    ],
                2: [
                    CallbackQueryHandler(give_reason, pattern="^0$"),
                    CallbackQueryHandler(give_reason, pattern="^1$"),
                    CallbackQueryHandler(update_attendance, pattern="^2$"),
                    MessageHandler(Filters.text & ~Filters.command, update_attendance)
                    ],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
            )

    conv_handler_kaypoh = ConversationHandler(
            entry_points=[CommandHandler("kaypoh", choosing_date_high_access)],
            states={
                1: [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$'),
                    CallbackQueryHandler(attendance_list, pattern='^(\d{10}|\d{12})$')
                    ],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
            )

    conv_handler_mass_attendance = ConversationHandler(
            entry_points=[CommandHandler("attendance_plus", choosing_more_dates)],
            states={
                1: [
                    CallbackQueryHandler(choosing_more_dates_cont, pattern='^(\d{10}|\d{12})$'),
                    CallbackQueryHandler(indicate_more, pattern='^forward$')
                    ],
                2: [
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
                1: [
                    CallbackQueryHandler(page_change, pattern='^-?[0-9]{0,10}$'),
                    CallbackQueryHandler(generate_ics, pattern='^(\d{10}|\d{12})$')
                    ],
                },
            fallbacks=[CommandHandler("cancel", cancel)],
            )

    conv_handler_settings = ConversationHandler(
            entry_points=[CommandHandler("settings",settings_start)],
            states={
                1: [
                    CallbackQueryHandler(name_change, pattern="^name$"),
                    CallbackQueryHandler(notification_change, pattern="^notification$"),
                    CallbackQueryHandler(language_change, pattern="^language$")
                    ],
                1.1: [MessageHandler(Filters.text & ~Filters.command, confirmation_name_change)],
                1.2: [CallbackQueryHandler(commit_notification_change, pattern="^\d$")],
                2.1: [
                CallbackQueryHandler(commit_name_change, pattern="^forward$"),
                CallbackQueryHandler(name_change, pattern="^back$")
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
                        )

    conv_handler_register = ConversationHandler(
            entry_points=[CommandHandler("register", select_gender)],
            states={
                1: [
                    CallbackQueryHandler(fill_name, pattern='^Male$'),
                    CallbackQueryHandler(fill_name, pattern='Female')
                    ],
                2: [
                    MessageHandler(Filters.text & ~Filters.command, confirm_name_registration),
                    ],
                3: [
                    CallbackQueryHandler(commit_registration, pattern='^forward$')
                    ],
                },
            fallbacks=[CommandHandler('cancel', cancel)],
            )
    # conv_handler_apply_members = ConversationHandler(
    #         entry_points=[CommandHandler("apply_membership", review_membership)],
    #         states={
    #             1: [
    #                 CallbackQueryHandler(commit_membership_position),
    #                 ],
    #             },
    #         fallbacks=[CommandHandler('cancel', cancel)]
    #         )
    #
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(conv_handler_attendance)
    dispatcher.add_handler(conv_handler_kaypoh)
    dispatcher.add_handler(conv_handler_mass_attendance)
    dispatcher.add_handler(CommandHandler("events", events))
    dispatcher.add_handler(conv_handler_register)
    dispatcher.add_handler(conv_handler_save_event)
    dispatcher.add_handler(conv_handler_settings)
    # dispatcher.add_handler(conv_handler_apply_members)
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    webhook_url = CONFIG['training_bot_url']

    if CONFIG["use_webhook"]:
        logger.info('initiating webhook on %s', webhook_url)
        updater.start_webhook(
                listen="0.0.0.0",
                port=5010,
                url_path=token,
                )
        logger.info('setting webhook...')
        updater.set_webhook(webhook_url + token)
    else:
        logger.info('using polling instead')
        updater.start_polling()
        updater.idle()


if __name__ == "__main__":
    main()
