from typing import TypedDict

class ActionDict(TypedDict, total=False):
    origine: str 
    type: str
    profile: str
    level: float