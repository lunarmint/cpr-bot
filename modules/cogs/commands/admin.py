import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules import config
from modules.utils import embeds

log = logging.getLogger(__name__)


class AdminCog(commands.GroupCog, group_name="sync"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="global", description="Sync commands globally.")
    async def sync_global(self, interaction: discord.Interaction) -> None:
        synced = await self.bot.tree.sync()
        embed = embeds.make_embed(
            description=f"Synced {len(synced)} commands globally.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="guild", description="Sync commands in the current guild.")
    async def sync_guild(self, interaction: discord.Interaction) -> None:
        synced = await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            description=f"Synced {len(synced)} commands to the current guild.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="copy", description="Copies all global app commands to current guild and syncs.")
    async def sync_global_to_guild(self, interaction: discord.Interaction) -> None:
        self.bot.tree.copy_global_to(guild=interaction.guild)
        synced = await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            description=f"Copied and synced {len(synced)} global app commands to the current guild.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="remove", description="Clears all commands from the current guild target and syncs.")
    async def sync_remove(self, interaction: discord.Interaction) -> None:
        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            description=f"Cleared all commands from the current guild and synced.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot), guild=discord.Object(id=config["guild_id"]))
    log.info("Command loaded: sync global")
    log.info("Command loaded: sync guild")
    log.info("Command loaded: sync copy")
    log.info("Command loaded: sync remove")
