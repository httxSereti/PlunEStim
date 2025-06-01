import time

import nextcord
from nextcord import Interaction, slash_command, SlashOption
from nextcord.ext.commands import Cog

list_of_dog_breeds = [
    "German Shepard",
    "Poodle",
    "Pug",
    "Shiba Inu",
]

class HelpCommand(Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        description="Show Help"
    )
    async def help(self, interaction: Interaction):
        
        await self.bot.add_event_action(
            'pilloryvote',
            'pillory_chaster' + '_' + "lucie",
            time.localtime()
        )
        
        
        await interaction.send(f"Pong! {self.bot.latency * 1000:.2f}ms")
        
    
    @slash_command()
    async def your_favorite_dog(
        self,
        interaction: Interaction,
        dog: str = SlashOption(
            name="dog",
            description="Choose the best dog from this autocompleted list!",
        ),
    ):
        # sends the autocompleted result
        await interaction.response.send_message(f"Your favorite dog is {dog}!")


    @your_favorite_dog.on_autocomplete("dog")
    async def favorite_dog(self, interaction: Interaction, dog: str):
        print(interaction.user.id)
        
        admins: dict = {}
        
        for adminId in self.bot.administrators:
            user: nextcord.User = self.bot.get_user(adminId)
            
            admins[user.display_name] = str(adminId)

        await interaction.response.send_autocomplete(admins)


def setup(bot):
    bot.add_cog(HelpCommand(bot))