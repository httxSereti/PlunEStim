from typing import TypedDict, Optional

class ActionDict(TypedDict, total=False):
    """
        Dict for an Action

        Attributes
        ----------
        type: :class:`str`
            The type of Action <PROFILE|LEVEL|MULT|ADD>.
        \n
        origin: :class:`str`
            What triggered this action (ex: chaster_pilloryVote).
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
        profile: :class:`str`
            Profile Name to use.
    """
    type: str
    origin: str 
    duration: int
    cumulative: bool
    displayName: str
    
    profile: Optional[str]
    level: Optional[float]