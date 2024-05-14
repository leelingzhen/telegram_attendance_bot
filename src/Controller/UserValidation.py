from abc import ABC, abstractmethod
from src.Database.Services.UserService import UserService, UserServicing
from src.Database.Services.AccessService import AccessService, AccessServicing
from src.Models.User import User
from src.Models.Access import Access
from src.Enum.Enum import AccessCategory

class UserValidating(ABC):

    @abstractmethod
    def user_exists(self, user_id) -> bool:
        pass

    @abstractmethod
    def cache_user(self, user: User, access: AccessCategory):
        pass

    @abstractmethod
    def make_new_user(
            self,
            id: int,
            telegram_user: str,
            name: str,
            gender: str,
            notification: int,
            language_pack: str,
            hidden: int
    ) -> User:
        pass


class UserValidation(UserValidating):

    def __init__(
            self,
            user_service: UserServicing = UserService(),
            access_service: AccessServicing = AccessService(),
    ):
        self.user_service = user_service
        self.access_service = access_service

    def user_exists(self, user_id) -> bool:
        return self.user_service.is_exists(user_id)

    def cache_user(self, user: User, access: AccessCategory = AccessCategory.public):
        self.user_service.insert(user)
        access = Access(control_id=access.value, user_id=user.id)
        self.access_service.insert(access)
        return

    def make_new_user(
            self,
            id: int,
            telegram_user: str,
            name: str = None,
            gender: str = None,  # Male or Female
            notification: int = 1,
            language_pack: str = 'default',
            hidden: int = 0
    ):
        return User(
            id=id,
            telegram_user=telegram_user,
            name=name,
            gender=gender,
            notification=notification,
            language_pack=language_pack,
            hidden=hidden
        )


