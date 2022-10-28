import logging
from typing import Mapping, Any, Optional

import arrow
import discord
from discord import app_commands
from discord.ext import commands

from modules import database
from modules.utils import embeds, helpers

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
        settings_result = await helpers.role_availability_check(interaction)
        if isinstance(settings_result, discord.Embed):
            return await interaction.response.send_message(embed=settings_result, ephemeral=True)

        team_collection = database.Database().get_collection("teams")
        new_team_query = {"name_lowercase": team.lower()}
        new_team_result = team_collection.find_one(new_team_query)

        if len(new_team_result["members"]) >= settings_result["team_size"]:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"The team '{new_team_result['name']}' is already full.",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

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
        current_team_result = team_collection.find_one(current_team_query)

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
            embed.description = (
                f"You are currently in the team '{current_team_result['name']}'. "
                f"Do you still wish to join the team '{new_team_result['name']}'?"
            )
        else:
            embed.description = f"You are about to join the team '{new_team_result['name']}'. Do you wish to continue?"

        return await interaction.response.send_message(
            embed=embed,
            view=JoinTeamConfirmButtons(current_team=current_team_result, new_team=new_team_result),
            ephemeral=True,
        )

    @app_commands.command(name="leave", description="Leave the current team.")
    async def leave(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("teams")
        query = {"members": interaction.user.id}
        result = collection.find_one(query)

        if result is None:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Cannot leave team because you are not in any teams yet.",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description=f"You are currently in the team '{result['name']}'. Do you wish to leave?",
        )
        await interaction.response.send_message(
            embed=embed, view=LeaveTeamConfirmButtons(name=result["name"], channel_id=result["channel_id"]), ephemeral=True
        )

    @app_commands.command(name="view", description="View a list of all teams.")
    async def view(self, interaction: discord.Interaction):
        collection = database.Database().get_collection("teams")
        teams_query = {"guild_id": interaction.guild_id}
        teams_result = collection.find(teams_query)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/HcZHHdQ.png",
            title="Team list",
            footer="Your current team will be marked in bold.",
        )

        if teams_result is None:
            embed.description = "No teams were found. Please try again later!"
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        current_team_query = {"members": interaction.user.id}
        current_team_result = collection.find_one(current_team_query)

        settings_result = await helpers.role_availability_check(interaction)
        if isinstance(settings_result, discord.Embed):
            return await interaction.response.send_message(embed=settings_result, ephemeral=True)

        teams = []
        for index, value in enumerate(teams_result):
            if len(value["members"]) >= settings_result["team_size"]:
                teams.append(f"{index + 1}. {value['name']} (full)")
            else:
                teams.append(f"{index + 1}. {value['name']}")

        if not current_team_result:
            embed.description = "\n".join(teams)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        for index, value in enumerate(teams):
            if current_team_result["name"] in value:
                teams[index] = f"**{value}**"

        embed.description = "\n".join(teams)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @staticmethod
    async def set_cooldown(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
        collection = database.Database().get_collection("settings")
        query = {"guild_id": interaction.guild_id}
        result = collection.find_one(query)
        if result is None:
            return app_commands.Cooldown(rate=1, per=86400)

        instructor_role = interaction.guild.get_role(result["role_id"])
        if instructor_role in interaction.user.roles:
            return None

        return app_commands.Cooldown(rate=1, per=86400)

    @app_commands.command(name="rename", description="Rename a team.")
    @app_commands.checks.dynamic_cooldown(set_cooldown)
    async def rename(self, interaction: discord.Interaction):
        collection = database.Database().get_collection("teams")
        query = {"members": interaction.user.id}
        result = collection.find_one(query)
        if result is None:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Cannot update team name because you are not in any teams yet.",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description=(
                f"If you are not an instructor, updating your team name will set the command on a 24 hours cooldown to prevent abuse. "
                f"Your action will also be logged. Do you wish to continue?"
            ),
        )
        await interaction.response.send_message(embed=embed, view=RenameTeamConfirmButtons(result["name"]), ephemeral=True)

    @rename.error
    async def rename_error(self, interaction: discord.Interaction, error: discord.HTTPException) -> None:
        log.error(error)
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            present = arrow.utcnow()
            future = present.shift(seconds=int(error.cooldown.get_retry_after()))
            duration_string = future.humanize(present, granularity=["hour", "minute", "second"])
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/40eDcIB.png",
                title="Error",
                description=f"Your team name update request is on cooldown. Try again {duration_string}.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class CreateTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str) -> None:
        super().__init__(timeout=None)
        self.name = name

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="create_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)

        instructor_role = interaction.guild.get_role(settings_result["role_id"])
        permission = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            instructor_role: discord.PermissionOverwrite(read_messages=True),
        }

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
            "locked": False,
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
            channel = interaction.guild.get_channel(self.current_team["channel_id"])
            await channel.set_permissions(interaction.user, overwrite=None)
            current_team_query = {"name_lowercase": self.current_team["name_lowercase"]}
            current_team_value = {"$pull": {"members": interaction.user.id}}
            collection.update_one(current_team_query, current_team_value)

        channel = interaction.guild.get_channel(self.new_team["channel_id"])
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


class LeaveTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str, channel_id: int) -> None:
        super().__init__(timeout=None)
        self.name = name
        self.channel_id = channel_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="leave_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("teams")
        query = {"members": interaction.user.id}
        value = {"$pull": {"members": interaction.user.id}}
        collection.update_one(query, value)

        channel = interaction.guild.get_channel(self.channel_id)
        await channel.set_permissions(interaction.user, overwrite=None)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"You were successfully removed from the team '{self.name}'.",
        )
        return await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="leave_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team leaving request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


class RenameTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str) -> None:
        super().__init__(timeout=None)
        self.name = name

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="rename_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        item = discord.ui.TextInput(
            label="New Team Name:",
            default=self.name,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        rename_team_modal = RenameTeamModal(self.name)
        await interaction.response.send_modal(rename_team_modal.add_item(item))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="rename_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team rename request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


class RenameTeamModal(discord.ui.Modal, title="Rename Team"):
    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = name

    async def on_submit(self, interaction: discord.Interaction) -> None:
        new_name = self.children[0].value
        collection = database.Database().get_collection("teams")
        query = {"members": interaction.user.id}
        result = collection.find_one(query)

        new_name_lowercase = new_name.lower()
        new_value = {
            "$set": {
                "name": new_name,
                "name_lowercase": new_name_lowercase,
            }
        }
        collection.update_one(query, new_value)

        channel = interaction.guild.get_channel(result["channel_id"])
        formatted_name = new_name_lowercase.replace(" ", "-")
        await channel.edit(name=formatted_name)

        category = channel.category
        await category.edit(name=new_name)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Team renamed",
            description=f"Successfully updated your team name from '{self.name}' to '{new_name}'.",
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error(error)
        embed = embeds.make_embed(
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/M1WQDzo.png",
            title="Error",
            description="Oops! Something went wrong. Please try again later!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))
    log.info("Cog loaded: team")
