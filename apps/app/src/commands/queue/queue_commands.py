import time
import nextcord

from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext.commands import Cog

from utils.discord import check_permission, ErrorEmbed

class QueueCommands(Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        name="queue",
        description="Commands to manage the Actions Queue."
    )
    async def queue(self, interaction: Interaction):
        pass 
    
    @queue.subcommand(
        name="view",
        description="View current queue",
    )
    async def view(self, interaction: Interaction):
        actionWaiting: int = 0
        waitingActionStr: list[str] = []
        
        waitingActionStr.append("# Actions in queue: \n")
        
        for idx in range(len(self.bot.action_queue)):
            if self.bot.action_queue[idx]['counter'] == -1: # action waiting if -1
                actionWaiting = actionWaiting + 1
                waitingActionStr.append("{}• [{}] {}".format(
                    actionWaiting,
                    self.bot.action_queue[idx]['type'],
                    self.bot.action_queue[idx]['origine']
                ))
        
        await interaction.response.send_message("\n".join(waitingActionStr))
        
            
    @queue.subcommand(
        name="purge",
        description="Purge all actions in queue."
    )
    async def purge(self, interaction: Interaction):
        if await check_permission(interaction, "administrator"):
            
            purgedActions: int = 0
            
            for idx in range(len(self.bot.action_queue)):
                if self.bot.action_queue[idx]['counter'] == -1:
                    self.bot.action_queue[idx]['counter'] = self.bot.action_queue[idx]['duration']
                    purgedActions = purgedActions + 1
                    
            await interaction.response.send_message(f"Removed {purgedActions} actions in the queue.")
    
    @queue.subcommand(
        name="resume",
        description="Resume queue."
    )
    async def resume(self, interaction: Interaction):
        if await check_permission(interaction, "administrator"):
            if self.bot.queueRunning == True:
                await interaction.response.send_message(embed=ErrorEmbed(
                    "",
                    "Queue is already resumed!",
                ))
                
                return
            
            self.bot.queueRunning = True
            await interaction.response.send_message(f"Queue is now resumed.")
    
    @queue.subcommand(
        name="pause",
        description="Pause queue."
    )
    async def pause(self, interaction: Interaction):
        if await check_permission(interaction, "administrator"):
            if self.bot.queueRunning == False:
                await interaction.response.send_message(embed=ErrorEmbed(
                    "",
                    "Queue is already paused!",
                ))
                
                return
            self.bot.queueRunning = False
            await interaction.response.send_message(f"Queue is now paused.")


def setup(bot):
    bot.add_cog(QueueCommands(bot))