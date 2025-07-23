from enum import Enum

class TriggerableEvent(Enum):
    """
        Chaster Events
    """
    CHASTER_PILLORY_VOTE = "chaster_pillory_vote",
    CHASTER_PILLORY_STARTED = "chaster_pillory_started",
    CHASTER_PILLORY_ENDED = "chaster_pillory_ended",
    
    CHASTER_VOTE_ADD = "chaster_vote_add",
    CHASTER_VOTE_SUB = "chaster_vote_sub",
    
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