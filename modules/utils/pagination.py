import logging

import discord
from discord.ext import menus

log = logging.getLogger(__name__)


class Paginate(discord.ui.View, menus.MenuPages):
    def __init__(self, source):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None

    async def start(self, ctx, *, channel=None, wait=False):
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        value = await super()._get_kwargs_from_page(page)
        if "view" not in value:
            value.update({"view": self})
        return value

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.primary)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_page(0)

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.primary)
    async def before_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(self.current_page - 1)

    @discord.ui.button(emoji="⏸", style=discord.ButtonStyle.primary)
    async def stop_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_checked_page(self.current_page + 1)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.primary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_page(self._source.get_max_pages() - 1)
