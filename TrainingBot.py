import logging
import os
import src.Upgrade.upgrade_manager
from datetime import datetime, date

from src.Controller.UserAttendanceController import UserAttendanceController
from src.Models.Attendance import Attendance
from src.Models.Event import Event
from src.Models.User import User

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

### new imports
from src.Controller.UserProvider import UserProvider
from src.Enum.Enum import AccessCategory, Direction
from src.Controller.EventProvider import EventProvider
from src.Buttons import ToggleReasonButton
from src.Decorators import Decorators
from src.Configuration import Configuration, BotTokens
from src.View.MessageView import SelectEventOptionsView

# enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

CONFIG = Configuration.load_configuration()

# ENTRY POINTS
@Decorators.send_typing_action
@Decorators.check_and_cache_user
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_provider = UserProvider()

    user = user_provider.user(user_id)

    user_access = user_provider.user_access(user_id)
    if user_access == AccessCategory.public:
        update.message.reply_text("Hello new player! please register yourself by using /register")
        return None

    update.message.reply_text("Hello please use the commands to talk to me!")
    logger.info('user %s has talked to the bot', user.name)

    return None


@Decorators.send_typing_action
@Decorators.check_and_cache_user
def validate_at_least_guest(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id

    user_provider = UserProvider()
    user = user_provider.user(user_id)
    access = user_provider.user_access(user_id)

    if not access.is_at_least_guest:
        update.message.reply_text("You do not have access to this command yet.")
        return ConversationHandler.END

    conversation_state = date_choosing_handler(update, context, user, access)

    return conversation_state


@Decorators.send_typing_action
@Decorators.check_and_cache_user
def validate_member(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id

    user_provider = UserProvider()
    user = user_provider.user(user_id)
    access = user_provider.user_access(user_id)

    if not access.is_at_least_member:
        update.message.reply_text("You do not have access to this command yet.")
        return ConversationHandler.END

    conversation_state = date_choosing_handler(update, context, user, access)

    return conversation_state


def page_change_v2(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    scroll_direction = int(query.data)

    context.user_data["page"] += scroll_direction

    page = context.user_data["page"]
    events = context.user_data["events"]

    message_view = SelectEventOptionsView(events, page)
    reply_markup = InlineKeyboardMarkup(message_view.buttons)

    query.edit_message_reply_markup(
        reply_markup=reply_markup
    )

    return 1


def date_choosing_handler(
        update: Update,
        context: CallbackContext,
        user: User,
        access: AccessCategory
) -> int:
    logger.info("user %s is choosing date...", user.name)
    event_provider = EventProvider()

    events = event_provider.events(from_date=date.today(), access=access)
    page = 0

    context.user_data["events"] = events
    context.user_data["user"] = user
    context.user_data["access"] = access
    context.user_data["page"] = page
    context.user_data['is_chosen'] = False

    if not events:
        update.message.reply_text("There are no more further planned events. Enjoy your break!🏝🏝")
        return ConversationHandler.END

    message_view = SelectEventOptionsView(events, current_page=0)
    reply_markup = InlineKeyboardMarkup(message_view.buttons)

    update.message.reply_text(
        text=SelectEventOptionsView.message_text,
        reply_markup=reply_markup
    )
    return 1


def indicate_attendance(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    attendance_controller = UserAttendanceController()

    is_chosen: bool = context.user_data['is_chosen']

    if not is_chosen:
        # retrieve date query and store
        event_id = int(query.data)
        user = context.user_data["user"]

        selected_event = next((event for event in context.user_data["events"] if event.id == event_id), None)

        attendance = Attendance(user_id=user.id, event_id=event_id, reason="", status=-1)
        if attendance_controller.is_exists(event_id, user_id=user.id):
            attendance = attendance_controller.fetch_attendance(event_id=event_id, user_id=user.id)

        attach_reason = False

        # store attendance into context
        context.user_data["event"] = selected_event
        context.user_data['attendance'] = attendance
        context.user_data['prev_status'] = attendance.status
        context.user_data["is_query"] = True

        # date has been chosen so toggle value
        context.user_data['is_chosen'] = True

    else:
        attach_reason_query = query.data

        attach_reason = False
        if attach_reason_query == "on":
            attach_reason = True

        selected_event = context.user_data['event_instance']
        attendance = context.user_data['attendance']

        # store
        context.user_data['attach_reason'] = attach_reason

    event_date = selected_event.event_date

    # always want to create a button state opposite of what attach_reason is
    reason_button = ToggleReasonButton(not attach_reason)

    is_accountable_reason = selected_event.accountable or attach_reason
    attach_reason = int(attach_reason)
    is_accountable_reason = int(is_accountable_reason)

    button = [
        [reason_button],
        [InlineKeyboardButton(f"Yes I ❤️{CONFIG.team_name} ", callback_data=f"1,{attach_reason}")],
        [InlineKeyboardButton("No (lame)", callback_data=f"0,{is_accountable_reason}")],
    ]
    reply_markup = InlineKeyboardMarkup(button)

    query.edit_message_text(
        text=f"""
Your attendance is indicated as \'{attendance.format_attendance}\'

<u>Details</u>
Date: {event_date.strftime('%-d %b, %a')}
Event: {selected_event.event_type}
Time: {selected_event.format_start} - {selected_event.format_end}
Location : {selected_event.location}
Accountable event: {'Yes' if selected_event.accountable else 'No'}

<u>Description</u>
{selected_event.description}
{chr(10) + '<i>You will write your reason/comment in the next step</i>' + chr(10) if attach_reason else ''}
Would you like to go for {selected_event.event_type}?
            """,
        reply_markup=reply_markup,
        parse_mode='html'
    )
    return 2

@Decorators.send_typing_action
def cancel(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    update.message.reply_text(
        text="process cancelled, see you next time!"
    )
    logger.info('user %s just cancelled a process', user.first_name)
    return ConversationHandler.END


def main():

    bot_tokens = BotTokens.load()

    if CONFIG.development:
        token = bot_tokens.dev_bot
    else:
        token = bot_tokens.training_bot

    commands = [
        BotCommand("new_attendance", "testing command"),
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

    single_attendance_handler = ConversationHandler(
        entry_points=[CommandHandler("new_attendance", validate_member)],
        states={
            1: [
                CallbackQueryHandler(page_change_v2, pattern='^-?[0-9]{0,10}$'),
                CallbackQueryHandler(indicate_attendance, pattern='^(\d{10}|\d{12})$')
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(single_attendance_handler)
    dispatcher.add_handler(CommandHandler("cancel", cancel))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
