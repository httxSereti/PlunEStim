from nextcord import Interaction, slash_command
from nextcord.ext.commands import Cog

class PingCommand(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        description="Show current latency"
    )
    async def ping(self, interaction: Interaction):
        await interaction.send(f"Pong! {self.bot.latency * 1000:.2f}ms")

def setup(bot):
    bot.add_cog(PingCommand(bot))