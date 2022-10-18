import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules import config, database
from modules.utils import embeds

log = logging.getLogger(__name__)


class SettingsCog(commands.GroupCog, group_name="settings"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="help", description="Instructions on how to setup the bot.")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/NBaYHQG.png",
            title="Help",
            description="To setup the bot:\n\n"
                        "1. Use the command `/settings role` to setup the professor role.",
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))
    log.info("Cog loaded: settings")
