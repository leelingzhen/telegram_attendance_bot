from abc import ABC, abstractmethod
from src.Database.Services.UserService import UserService, UserServicing
from src.Database.Services.UserService import UserServicing
from src.Models.User import User
from src.Enum.Enum import AccessCategory


class UserProviding(ABC):

    @abstractmethod
    def is_exists(self, user_id: int) -> bool:
        pass

    @abstractmethod
    def user(self, user_id: int) -> User:
        pass

    @abstractmethod
    def users(self, access: AccessCategory) -> list[User]:
        pass

    @abstractmethod
    def user_access(self, user_id: int) -> AccessCategory:
        pass


class UserProvider(UserProviding):

    user_service: UserServicing

    def __init__(
            self,
            user_service: UserServicing = UserService(),
    ):
        self.user_service = user_service

    def is_exists(self, user_id: int) -> bool:
        return self.user_service.is_exists(user_id)

    def user(self, user_id) -> User:
        return self.user_service.get_user_by(user_id)

    def users(self, access: AccessCategory) -> list[User]:
        users = self.user_service.get_users_by_access(access)
        return users

    def user_access(self, user_id: int) -> AccessCategory:
        access = self.user_service.get_user_access(user_id)

        return access
