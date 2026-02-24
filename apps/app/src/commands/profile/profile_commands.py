import time
import nextcord
import pathlib
import os
import json

from pprint import pprint

from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext.commands import Cog

from utils.discord import check_permission, ErrorEmbed

DIR_PROFILE = pathlib.Path(os.getenv('DIR_PROFILE')) # type: ignore


class ProfileCommands(Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        name="profilev2",
        description="Commands to manage Profiles."
    )
    async def profile(self, interaction: Interaction):
        pass 

    @profile.subcommand(
        name="list",
        description="List Profiles",
    )
    async def list(
        self,
        interaction: Interaction
    ):
        files = os.listdir(DIR_PROFILE)
        
        pprint(files)
        await interaction.response.send_message(f"Searching")
    
    @profile.subcommand(
        name="view",
        description="View profile",
    )
    async def view(
        self,
        interaction: Interaction,
        name: str
    ):
        profileFile = open(DIR_PROFILE / "K.json", 'r')
        backup_data = json.load(profileFile)
        pprint(backup_data)
        await interaction.response.send_message(f"Searching {name}")
            
    @profile.subcommand(
        name="apply",
        description="Apply profile"
    )
    async def purge(self, interaction: Interaction):
        await interaction.response.send_message(f"Applying {name}")

def setup(bot):
    bot.add_cog(ProfileCommands(bot))