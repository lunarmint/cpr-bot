import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules.utils import embeds

log = logging.getLogger(__name__)


class AdminCog(commands.GroupCog, group_name="admin"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    sync = app_commands.Group(name="sync", description="Sync commands.")

    @sync.command(name="global", description="Sync commands globally.")
    async def sync_global(self, interaction: discord.Interaction) -> None:
        """
        Does not sync all commands globally, just the ones registered as global.
        """
        synced = await self.bot.tree.sync()
        embed = embeds.make_embed(
            description=f"Synced {len(synced)} commands globally.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @sync.command(name="guild", description="Sync commands in the current guild.")
    async def sync_guild(self, interaction: discord.Interaction) -> None:
        """
        Does not sync all of your commands to that guild, just the ones registered to that guild.
        """
        synced = await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            description=f"Synced {len(synced)} commands to the current guild.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @sync.command(name="copy", description="Copies all global app commands to current guild and syncs.")
    async def sync_global_to_guild(self, interaction: discord.Interaction) -> None:
        """
        This will copy the global list of commands in the tree into the list of commands for the specified guild.
        This is not permanent between bot restarts, and it doesn't impact the state of the commands (you still have to sync).
        """
        self.bot.tree.copy_global_to(guild=interaction.guild)
        synced = await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            description=f"Copied and synced {len(synced)} global app commands to the current guild.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @sync.command(name="remove", description="Clears all commands from the current guild target and syncs.")
    async def sync_remove(self, interaction: discord.Interaction) -> None:
        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            description=f"Cleared all commands from the current guild and synced.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
    log.info("Cog loaded: admin")
