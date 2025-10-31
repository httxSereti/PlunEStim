import nextcord
import re
from datetime import datetime
from pprint import pprint

def EmbedEventList(
    eventActions: dict
) -> nextcord.Embed:
    
    embed: nextcord.Embed = nextcord.Embed(
        title=":mag_right: Events",
        description="*List of the current Events available and Actions associated with*",
        color=nextcord.Color.purple(),
        timestamp=datetime.now()
    )
    
    # TODO: sort by modifier if possible
    # loop events to format data to print
    for event, eventName in eventActions.items():
        if eventActions[event]:
            action: dict = eventActions[event]
            actionType: str = action["type"]
            actionText: list[str] = []
            
            if actionType == "lvl":
                actionText.append("✩ Modifier: **Level**")
                actionText.append("✩ UNIT(s): **{}**".format(action["unit"]))
                actionText.append("✩ Channel(s): **{}**".format(action["dest"]))
                actionText.append("✩ Change **{}**".format(action["level"]))
                actionText.append("✩ Duration: **{}s**".format(action["duration"]))
                actionText.append("✩ Waiting: **{}**".format(action["wait"]))
            
            if actionType == "pro":
                actionText.append("✩ Modifier: **Profile**")
                actionText.append("✩ Profile(s): **{}**".format(action["profile"]))
                actionText.append("✩ Level **{}**".format(action["level"]))
                actionText.append("✩ Duration: **{}s**".format(action["duration"]))
                actionText.append("✩ Waiting: **{}**".format(action["wait"]))
            
            if actionType == "multi":
                actionText.append("✩ Modifier: **Multiplier**")
                actionText.append("✩ Change: **{}%**".format(action["prct"]))
                actionText.append("✩ Target: **{}**".format(action["target"]))
                actionText.append("✩ Random: **{}**".format(action["rnd"]))
            
            if actionType == "add":
                actionText.append("✩ Modifier: **Duration**")
                actionText.append("✩ Duration: **{}**".format(action["duration"]))
                actionText.append("✩ Add in resting: **{}**".format(action["only_max"]))
            
            
            embed.add_field(
                name=f":ribbon: **{event}**:",
                value="\n".join(actionText),
                inline=True
            )
    
    embed.set_footer(
        text="PlunEStim [v1.0.0]",
        icon_url="https://media.discordapp.net/attachments/1365640845948354590/1380889378888487094/lune.png?ex=684584f3&is=68443373&hm=a93c967fe70134dbf6aea9b1cbb183f0f6d3e9587b15847eae9f5f5e5a24c330&=&format=webp&quality=lossless"
    )
    
    return embed