from enum import Enum
from typing import Dict, Set
from .user_permissions_enum import Permission

class Role(Enum):
    GUEST = "guest"
    USER = "user"
    OPERATOR = "operator"
    TRUSTED = "trusted"
    ADMIN = "admin"
    ROOT = "root"
    
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.GUEST: {
        Permission.READ_UNITS,
        Permission.READ_SENSORS,
    },
    Role.USER: {
        Permission.READ_UNITS,
        Permission.READ_SENSORS,
        Permission.READ_PROFILES,
    },
    Role.OPERATOR: {
        Permission.READ_UNITS,
        Permission.READ_SENSORS,
        Permission.READ_PROFILES,
        Permission.WRITE_UNITS,
        Permission.WRITE_SENSORS,
    },
    Role.TRUSTED: {
        Permission.READ_UNITS,
        Permission.READ_SENSORS,
        Permission.READ_PROFILES,
        Permission.WRITE_UNITS,
        Permission.WRITE_SENSORS,
        Permission.WRITE_PROFILES,
        Permission.MANAGE_PROFILES,
    },
    Role.ADMIN: {
        Permission.READ_UNITS,
        Permission.READ_SENSORS,
        Permission.READ_PROFILES,
        Permission.READ_USERS,
        Permission.WRITE_UNITS,
        Permission.WRITE_SENSORS,
        Permission.WRITE_PROFILES,
        Permission.MANAGE_USERS,
        Permission.MANAGE_PROFILES,
        Permission.ADMIN,
    },
    Role.ROOT: set(Permission),  # Toutes les permissions
}