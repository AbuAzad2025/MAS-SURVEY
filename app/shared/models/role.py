"""
Roles enum for users.
"""
class Role:
    SUPER_ADMIN = 'super_admin'
    REGISTERED = 'registered'
    GUEST = 'guest'

    ALL = (SUPER_ADMIN, REGISTERED, GUEST)

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls.ALL
