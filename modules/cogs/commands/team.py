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
        collection = database.Database().get_collection("teams")
        name_lowercase = name.lower()
        query = {"name_lowercase": name_lowercase}
        result = collection.find_one(query)
        if result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="A team with this name already exists.",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        cursor = collection.find()
        for document in cursor:
            if interaction.user.id in document["members"]:
                embed = embeds.make_embed(
                    ctx=interaction,
                    author=True,
                    color=discord.Color.red(),
                    thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                    title="Error",
                    description="You cannot create a new team because you are already in a team.",
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Create team",
            description=f"Would you like to create a team with the name '{name}'?",
        )
        await interaction.response.send_message(embed=embed, view=CreateTeamConfirmButtons(name), ephemeral=True)

    @app_commands.command(name="join", description="Join a team.")
    async def join(self, interaction: discord.Interaction, team: str) -> None:
        await interaction.response.defer(ephemeral=True)

        teams_collection = database.Database().get_collection("teams")
        team_query = {"name_lowercase": team.lower()}
        team_result = teams_collection.find_one(team_query)
        if team_result is None:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="The specified team name does not exist.",
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
                    description="You are already in a team.",
                )
                return await interaction.followup.send(embed=embed)

        new_value = {"$push": {"members": interaction.user.id}}
        teams_collection.update_one(team_query, new_value)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"You were successfully added to team '{team_result['name']}'.",
        )
        await interaction.followup.send(embed=embed)


class CreateTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str) -> None:
        super().__init__(timeout=None)
        self.name = name

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        teams_collection = database.Database().get_collection("teams")
        name_lowercase = self.name.lower()

        permission = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=False,
                manage_channels=False,
                manage_permissions=False,
                manage_messages=False,
            ),
        }

        formatted_name = name_lowercase.replace(" ", "-")
        team_category = await interaction.guild.create_category(name=self.name)
        team_channel = await interaction.guild.create_text_channel(
            name=formatted_name, category=team_category, overwrites=permission
        )

        team_document = {
            "guild_id": interaction.guild_id,
            "channel_id": team_channel.id,
            "name": self.name,
            "name_lowercase": name_lowercase,
            "members": [],
        }
        teams_collection.insert_one(team_document)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"Team '{self.name}' was successfully created.",
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team creation request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))
    log.info("Cog loaded: team")
