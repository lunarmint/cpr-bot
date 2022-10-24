import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules import database
from modules.utils import embeds

log = logging.getLogger(__name__)


class TeamCog(commands.GroupCog, group_name="team"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="create", description="Create a new team.")
    async def create(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer(ephemeral=True)

        teams_collection = database.Database().get_collection("teams")
        team_query = {"name": name}
        team_result = teams_collection.find_one(team_query)
        if team_result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"A team with this name already exist.",
            )
            return await interaction.followup.send(embed=embed)

        cursor = teams_collection.find()
        for document in cursor:
            if interaction.user.id in document["members"]:
                embed = embeds.make_embed(
                    ctx=interaction,
                    author=True,
                    color=discord.Color.red(),
                    thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                    title="Error",
                    description=f"You are already in a team.",
                )
                return await interaction.followup.send(embed=embed)

        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)
        if not settings_result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"No instructor role was found. Use the command `/settings role` to assign a role with the instructor permission.",
            )
            return await interaction.followup.send(embed=embed)

        permission = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                manage_channels=False,
                manage_permissions=False,
                manage_messages=False,
            ),
        }
        formatted_name = name.replace(" ", "-").lower()
        team_category = await interaction.guild.create_category(name=name)
        team_channel = await interaction.guild.create_text_channel(
            name=formatted_name, category=team_category, overwrites=permission
        )

        team_document = {
            "name": name,
            "channel_id": team_channel.id,
            "members": [],
        }
        teams_collection.insert_one(team_document)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"Team {team_channel.mention} was successfully created.",
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))
    log.info("Cog loaded: team")
