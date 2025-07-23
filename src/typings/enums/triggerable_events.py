from enum import Enum

class TriggerableEvent(Enum):
    """
        Chaster Events
    """
    CHASTER_PILLORY_VOTE = "chaster_PilloryVote",
    CHASTER_VOTE_ADD = "chaster_VoteAdd",
    CHASTER_VOTE_SUB = "chaster_VoteSub",
    
    """
        Sensors Events
    """
    SENSOR_SOUND = "sensor_Sound",
    SENSOR_POSITION = "sensor_Position",
    SENSOR_MOVE = "sensor_Move",
    
    """
        # TODO: X/Twitter Events
        WIP, release date; TBA
    """
    
    # TWITTER_RETWEET = "twitter_ReTweet",
    # TWITTER_FAVORITE = "twitter_Favorite",
    # TWITTER_FOLLOW = "twitter_Follow"