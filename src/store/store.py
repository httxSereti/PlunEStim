import threading
from typing import Dict, Optional
from datetime import datetime

from models.User import User

from api.ws.websocket_manager import WebSocketManager
from typings import UnitDict

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
                    UnitDict.UNIT3.value: {}
                }
                self._sensors_settings: Dict = {}
                self._users: Dict[str, User] = {}
                self._websocket = WebSocketManager()

                # separated lock for better concurrency
                self._units_lock = threading.RLock()
                self._sensors_lock = threading.RLock()
                self._users_lock = threading.RLock()
                
                self._initialized = True

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
                raise KeyError(f"Dictionary '{dict_name}' doesn't exist.")
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
                raise KeyError(f"Dictionary '{dict_name}' doesn't exist.")
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
    
    def update_sensors_settings(self, settings: Dict):
        with self._sensors_lock:
            self._sensors_settings.update(settings)
    
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
    
    @property
    def websocket(self) -> WebSocketManager:
        return self._websocket
