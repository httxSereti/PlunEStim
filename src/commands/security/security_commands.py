import nextcord
from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext.commands import Cog

from utils.discord import check_permission, SecurityEmbedError
from constants import DISCORD_TESTING_GUILD_IDS

class SecurityCommands(Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        name="security",
        guild_ids=DISCORD_TESTING_GUILD_IDS
    )
    async def security(self, interaction: Interaction):
        pass 
    
    @security.subcommand(
        name="lock",
        description="Remove permissions to Subject.",
    )
    async def lock(self, interaction: Interaction):
        if await check_permission(interaction, "administrator"):
            if self.bot.subjectId not in self.bot.administrators:
                await interaction.response.send_message(embed=SecurityEmbedError(
                    interaction.user.id,
                    "Command",
                    "Subject already got no permissions"
                ))
                
                return 
        
            self.bot.administrators.remove(self.bot.subjectId)
            await interaction.response.send_message(f"<@{self.bot.subjectId}> no longer have permissions.")
            
    @security.subcommand(
        name="unlock",
        description="Give back permissions to Subject.",
    )
    async def unlock(self, interaction: Interaction):
        if await check_permission(interaction, "administrator"):
            if self.bot.subjectId in self.bot.administrators:
                await interaction.response.send_message(embed=SecurityEmbedError(
                    interaction.user.id,
                    "Command",
                    "Subject already have permissions"
                ))
                
                return 
        
            self.bot.administrators.append(self.bot.subjectId)
            await interaction.response.send_message(f"<@{self.bot.subjectId}> have retrieved permissions.")
            
    @security.subcommand()
    async def admin(self, interaction: Interaction):
        pass
        
    @admin.subcommand(
        description="List Administrators.",
    )
    async def list(
        self, 
        interaction: nextcord.Interaction
    ):
        adminList: str = ""
        
        for adminId in self.bot.administrators:
            adminList += f":sparkles: ✿ <@{adminId}>\n"
            
        embed: nextcord.Embed = nextcord.Embed(
            title=f":sparkles: Administrator(s)",
            description=adminList,
            color=nextcord.Color.purple()
        )
        
        await interaction.response.send_message(embed=embed)
        
    @admin.subcommand(
        description="Add @User to Administrators.",
    )
    async def add(
        self,
        interaction: nextcord.Interaction,
        member: nextcord.Member = SlashOption(name="user", description="The User you want to add to Administrators.", required=True),
    ) -> None:
        if await check_permission(interaction, "administrator"):
            if member.id in self.bot.administrators:
                await interaction.response.send_message(embed=SecurityEmbedError(
                    interaction.user.id,
                    "Command",
                    "User already have permissions"
                ))
                
                return 
            
            self.bot.administrators.append(member.id)
            await interaction.response.send_message(f"{interaction.user} just added {member.mention} to Administrators.")
        
    @admin.subcommand(
        description="Remove @User from Administrators."
    )
    async def remove(
        self,
        interaction: nextcord.Interaction,
        member: nextcord.Member = SlashOption(name="user", description="The User you want to remove from Administrators.", required=True),
    ):
        if await check_permission(interaction, "administrator"):
            if member.id not in self.bot.administrators:
                await interaction.response.send_message(embed=SecurityEmbedError(
                    interaction.user.id,
                    "Command",
                    "User already don't have permissions"
                ))
                
                return 
            
            self.bot.administrators.remove(member.id)
            await interaction.response.send_message(f"{interaction.user} just removed {member.mention} from Administrators.")

def setup(bot):
    bot.add_cog(SecurityCommands(bot))