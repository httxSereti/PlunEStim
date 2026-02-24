import nextcord
from datetime import datetime

def EmbedChasterPilloryStarted(
    reason: str,  
    nbVotes: int,
    startedAt: str,
    endAt: str,
) -> nextcord.Embed:
    embed: nextcord.Embed = nextcord.Embed(
        title=":hammer: Pillory!",
        description="You've been pilloried!..",
        color=nextcord.Color.purple(),
        timestamp=datetime.now()
    )       
    
    embed.set_thumbnail("https://cdn02.chaster.app/app/uploads/avatars/bB4wAseSW4arDWWU.jpg")
    
    embed.add_field(
        name=":envelope: Reason:",
        value=f"{reason}",
        inline=False
    )
    
    embed.add_field(
        name=":level_slider: Votes:",
        value=f"{nbVotes} votes",
        inline=False
    )
    
    embed.add_field(
        name=":alarm_clock: Started at:",
        value="<t:{}:R>".format(int(datetime.fromisoformat(startedAt).timestamp())),
        inline=True
    )
    
    embed.add_field(
        name=":alarm_clock: End at:",
        value="<t:{}:R>".format(int(datetime.fromisoformat(endAt).timestamp())),
        inline=True
    )
    
    embed.set_footer(
        text="PlunEStim [v1.0.0]",
        icon_url="https://media.discordapp.net/attachments/1365640845948354590/1380889378888487094/lune.png?ex=684584f3&is=68443373&hm=a93c967fe70134dbf6aea9b1cbb183f0f6d3e9587b15847eae9f5f5e5a24c330&=&format=webp&quality=lossless"
    )
    
    return embed

def EmbedChasterPilloryVote(
    reason: str,  
    nbVotes: int,
    nbTotalVotes: int,
    endAt: str,
) -> nextcord.Embed:
    embed: nextcord.Embed = nextcord.Embed(
        title=":hammer: Pillory Vote!",
        description="You've received a vote!..",
        color=nextcord.Color.purple(),
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail("https://cdn02.chaster.app/app/uploads/avatars/bB4wAseSW4arDWWU.jpg")
    
    embed.add_field(
        name=":envelope: Reason:",
        value=f"{reason}",
        inline=False
    )
    
    embed.add_field(
        name=":level_slider: Votes received:",
        value=f"<:increase:1384470395100467220> + {nbVotes} votes ({nbTotalVotes} votes)",
        inline=False
    )
    
    embed.add_field(
        name=":alarm_clock: End at:",
        value="<t:{}:R>".format(int(datetime.fromisoformat(endAt).timestamp())),
        inline=True
    )
    
    embed.set_footer(
        text="PlunEStim [v1.0.0]",
        icon_url="https://media.discordapp.net/attachments/1365640845948354590/1380889378888487094/lune.png?ex=684584f3&is=68443373&hm=a93c967fe70134dbf6aea9b1cbb183f0f6d3e9587b15847eae9f5f5e5a24c330&=&format=webp&quality=lossless"
    )
    
    return embed