import nextcord
from datetime import datetime
from typings import TriggerableEvent

def EmbedChasterWOFTurned(
    author: str,  
    wofText: str,
    triggeredAt: str,
) -> nextcord.Embed:
    
    # replace author to have a better display
    if author == "user":
        author = ":lock: **Subject**"
    else:
        author = ":closed_lock_with_key: Keyholder"
    
    embed: nextcord.Embed = nextcord.Embed(
        title=":arrows_counterclockwise: Turned WOF",
        description="{} turned the wheel of fortune".format(author),
        color=nextcord.Color.purple(),
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail("https://cdn02.chaster.app/app/uploads/avatars/bB4wAseSW4arDWWU.jpg")
    
    embed.add_field(
        name=":envelope: Action:",
        value=f"{wofText}",
        inline=False
    )
    
    embed.add_field(
        name=":alarm_clock: Turned at:",
        value="<t:{}:R>".format(int(datetime.fromisoformat(triggeredAt).timestamp())),
        inline=True
    )
    
    embed.set_footer(
        text="PlunEStim [v1.0.0]",
        icon_url="https://media.discordapp.net/attachments/1365640845948354590/1380889378888487094/lune.png?ex=684584f3&is=68443373&hm=a93c967fe70134dbf6aea9b1cbb183f0f6d3e9587b15847eae9f5f5e5a24c330&=&format=webp&quality=lossless"
    )
    
    return embed

def EmbedChasterSharedLinkVote(
    author: str,  
    duration: int,
    triggeredAt: str,
) -> nextcord.Embed:
    
    consequence: str = "added time" if duration > 0 else "removed time"
    
    embed: nextcord.Embed = nextcord.Embed(
        title=":wilted_rose: An user voted on your lock!",
        description="**{}** {}".format(author, consequence),
        color=nextcord.Color.purple(),
        timestamp=datetime.now()
    )
    
    embed.set_thumbnail("https://cdn02.chaster.app/app/uploads/avatars/bB4wAseSW4arDWWU.jpg")
    
    embed.add_field(
        name=":envelope: Duration:",
        value=f"{duration} s",
        inline=False
    )
    
    embed.add_field(
        name=":alarm_clock: Triggered at:",
        value="<t:{}:R>".format(int(datetime.fromisoformat(triggeredAt).timestamp())),
        inline=True
    )
    
    embed.set_footer(
        text="PlunEStim [v1.0.0]",
        icon_url="https://media.discordapp.net/attachments/1365640845948354590/1380889378888487094/lune.png?ex=684584f3&is=68443373&hm=a93c967fe70134dbf6aea9b1cbb183f0f6d3e9587b15847eae9f5f5e5a24c330&=&format=webp&quality=lossless"
    )
    
    return embed