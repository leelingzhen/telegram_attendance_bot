
from functools import wraps
from telegram import ChatAction

from src.user_manager import UserManager
from src.Enum.Enum import AccessCategory
from src.Controller.UserValidation import UserValidation

class Decorators:
    def send_typing_action(func):
        """Sends typing action while processing func command."""

        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
            return func(update, context, *args, **kwargs)

        return command_func


    # DEPRECATED
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


    def check_and_cache_user(func):
        """Sends typing action while processing func command."""

        @wraps(func)
        def wrapped(update, context, *args, **kwargs):
            telegram_user_object = update.effective_user
            validation = UserValidation()
            if not validation.user_exists(user_id=telegram_user_object.id):
                user = validation.make_new_user(
                    id=telegram_user_object.id,
                    telegram_user=telegram_user_object.username)
                validation.cache_user(user, AccessCategory.public)
            return func(update, context, *args, **kwargs)

        return wrapped
