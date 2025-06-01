import nextcord

def SecurityEmbedError(
    errorAuthor: str,
    errorName: str,
    errorReason: str,
) -> nextcord.Embed:
    embed: nextcord.Embed = nextcord.Embed(
        title=f"{errorName} **Error**",
        description="You can't perform this action!",
        color=nextcord.Color.red()
    )
    
    embed.add_field(
        name="User:",
        value=f"<@{errorAuthor}>",
        inline=True        
    )
    
    embed.add_field(
        name="Reason:",
        value=f"{errorReason}",
        inline=True        
    )
    
    return embed