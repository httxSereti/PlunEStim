import nextcord

from typings import PilloryVoteDict, TriggerableEvent
from .embeds.pillory import EmbedChasterPilloryStarted, EmbedChasterPilloryVote
from .embeds.chaster_common import EmbedChasterWOFTurned, EmbedChasterSharedLinkVote

class Notifier():
    """
        Notifications Controller
    """
    
    def __init__(self, bot):
        self.bot = bot

    async def triggerEvent(
        self, 
        eventType: TriggerableEvent,
        **kwargs
    ) -> nextcord.Message | None:
        nextcordMessage: nextcord.Message | None = None
        
        print(eventType)
        
        # Start a Pillory on Chaster
        if eventType == TriggerableEvent.CHASTER_PILLORY_STARTED:
            nextcordMessage = await self.bot.logChannel.send(
                embed=EmbedChasterPilloryStarted(
                    reason=kwargs["eventData"]['reason'],
                    nbVotes=kwargs["eventData"]['nbVotes'],
                    startedAt=kwargs["eventData"]['startedAt'],
                    endAt=kwargs["eventData"]['endAt'],
                )
            )
        
        # Detected new Pillory votes on Chaster
        if eventType == TriggerableEvent.CHASTER_PILLORY_VOTE:
            nextcordMessage = await self.bot.logChannel.send(
                embed=EmbedChasterPilloryVote(
                    reason=kwargs["eventData"]['reason'],
                    nbVotes=kwargs["eventData"]["nbVotes"],
                    nbTotalVotes=kwargs["eventData"]['nbTotalVotes'],
                    endAt=kwargs["eventData"]['endAt'],
                )
            )

        if eventType == TriggerableEvent.CHASTER_WOF_TURNED:
            nextcordMessage = await self.bot.logChannel.send(
                embed=EmbedChasterWOFTurned(
                    author=kwargs["eventData"]['author'],
                    wofText=kwargs["eventData"]["wofText"],
                    triggeredAt=kwargs["eventData"]['triggeredAt'],
                )
            )
            
        if eventType == TriggerableEvent.CHASTER_VOTE_ADD or eventType == TriggerableEvent.CHASTER_VOTE_SUB:
            print("helasldasdoao")
            nextcordMessage = await self.bot.logChannel.send(
                embed=EmbedChasterSharedLinkVote(
                    author=kwargs["eventData"]['author'],
                    duration=kwargs["eventData"]["duration"],
                    triggeredAt=kwargs["eventData"]['triggeredAt'],
                )
            )
            
        return nextcordMessage