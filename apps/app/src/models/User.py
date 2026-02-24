from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

from typings import Role, Permission, ROLE_PERMISSIONS

@dataclass
class User:
    id: str
    display_name: Optional[str]
    magic_token: str
    is_online: bool = False
    
    created_at: datetime = field(default_factory=datetime.now)
    
    metadata: Dict = field(default_factory=dict)
    
    role: Role = Role.GUEST
    custom_permissions: Set[Permission] = field(default_factory=set)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id
        return False

    def get_permissions(self) -> Set[Permission]:
        role_perms = ROLE_PERMISSIONS.get(self.role, set())
        return role_perms | self.custom_permissions
    
    def has_permission(self, permission: Permission) -> bool:
        perms = self.get_permissions()
        if Permission.ROOT in perms:
            return True
        return permission in perms
    
    def has_any_permission(self, *permissions: Permission) -> bool:
        user_perms = self.get_permissions()
        return any(perm in user_perms for perm in permissions)
    
    def has_all_permissions(self, *permissions: Permission) -> bool:
        user_perms = self.get_permissions()
        return all(perm in user_perms for perm in permissions)
