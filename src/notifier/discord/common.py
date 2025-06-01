from discord_webhook import DiscordWebhook, DiscordEmbed

def NotifyPluneStartSettings(
    webhookURL: str,
    sensorsSettings: list
):
    try:
        webhook = DiscordWebhook(
            url=webhookURL,
            username='Plune',
            avatar_url='https://media.discordapp.net/attachments/1365640845948354590/1365641164123803688/plune-pdp.png?ex=681b3af1&is=6819e971&hm=1ea85dd67f3fb7f8049e05839498fd6b5a230a0c9e2fd2abe4ede172dacc655b&=&format=webp&quality=lossless&width=350&height=350'
        )
        
        for sensorName in sensorsSettings.keys():
            sensor = sensorsSettings[sensorName]
            
            embed = DiscordEmbed(
                timestamp="now",
                color=7484927
            )

            embed.set_author(
                name=f"✨ Sensors • ({sensorName})",
                url="https://plune.app"
            )
            
            embed.add_embed_field(name='✿ • Status', value=':black_medium_square::black_medium_square::green_square::black_medium_square::black_medium_square:', inline=True)
            embed.add_embed_field(name='✿ • Enabled', value=':black_medium_square::black_medium_square::green_square::black_medium_square::black_medium_square:', inline=True)
            embed.add_embed_field(name='✿ • Notify', value=':black_medium_square::black_medium_square::green_square::black_medium_square::black_medium_square:', inline=True)
            
            if (sensor['sensor_type'] == "motion"):
                motionTextComponents = "```"
                motionTextComponents += f"Current Position: {sensor['current_position']}"
                motionTextComponents += "```"
                
                embed.add_embed_field(name='✿ • Position'.format(sensorName), value=motionTextComponents, inline=False)
                embed.add_embed_field(name='✿ • Move'.format(sensorName), value=motionTextComponents, inline=False)
                
            if (sensor['sensor_type'] == "sound"):
                text = "```"
                text += f"Current sound level: {sensor['current_sound']}\n"
                text += f"Alarm at level: {sensor['sound_alarm_level']}\n"
                text += f"Sound duration before Alarm: {sensor['sound_delay_on']}\n"
                text += f"Sound duration cooldown: {sensor['sound_delay_off']}\n"
                text += "```"
                
                embed.add_embed_field(name='✿ • Move'.format(sensorName), value=text, inline=False)
                
            embed.set_footer(text="@plune.app")
            embed.set_timestamp()

            webhook.add_embed(embed)
        webhook.execute()
    except Exception as error:
        print(error)