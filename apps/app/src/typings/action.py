from typing import TypedDict, Optional

class ActionDict(TypedDict, total=False):
    """
        Dict for an Action

        Attributes
        ----------
        actionType: :class:`str`
            The type of Action <PROFILE|LEVEL|MULT|ADD>.
        \n
        issuer: :class:`str`
            Issuer of the Action.
        \n
        duration: :class:`bool`
            Duration of Action in seconds
        \n
        cumulative: :class:`bool`
            Action should be cumulative to running actions or wait in queue.
        \n
        displayName: :class:`bool`
            How Action should be displayed in UI (ex: Pillory vote from Chaster, at 07:00:00)
        \n
        tags: :class:`list[str]`
            Tags associated with the Action (correction, pleasure...)
        \n
        profile: :class:`str`
            Profile Name to use.
    """
    
    actionType: str
    issuer: str
    duration: int
    cumulative: bool
    displayName: str
    
    tags: list[str]
    
    profile: Optional[str]
    level: Optional[float]