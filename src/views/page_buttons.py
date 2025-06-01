from nextcord import Interaction, Embed, ButtonStyle, TextInputStyle
from nextcord.ui import View, Item, Button, Modal, TextInput, button


class PageButtons(View):
    def __init__(self, bot, embeds: list[Embed], value: int = 0):
        super().__init__(timeout=None)
        self.bot = bot
        self.embeds = embeds
        
        self.value = value
        self.children: list[Button]
        self.backward, self.page, self.forward = self.children
        self.page.label = f"Page {self.value + 1}/{len(self.embeds)}"
        
    async def on_error(self, exception: Exception, item: Item, interaction: Interaction):
        await self.bot.handle_interaction_error(interaction, exception)


    @button(label = "Previous", style=ButtonStyle.blurple, disabled=True)
    async def backward_button(self, button: Button, interaction: Interaction):
        if self.value >= 1:
            self.value -= 1
        else:
            self.value = 0
        await self.update(interaction)
        
    @button(label="Page 0/X", style=ButtonStyle.grey)
    async def page_button(self, button: Button, interaction: Interaction):
        modal = JumpToPageModal(self, len(self.embeds))
        await interaction.response.send_modal(modal)
        await modal.wait()
        

    @button(label = "Next", style=ButtonStyle.blurple)
    async def forward_button(self, button: Button, interaction: Interaction):
        if self.value <= len(self.embeds) - 1:
            self.value += 1
        await self.update(interaction)


    async def update(self, interaction: Interaction):
                
        self.page.label = f"Page {self.value + 1}/{len(self.embeds)}"
        
        if self.value <= 0:
            self.disable(self.backward)
        else:
            self.enable(self.backward)
            
        if self.value >= len(self.embeds) - 1:
            self.disable(self.forward)
        else:
            self.enable(self.forward)
            
        await interaction.response.edit_message(embed=self.embeds[self.value], view=self)
    
    def disable(self, *buttons: Button):
        for b in buttons:
            b.disabled = True
        
    def enable(self, *buttons: Button):
        for b in buttons:
            b.disabled = False

class JumpToPageModal(Modal):
    
    def __init__(self, page_buttons: PageButtons, max_value: int):
        super().__init__("Jump to page", timeout=60)
        self.page_buttons = page_buttons
        self.max_value = max_value
        
        self.field = TextInput(
            label="Page number",
            style=TextInputStyle.short,
            placeholder="Enter a number between 1 and " + str(max_value),
            required=True,
            min_length=1,
            max_length=len(str(max_value)),
        )
        self.add_item(self.field)
        
    async def on_error(self, exception: Exception, interaction: Interaction):
        await self.page_buttons.bot.handle_interaction_error(interaction, exception)
        
    async def callback(self, interaction: Interaction):
        
        if self.field.value.isdigit():
            
            value = int(self.field.value) - 1
            if value >= 0 and value < self.max_value:
                
                self.stop()
                self.page_buttons.value = value
                await self.page_buttons.update(interaction)