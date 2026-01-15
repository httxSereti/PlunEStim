import threading
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

@dataclass
class User:
    id: str
    display_name: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id
        return False
