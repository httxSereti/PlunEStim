from enum import Enum

class Permission(Enum):
    """
        Permission enum with all permissions for Users
    """
    READ_UNITS = "read_units"
    READ_SENSORS = "read_sensors"
    READ_PROFILES = "read_profiles"
    READ_USERS = "read_users"
    
    WRITE_UNITS = "write_units"
    WRITE_SENSORS = "write_sensors"
    WRITE_PROFILES = "write_profiles"
    
    MANAGE_USERS = "manage_users"
    MANAGE_SENSORS = "manage_sensors"
    MANAGE_PROFILES = "manage_profiles"
    
    ADMIN = "admin"
    ROOT = "root"
