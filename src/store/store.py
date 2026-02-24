import threading
import asyncio
from typing import Dict, Optional, Set

from models.User import User

from api.ws.websocket_manager import WebSocketManager
from typings import UnitDict, Role, Permission

class Store:
    """
    Singleton thread-safe to store variables
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self._units_settings: Dict[str, Dict] = {
                    UnitDict.UNIT1.value: {},
                    UnitDict.UNIT2.value: {},
                    UnitDict.UNIT3.value: {},
                }
                self._sensors_settings: Dict = {}
                
                # Initalize Sensors
                self._init_sensors()

                self._users: Dict[str, User] = {}
                self._websocket = WebSocketManager()

                # separated lock for better concurrency
                self._units_lock = threading.RLock()
                self._sensors_lock = threading.RLock()
                self._users_lock = threading.RLock()

                self._initialized = True

    """
        Init Functions
    """

    def _init_sensors(self) -> None:
        """
        Initialize Sensors with default values, supported sensors;
          - move (x2)
          - sound (x1)
        """

        # Motion sensors init
        motion_config = {
            "id": "motion1",
            "sensor_type": "motion",
            "sensor_online": False,  # true if the sensors is online
            "position_ref": -1.0,  # position reference
            "position_alarm_level": 45,  # threshold for position alarm action
            "position_delay_on": 1,  # nb consecutive value for starting an action
            "position_delay_off": 5,  # nb consecutive value before starting an action again
            "move_alarm_level": 12,  # threshold for moving alarm action
            "move_delay_on": 1,  # nb consecutive value for starting an action
            "move_delay_off": 5,  # nb consecutive value before starting an action again
            "position_alarm_counter": 0,  # Num of consecutive position alarm
            "move_alarm_counter": 0,  # Num of consecutive move alarm
            "position_alarm_number": 0,  # Number of the last alarm
            "move_alarm_number": 0,  # Number of the last alarm
            "position_alarm_number_action": 0,  # Number of the last alarm who had generated an action
            "move_alarm_number_action": 0,  # Number of the last alarm who had generated an action
            "current_position": 0,  # Current position value
            "current_move": 0,  # Current move value
            "alarm_enable": False,  # alarm activation
        }

        self._sensors_settings["motion1"] = motion_config
        self._sensors_settings["motion2"] = motion_config.copy()
        
        self._sensors_settings["motion2"]["id"] = "motion2"

        # Sound sensor init
        self._sensors_settings["sound"] = {
            "id": "sound",
            "sensor_type": "sound",
            "sensor_online": False,  # true if the sensors is online
            "sound_alarm_level": 30,  # threshold for position alarm action
            "sound_delay_on": 5,  # nb consecutive value for starting an action
            "sound_delay_off": 10,  # nb consecutive value before starting an action again
            "sound_alarm_counter": 0,  # Num of consecutive sound alarm
            "sound_alarm_number": 0,  # Number of the last alarm
            "sound_alarm_number_action": 0,  # Number of the last alarm who had generated an action
            "current_sound": 0,  # Current sound value
            "alarm_enable": False,  # alarm activation
        }

    """
        Units Functions
    """

    def get_unit_setting(self, unit_dict: UnitDict, key: str, default=None):
        with self._units_lock:
            dict_name = unit_dict.value
            if dict_name not in self._units_settings:
                return default
            return self._units_settings[dict_name].get(key, default)

    def set_unit_setting(self, unit_dict: UnitDict, key: str, value):
        with self._units_lock:
            dict_name = unit_dict.value
            if dict_name not in self._units_settings:
                raise KeyError(f"Dictionary '{dict_name}' doesn't exist")
            self._units_settings[dict_name][key] = value

    def get_unit_dict(self, unit_dict: UnitDict) -> Dict:
        with self._units_lock:
            dict_name = unit_dict.value
            if dict_name not in self._units_settings:
                return {}
            return self._units_settings[dict_name].copy()

    def update_unit_dict(self, unit_dict: UnitDict, settings: Dict):
        with self._units_lock:
            dict_name = unit_dict.value
            if dict_name not in self._units_settings:
                raise KeyError(f"Dictionary '{dict_name}' doesn't exist")
            self._units_settings[dict_name].update(settings)

    def get_all_units_settings(self) -> Dict[str, Dict]:
        with self._units_lock:
            return {
                name: dict_content.copy()
                for name, dict_content in self._units_settings.items()
            }

    def clear_unit_dict(self, unit_dict: UnitDict):
        with self._units_lock:
            dict_name = unit_dict.value
            if dict_name in self._units_settings:
                self._units_settings[dict_name].clear()

    def clear_units_settings(self):
        with self._units_lock:
            for dict_content in self._units_settings.values():
                dict_content.clear()

    """
        Sensors Functions
    """

    def get_sensor_setting(self, key: str, default=None):
        with self._sensors_lock:
            return self._sensors_settings.get(key, default)

    def set_sensor_setting(self, key: str, value):
        with self._sensors_lock:
            self._sensors_settings[key] = value
        
        # broadcast change
        self._broadcast_sensor_update(key, value)
            
    def update_sensor_fields(self, sensor_name: str, fields: Dict):
        with self._sensors_lock:
            if sensor_name not in self._sensors_settings:
                raise KeyError(f"Sensor '{sensor_name}' doesn't exist")
            self._sensors_settings[sensor_name].update(fields)
        
        # broadcast only updated fields
        self._broadcast_sensor_update(sensor_name, fields, partial=True)
    
    def update_sensor_field(self, sensor_name: str, field_name: str, value):
        with self._sensors_lock:
            if sensor_name not in self._sensors_settings:
                raise KeyError(f"Sensor '{sensor_name}'  doesn't exist")
            self._sensors_settings[sensor_name][field_name] = value
        
        # broadcast only updated field
        self._broadcast_sensor_update(sensor_name, {field_name: value}, partial=True)
    
    def _broadcast_sensor_update(self, sensor_id: str, data: Dict, partial: bool = False):
        """
            Broadcast to WebSocket clients sensor updates
        """
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    return
            
            message = {
                "type": "sensors:update",
                "payload": {
                    "id": sensor_id,
                    "partial": partial,
                    "changes": data
                }
            }
            
            asyncio.run_coroutine_threadsafe(
                self._websocket.broadcast(message),
                loop
            )
        except Exception as e:
            print(f"[WebSocket] Error when broadcast sensor update: {e}")

    def get_all_sensors_settings(self) -> Dict:
        with self._sensors_lock:
            return self._sensors_settings.copy()

    def clear_sensors_settings(self):
        with self._sensors_lock:
            self._sensors_settings.clear()

    """
        User Functions
    """

    def add_user(self, user: User):
        with self._users_lock:
            self._users[user.id] = user

    def get_user(self, user_id: str) -> Optional[User]:
        with self._users_lock:
            return self._users.get(user_id)

    def remove_user(self, user_id: str):
        with self._users_lock:
            self._users.pop(user_id, None)

    def get_all_users(self) -> Dict[str, User]:
        with self._users_lock:
            return self._users.copy()

    """
        User Roles/Permissions Functions
    """

    def set_user_role(self, user_id: str, role: Role):
        with self._users_lock:
            user = self._users.get(user_id)
            if user:
                user.role = role

    def add_user_permission(self, user_id: str, permission: Permission):
        with self._users_lock:
            user = self._users.get(user_id)
            if user:
                user.custom_permissions.add(permission)

    def remove_user_permission(self, user_id: str, permission: Permission):
        with self._users_lock:
            user = self._users.get(user_id)
            if user:
                user.custom_permissions.discard(permission)

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        with self._users_lock:
            user = self._users.get(user_id)
            return user.has_permission(permission)

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        with self._users_lock:
            user = self._users.get(user_id)
            if user:
                return user.get_permissions()
            return set()

    def require_permission(self, user_id: str, permission: Permission):
        if not self.check_permission(user_id, permission):
            user = self.get_user(user_id)
            display_name = user.display_name if user else "Unknown"
            raise PermissionError(
                f"User '{display_name}' doesn't have permission: {permission.value}"
            )

    @property
    def websocket(self) -> WebSocketManager:
        return self._websocket
