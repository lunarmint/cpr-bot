import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules.utils import embeds, helpers

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
        await interaction.response.defer(ephemeral=True)

        embed = await helpers.bot_owner_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.followup.send(embed=embed)

        synced = await self.bot.tree.sync()
        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"Synced {len(synced)} commands globally.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed)

    @sync.command(name="guild", description="Sync commands in the current guild.")
    async def sync_guild(self, interaction: discord.Interaction) -> None:
        """
        Does not sync all of your commands to that guild, just the ones registered to that guild.
        """
        await interaction.response.defer(ephemeral=True)

        embed = await helpers.bot_owner_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.followup.send(embed=embed)

        synced = await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"Synced {len(synced)} commands to the current guild.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed)

    @sync.command(name="copy", description="Copies all global app commands to current guild and syncs.")
    async def sync_global_to_guild(self, interaction: discord.Interaction) -> None:
        """
        This will copy the global list of commands in the tree into the list of commands for the specified guild.
        This is not permanent between bot restarts, and it doesn't impact the state of the commands (you still have to sync).
        """
        await interaction.response.defer(ephemeral=True)

        embed = await helpers.bot_owner_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.followup.send(embed=embed)

        self.bot.tree.copy_global_to(guild=interaction.guild)
        synced = await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"Copied and synced {len(synced)} global app commands to the current guild.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed)

    @sync.command(name="remove", description="Clears all commands from the current guild target and syncs.")
    async def sync_remove(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        embed = await helpers.bot_owner_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.followup.send(embed=embed)

        self.bot.tree.clear_commands(guild=interaction.guild)
        await self.bot.tree.sync(guild=interaction.guild)
        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description="Cleared all commands from the current guild and synced.",
            color=discord.Color.green(),
        )
        await interaction.followup.send(embed=embed)

    @sync_global.error
    @sync_guild.error
    @sync_global_to_guild.error
    @sync_remove.error
    async def sync_error(self, interaction: discord.Interaction, error: discord.HTTPException) -> None:
        log.error(error)
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"Manage server permission is required to use this command.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
    log.info("Cog loaded: admin")
