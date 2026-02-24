import nextcord
from datetime import datetime


def ErrorEmbed(
    errorName: str,
    errorReason: str,
    hideReason: bool = False
) -> nextcord.Embed:
    embed: nextcord.Embed = nextcord.Embed(
        title=f"{errorName} **Error**",
        description="You can't perform this action!",
        color=nextcord.Color.red(),
        timestamp=datetime.now()
    )
    
    if hideReason:
        embed.add_field(
            name="Reason:",
            value=f"||{errorReason}||",
            inline=True        
        )
    else:
        embed.add_field(
            name="Reason:",
            value=f"{errorReason}",
            inline=True        
        )
        
    embed.set_footer(text="PlunEStim [v1.0.0]")
    
    return embed