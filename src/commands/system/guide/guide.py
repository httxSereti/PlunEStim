import time
import nextcord

from nextcord import Interaction, slash_command, SlashOption, Embed
from nextcord.ext.commands import Cog

from views import *

PAGES_AVAILABLE = {
    'Introduction [Page 1]': 0,
    'Estim infos [Page 2]': 1,
    'Configuration [Page 3]': 2,
    'Units Settings [Page 4]': 3,
    'Events & Trigger Rules [Page 5]': 4,
    'Programs [Page 6]': 5,
    'Profile [Page 7]': 6,
    'Sensors [Page 8]': 7,
}

class GuideCommand(Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        description="The guide about PlunEStim Companion"
    )
    async def guide(
        self,
        interaction: Interaction,
        page: int = SlashOption(
            name="page",
            description="The page you want to view.",
            required=False,
            choices=PAGES_AVAILABLE
        )
    ):
        if page is None:
            page = 0
            
        embeds = [
            Embed(
                title=":sparkles: Introduction",
                description="\n".join([
                    "### **PlunEStim** is a Software running on Subject device, created by **@httx.sereti**.",
                    "Allowing Users to interact with Subject e-stim units (2B E-Stim Box) through Discord, Events or from Subject actions.",
                    "## :sparkles: Main features",
                    "- Stimulate Subject with pre-configured **Profile** (Soft Edging, Spank, Pinch, Squeeze...)",
                    "- Interact with Subject using Cumulative actions or by adding actions in waiting queue",
                    "- Highly customisable **Profile**",
                    "- Quick commands to manage Level/Units/Modes",
                    "- Events can be monitored with 'Trigger Rules'",
                    "- Configure and choose Actions to apply when a 'Trigger Rules' is fired (Apply Profile, Increase Levels..)",
                    "- Support 'RAMP' Mode (Increase intensity by x2, x3, x4, x8 per steps)",
                    "- Support 'Training' Mode (Increase intensity by x2, x4 while ensure Subject can handle it)",
                    "- Manage 2B EStim **Advanced Settings** (Timers, Power Level, Waveforms)",
                    # "_ _",
                    "## :sparkles: Integrations",
                    "- Chaster Events Integration (Lock, Pillory, Tasks, WOF, Votes)",
                    "- Discord Events Integration (Use banned words, talk when muffled, enforce good speech behaviors)",
                    "- Noises Sensor Integration (too much noises will triggers **Events**)",
                    "- Motion Sensor Integration (movements, position, leave area will triggers **Events**)",
                ]),
                color=nextcord.Color.purple()
            ),
            Embed(
                title=":sparkles: Estim infos",
                description="\n".join([
                    "-# Electrostimulation 'Estim', tickle, squeeze, pinch, hurt, give pleasure, pain and lot of feelings depending settings...",
                    "_ _",
                    "Allowing Users to interact with Subject e-stim units (2B E-Stim Box) through Discord, Events or from Subject actions.",
                    "## :sparkles: WIP",
                    "sdakdla"
                ]),
                color=nextcord.Color.purple()
            ),
            Embed(
                title=":sparkles: Configuration",
                description="\n".join([
                    "PlunEStim is a Software running on Subject device, created by **@httx.sereti**.",
                    "_ _",
                    "Allowing Users to interact with Subject e-stim units (2B E-Stim Box) through Discord, Events or from Subject actions.",
                    "## :sparkles: sad",
                    "sdakdla"
                ]),
            ),
            Embed(
                title=":sparkles: Units",
                description="4"
            ),
            Embed(
                title=":sparkles: Trigger Rules and Events",
                
                description="\n".join([
                    "### **Trigger Rules**",
                    "*Create one or many rules to monitor Events, applying one or many actions when rule is triggered*",
                    "## :sparkles: Commands",
                    "- /rules events monitor [eventName] [actionId] [description]",
                    "- Interact with Subject using Cumulative actions or by adding actions in waiting queue",
                ]),
            ).set_image("https://mermaid.ink/img/pako:eNqFk8FygjAQhl-F2TNRRNDAoYe219566nBJyapMIWFCGG0Z371JMGpRpzmR_f79dzchA5SSI-RQiE0t9-WOKR28PxciMGvPKh0Q8tlrLUXQKuw65IQ8OUC4FPhHt1dSbINRfVa54EV2Enl8Baydi7NSE1frEdzJmj9iCltkxnbkZyvHOZZVV8krNqodNCqyYVV9F162pJS90FPRGL1p4qHothM70wSN0O-Hri9LO8k8sG0e_9I7I9ygk4E39ur_Lvii9h2Q8UznrufG_D6TCmbeGlmH9zJPh-qzXB2BB32j9SbBRHZ18TZgcCVKhQ0KjXzy80EIW1VxyLXqMYQGVcPsFgbrUoDembwCcvPJmfoqzCM4mpyWiQ8pG5-mZL_d-U3fcqbxtWJbxYxiw-rOSlBwVC_2fiFf0th5QD7AAfI4S2fpKkpoSpcZTZbrNIRvyNNotqDrhNI0TbOIxscQflzRaGbCmVk0XkRJtF6tQ0BeaanexpfqHuzxF_bKNY4?type=png"),
            Embed(
                title=":sparkles: Programs",
                description="6"
            ),
            Embed(
                title=":sparkles: Profile",
                description="7"
            ),
            Embed(
                title=":sparkles: Sensors",
                description="\n".join([
                    "### **Sensors**",
                    "*Your eyes and ears, detect sounds, movements and position of Subject in real time*",
                    "# :sparkles: Commands",
                    "- /sensors display",
                    "-# Display Sensors configurations and status.",
                    "_ _",
                    "- /sensors alarm [sensorName] [enable|disable] (delay)",
                    "-# Enable or disable Alarm of a desired Sensor with delay or now.",
                    "_ _",
                    "- /sensors set [settingName] [sensorName] [value]",
                    "-# Update configuration of a desired Sensor; trigger level, delay to fire, cooldown to fire",
                ]),
            ),
        ]
        
        # Initialize the view
        view = PageButtons(self.bot, embeds, page)
        
        # Send a message with the first embed and attach the view
        await interaction.send(
            embed=embeds[page],
            view=view
        )

def setup(bot):
    bot.add_cog(GuideCommand(bot))