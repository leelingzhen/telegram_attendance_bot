from enum import Enum


class Gender(Enum):
    male = "Male"
    female = "Female"
    both = ""


class AccessCategory(Enum):
    all = -1
    public = 0
    pending_guests = 1
    guest = 2
    pending_members = 3
    member = 4
    core = 5
    admin = 6
    team_manager = 7
    superuser = 100

    @property
    def is_at_least_member(self) -> bool:
        return self.value >= self.member.value

    @property
    def is_at_least_guest(self):
        return self.value >= self.guest.value

    @staticmethod
    def enum_from_int(value: int) -> "AccessCategory":
        for category in AccessCategory:
            if category.value == value:
                return category



