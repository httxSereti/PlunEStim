import nextcord

def EmbedPlayingActionLevel(
    actionType: str,
    actionOrigin: str,    
) -> nextcord.Embed:
    return nextcord.Embed(
        title="Hello"
    )
    
def EmbedPlayingActionProfile(
    actionOrigin: str,
    profileName: str,  
) -> nextcord.Embed:
    embed: nextcord.Embed = nextcord.Embed(
        title=":zap: Profile Applied!",
        description="Successfully updated Profile!"
    )
    
    embed.add_field(
        name="Profile:",
        value=f"{profileName}",
        inline=True
    )
    
    embed.add_field(
        name="Trigger:",
        value=f"{actionOrigin}",
        inline=True
    )
    
    return embed