import time
import nextcord

from nextcord import Interaction, slash_command, SlashOption, Embed
from nextcord.ext.commands import Cog

from views import *

PAGES_AVAILABLE = {
    'Basics [Page 1]': 0,
    'E-Stim & 2B quick tour [Page 2]': 1,
    'Programs [Page 3]': 2,
    'Units [Page 4]': 3,
    'Sensors [Page 5]': 4,
    'Programs [Page 6]': 5,
    'Profile [Page 7]': 6,
}

class GuideCommand(Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @slash_command(
        description="Learn about PlunEStim, features, how to use, tips & tricks.."
    )
    async def guide(
        self,
        interaction: Interaction,
        page: int = SlashOption(
            name="page",
            description="The guide page you want to view.",
            required=False,
            choices=PAGES_AVAILABLE
        )
    ):
        if page is None:
            page = 0
            
        embeds = [
            Embed(
                title=":sparkles: Welcome to PlunEStim v1.0.0",
                description=
                """
                    PlunEStim is a Software running on Subject device, created by **@httx.sereti**.
                    _ _
                    Allowing Users to interact with Subject e-stim units (2B E-Stim Box) through Discord, Events or from Subject actions.
                    \r## :sparkles: Features
                    \r- Stimulate Subject with automatised programs (People like to spank you and sometimes edge your sensible parts)
                    \r- Use Profile to apply desired settings to Subject for a desired duration
                    \r- Notify Subject for stimulations incoming using Sounds
                    \r- Prevent Subject to make too much noises using Punishments
                    \r- Prevent Subject to move or escape an area using Punishments
                    \r- Edge Subject relentlessly until Subject is unlocked
                """,
                color=nextcord.Color.purple()
            ),
            Embed(
                title=":sparkles: EStim quick guide",
                description=
                """
                    *Skip this page if you're advanced into E-Stim and have a 2B E-Stim Unit at home or used one*
                    ## E-Stim
                    *that thing is awesome and can do lot of feelings.*
                    If you're using a DG Lab :3
                    ## 2B E-Stim Unit
                    *powerfull, easy, lot of settings, but bit old and expansive*
                """,
                color=nextcord.Color.purple()
            ),
            Embed(
                title="asdasd",
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
                title=":sparkles: Sensors",
                description="5"
            ),
            Embed(
                title=":sparkles: Programs",
                description="6"
            ),
            Embed(
                title=":sparkles: Profile",
                description="7"
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