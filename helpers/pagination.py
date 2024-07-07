import discord
from typing import Callable, Optional
import time


class Pagination(discord.ui.View):
    def __init__(
        self, interaction: discord.Interaction, get_page: Callable, timeout: int = 100
    ):
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.get_page = get_page
        self.total_pages: Optional[int] = None
        self.index = 1
        self.timeout_duration = timeout

    async def navigate(self):
        emb, self.total_pages = await self.get_page(self.index)
        timeout_timestamp = int(time.time()) + self.timeout_duration
        emb.add_field(
            name="*Command Timeout:*",
            value=f"*<t:{timeout_timestamp}:R>*",
            inline=False,
        )
        if self.total_pages > 1:
            self.update_buttons()
            await self.interaction.response.send_message(embed=emb, view=self)
        else:
            await self.interaction.response.send_message(embed=emb)

    async def edit_page(self, interaction: discord.Interaction):
        emb, self.total_pages = await self.get_page(self.index)
        timeout_timestamp = int(time.time()) + self.timeout_duration + 1
        emb.add_field(name="Timeout", value=f"<t:{timeout_timestamp}:R>", inline=False)
        self.update_buttons()
        await interaction.response.edit_message(embed=emb, view=self)

    def update_buttons(self):
        self.children[0].disabled = self.index == 1
        self.children[1].disabled = self.index == 1
        self.children[2].disabled = self.index == self.total_pages
        self.children[3].disabled = self.index == self.total_pages

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.blurple)
    async def first(self, interaction: discord.Interaction, button: discord.Button):
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.Button):
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.Button):
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.blurple)
    async def last(self, interaction: discord.Interaction, button: discord.Button):
        self.index = self.total_pages
        await self.edit_page(interaction)

    async def on_timeout(self):
        # Edit the message on timeout to indicate it has timed out
        try:
            timeout_timestamp = int(time.time())
            emb = discord.Embed(description=f"This interaction has timed out.")
            message = await self.interaction.original_response()
            await message.edit(embed=emb, view=None)
        except discord.NotFound:
            pass

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1
