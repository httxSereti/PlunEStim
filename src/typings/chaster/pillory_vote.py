from typing import TypedDict, Optional

class PilloryVoteDict(TypedDict):
    """
        Dict for PilloryVote

        Attributes
        ----------
        actionType: :class:`str`
            The type of Action <PROFILE|LEVEL|MULT|ADD>.
        \n
        issuer: :class:`str`
            Issuer of the Action.
        \n
    """
    
    canVote: bool
    createdAt: str
    nbVotes: int
    reason: str
    totalDurationAdded: int
    voteEndsAt: str
    
    messageId: Optional[str]