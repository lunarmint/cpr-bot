import logging
from typing import Mapping, Any

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
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Create team",
            description=f"Create a new team with the name '{name}'?",
        )
        await interaction.response.send_message(embed=embed, view=CreateTeamConfirmButtons(name), ephemeral=True)

    @app_commands.command(name="join", description="Join a team.")
    async def join(self, interaction: discord.Interaction, team: str) -> None:
        collection = database.Database().get_collection("teams")
        new_team_query = {"name_lowercase": team.lower()}
        new_team_result = collection.find_one(new_team_query)
        if new_team_result is None:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="The specified team name does not exist.",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        current_team_query = {"members": interaction.user.id}
        current_team_result = collection.find_one(current_team_query)

        if current_team_result and current_team_result["name"] == new_team_result["name"]:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Cannot join a team that you are already in.",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
        )

        if current_team_result:
            embed.description = f"You are currently in the team '{current_team_result['name']}'. Do you still wish to join the team '{new_team_result['name']}'?"
        else:
            embed.description = f"You are about to join the team '{new_team_result['name']}'. Do you wish to continue?"

        return await interaction.response.send_message(
            embed=embed,
            view=JoinTeamConfirmButtons(current_team=current_team_result, new_team=new_team_result),
            ephemeral=True,
        )


class CreateTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str) -> None:
        super().__init__(timeout=None)
        self.name = name

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="create_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)

        permission = {interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False)}

        if not any(role.id == settings_result["role_id"] for role in interaction.user.roles):
            permission[interaction.user] = discord.PermissionOverwrite(read_messages=True)

        name_lowercase = self.name.lower()
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
        teams_collection = database.Database().get_collection("teams")
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

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="create_team_cancel")
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


class JoinTeamConfirmButtons(discord.ui.View):
    def __init__(self, current_team: Mapping[str, Any], new_team: Mapping[str, Any]) -> None:
        super().__init__(timeout=None)
        self.current_team = current_team
        self.new_team = new_team

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="join_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("teams")

        if self.current_team:
            channel = discord.utils.get(interaction.guild.channels, id=self.current_team["channel_id"])
            await channel.set_permissions(interaction.user, overwrite=None)
            current_team_query = {"name_lowercase": self.current_team["name_lowercase"]}
            current_team_value = {"$pull": {"members": interaction.user.id}}
            collection.update_one(current_team_query, current_team_value)

        channel = discord.utils.get(interaction.guild.channels, id=self.new_team["channel_id"])
        await channel.set_permissions(interaction.user, read_messages=True)

        new_team_query = {"name_lowercase": self.new_team["name_lowercase"]}
        new_team_value = {"$push": {"members": interaction.user.id}}
        collection.update_one(new_team_query, new_team_value)
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"You were successfully added to the team '{self.new_team['name']}'.",
        )
        return await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="join_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team join request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))
    log.info("Cog loaded: team")
