import logging
from typing import Mapping, Any

import discord
from discord import app_commands
from discord.ext import commands

from modules import database
from modules.utils import embeds, helpers

log = logging.getLogger(__name__)


class AssignmentCog(commands.GroupCog, group_name="assignment"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="create", description="Create a new assignment.")
    async def create(self, interaction: discord.Interaction, name: str) -> None:
        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AssignmentCog(bot))
    log.info("Cog loaded: assignment")
