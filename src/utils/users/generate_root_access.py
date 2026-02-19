from models import User
from typings import Role
from store import Store

from api.helpers import generate_magic_token

def generate_root_access():
    
    # root user
    rootUser = User(
        id="xsxrxti",
        display_name="Sereti",
        magic_token=generate_magic_token(),
        is_online=False,
        role=Role.ROOT
    )
    
    store = Store()
    store.add_user(rootUser)
    
    print(f"root magic url http://localhost:5173/auth?magic_token={rootUser.magic_token}")
    
    return f"http://localhost:5173/auth?magic_token={rootUser.magic_token}"