import nextcord
from nextcord import Interaction, SlashOption, slash_command
from nextcord.ext.commands import Cog

from utils.discord import check_permission, SecurityEmbedError

class SecurityCommands(Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        name="security",
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
                    str(interaction.user.id), # type: ignore
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
                    str(interaction.user.id), # type: ignore
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
                    str(interaction.user.id), # type: ignore
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
        user: str = SlashOption(
            name="user",
            description="User to remove from Administrators",
        ),
    ):
        userId: int = int(user)
        
        if await check_permission(interaction, "administrator"):
            if userId not in self.bot.administrators:
                await interaction.response.send_message(embed=SecurityEmbedError(
                    str(interaction.user.id), # type: ignore
                    "Command",
                    "User already don't have permissions"
                ))
                
                return 
            
            self.bot.administrators.remove(userId)
            await interaction.response.send_message(f"{interaction.user} just removed <@{userId}> from Administrators.")
            
    @remove.on_autocomplete("user")
    async def remove_autocomplete(self, interaction: Interaction, user: str):
        admins: dict = {}
        
        for adminId in self.bot.administrators:
            adminUser: nextcord.User = self.bot.get_user(adminId)
            choiceName = "{} ({})".format(
                adminUser.display_name,
                adminUser.name
            )
            admins[choiceName] = str(adminId)

        await interaction.response.send_autocomplete(admins)

def setup(bot):
    bot.add_cog(SecurityCommands(bot))