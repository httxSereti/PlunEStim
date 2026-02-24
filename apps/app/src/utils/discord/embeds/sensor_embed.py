import nextcord
import re
from datetime import datetime

def EmbedSensorConfiguration(
    sensorsSettings: dict
) -> nextcord.Embed:
    
    embed: nextcord.Embed = nextcord.Embed(
        title=":mag_right: Sensor Configuration",
        description="*Configuration of the Sensors*",
        color=nextcord.Color.purple(),
        timestamp=datetime.now()
    )
    
    for sensorName in sorted(sensorsSettings.keys()):
        emoji: str = ":green_square:" if sensorsSettings[sensorName]["alarm_enable"] else ":red_square:"
        status: str = "enabled" if sensorsSettings[sensorName]["alarm_enable"] else "disabled"
        sensorText: list[str] = []
        
        # for each sensor type
        for field in sorted(sensorsSettings[sensorName].keys()):
            if ma := re.match(r"^(\w+)_alarm_level$", field):
                sensorType = ma[1]
                
                sensorText.append("")
                sensorText.append("‿︵ Type: **{}**".format(sensorType))
                sensorText.append("୨୧ Threshold: `{}`".format(sensorsSettings[sensorName][sensorType + '_alarm_level']))
                sensorText.append("୨୧ Fire Delay: `{}`".format(sensorsSettings[sensorName][sensorType + '_delay_on']))
                sensorText.append("୨୧ Unfire Delay: `{}`".format(sensorsSettings[sensorName][sensorType + '_delay_off']))

        embed.add_field(
            name=f"{emoji} ₊✩‧₊˚ `{sensorName}`",
            value="\n".join(sensorText),
            inline=True
        )
    
    embed.set_footer(
        text="PlunEStim [v1.0.0]",
        icon_url="https://media.discordapp.net/attachments/1365640845948354590/1380889378888487094/lune.png?ex=684584f3&is=68443373&hm=a93c967fe70134dbf6aea9b1cbb183f0f6d3e9587b15847eae9f5f5e5a24c330&=&format=webp&quality=lossless"
    )
    
    return embed