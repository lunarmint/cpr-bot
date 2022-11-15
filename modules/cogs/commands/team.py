import logging
from typing import Mapping, Any

import discord
from discord import app_commands
from discord.ext import commands

from modules.utils import database, embeds, helpers

log = logging.getLogger(__name__)


class TeamCog(commands.GroupCog, group_name="team"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="create", description="Create a new team.")
    async def create(self, interaction: discord.Interaction, name: str) -> None:
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.team_lock_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        team_collection = database.Database().get_collection("teams")
        name_lowercase = name.lower()
        team_query = {"name_lowercase": name_lowercase}
        team_result = team_collection.find_one(team_query)
        if team_result:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="A team with this name already exists.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        cursor = team_collection.find()
        for document in cursor:
            if interaction.user.id in document["members"]:
                embed = embeds.make_embed(
                    interaction=interaction,
                    color=discord.Color.red(),
                    thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                    title="Error",
                    description="You cannot create a new team because you are already in a team.",
                    timestamp=True,
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Create team",
            description=f"Create a new team with the name '{name}'?",
        )
        await interaction.response.send_message(embed=embed, view=CreateTeamConfirmButtons(name), ephemeral=True)

    @app_commands.command(name="join", description="Join a team.")
    async def join(self, interaction: discord.Interaction, team: str) -> None:
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.team_lock_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)

        team_collection = database.Database().get_collection("teams")
        new_team_query = {"name_lowercase": team.lower()}
        new_team_result = team_collection.find_one(new_team_query)

        if len(new_team_result["members"]) >= settings_result["team_size"]:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"The team '{new_team_result['name']}' is already full.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if new_team_result is None:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="The specified team name does not exist.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        current_team_query = {"members": interaction.user.id}
        current_team_result = team_collection.find_one(current_team_query)

        if current_team_result and current_team_result["name"] == new_team_result["name"]:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Cannot join a team that you are already in.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            interaction=interaction,
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
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.team_lock_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        team_collection = database.Database().get_collection("teams")
        team_query = {"members": interaction.user.id}
        team_result = team_collection.find_one(team_query)

        if team_result is None:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Cannot leave team because you are not in any teams yet.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description=f"You are currently in the team '{team_result['name']}'. Do you wish to leave?",
        )
        await interaction.response.send_message(
            embed=embed,
            view=LeaveTeamConfirmButtons(name=team_result["name"], channel_id=team_result["channel_id"]),
            ephemeral=True,
        )

    @app_commands.command(name="view", description="View a list of all teams.")
    async def view(self, interaction: discord.Interaction):
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.role_availability_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id}
        team_result = team_collection.find(team_query)

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/HcZHHdQ.png",
            title="Team list",
            footer="Your current team will be marked in bold.",
            timestamp=True,
        )

        if team_result is None:
            embed.description = "No teams were found. Please try again later!"
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        current_team_query = {"members": interaction.user.id}
        current_team_result = team_collection.find_one(current_team_query)

        teams = []
        for index, value in enumerate(team_result):
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

    @app_commands.command(name="rename", description="Rename a team.")
    async def rename(self, interaction: discord.Interaction):
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.team_lock_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.cooldown_check(interaction=interaction, command="team rename")
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        team_collection = database.Database().get_collection("teams")
        team_query = {"members": interaction.user.id}
        team_result = team_collection.find_one(team_query)
        if team_result is None:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Cannot update team name because you are not in any teams yet.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description=(
                "If you are not an instructor, updating your team name will set the command on a cooldown to prevent abuse. "
                "Your action will also be logged. Do you wish to continue?"
            ),
        )
        await interaction.response.send_message(
            embed=embed, view=RenameTeamConfirmButtons(team_result["name"]), ephemeral=True
        )

    @app_commands.command(name="lock", description="Lock all teams.")
    async def lock(self, interaction: discord.Interaction):
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)
        if settings_result["teams_locked"]:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/TwBPBrs.png",
                title="Error",
                description="Cannot lock teams because all teams are already locked.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/C3gWtnj.png",
            title="Warning",
            description=(
                "You are about to lock all teams. This will prevent students from creating, joining, "
                "leaving, or updating team name. Do you wish to continue?"
            ),
            footer="Use '/team unlock' if you wish to reverse this action at a later time.",
        )
        await interaction.response.send_message(embed=embed, view=LockTeamConfirmButtons(), ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock all teams.")
    async def unlock(self, interaction: discord.Interaction):
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)
        if not settings_result["teams_locked"]:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/OidhOOU.png",
                title="Error",
                description="Cannot unlock teams because all teams are already unlocked.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/HVA4eCw.png",
            title="Warning",
            description=(
                "You are about to unlock all teams. This will allow students to create, join, "
                "leave, and update team name. Do you wish to continue?"
            ),
            footer="Use '/team lock' if you wish to reverse this action at a later time.",
        )
        await interaction.response.send_message(embed=embed, view=UnlockTeamConfirmButtons(), ephemeral=True)


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
        }
        team_collection = database.Database().get_collection("teams")
        team_collection.insert_one(team_document)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"Team '{self.name}' was successfully created.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="create_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team creation request was canceled.",
            timestamp=True,
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
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"You were successfully added to the team '{self.new_team['name']}'.",
            timestamp=True,
        )
        return await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="join_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team join request was canceled.",
            timestamp=True,
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
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"You were successfully removed from the team '{self.name}'.",
            timestamp=True,
        )
        return await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="leave_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team leave request was canceled.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class RenameTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str) -> None:
        super().__init__(timeout=None)
        self.name = name

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="rename_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(RenameTeamModal(self.name))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="rename_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team rename request was canceled.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class RenameTeamModal(discord.ui.Modal, title="Rename Team"):
    def __init__(self, name: str) -> None:
        super().__init__(timeout=None)
        self.name = name
        self.new_name = discord.ui.TextInput(
            label="New Team Name:",
            default=self.name,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )

        self.add_item(self.new_name)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        new_name = self.new_name.value
        team_collection = database.Database().get_collection("teams")
        team_query = {"members": interaction.user.id}
        team_result = team_collection.find_one(team_query)

        new_name_lowercase = new_name.lower()
        new_value = {
            "$set": {
                "name": new_name,
                "name_lowercase": new_name_lowercase,
            }
        }
        team_collection.update_one(team_query, new_value)

        channel = interaction.guild.get_channel(team_result["channel_id"])
        formatted_name = new_name_lowercase.replace(" ", "-")
        await channel.edit(name=formatted_name)

        category = channel.category
        await category.edit(name=new_name)

        await helpers.set_cooldown(interaction=interaction, command="team rename")

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Team renamed",
            description=f"Successfully updated your team name from '{self.name}' to '{new_name}'.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error(error)
        embed = embeds.make_embed(
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/M1WQDzo.png",
            title="Error",
            description="Oops! Something went wrong. Please try again later!",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, ephemeral=True)


class LockTeamConfirmButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="lock_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        new_value = {"$set": {"teams_locked": True}}
        settings_collection.update_one(settings_query, new_value)

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id}
        team_results = team_collection.find(team_query)
        team_list = [f"{index + 1}. {value['name']}" for index, value in enumerate(team_results)]
        team_names = "\n".join(team_list)
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/6620Buy.png",
            title="Teams locked",
            description=f"Successfully locked the following teams:\n\n{team_names}",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="lock_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team lock request was canceled.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class UnlockTeamConfirmButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="unlock_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        new_value = {"$set": {"teams_locked": False}}
        settings_collection.update_one(settings_query, new_value)

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id}
        team_results = team_collection.find(team_query)
        team_list = [f"{index + 1}. {value['name']}" for index, value in enumerate(team_results)]
        team_names = "\n".join(team_list)
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/OaGi4Xz.png",
            title="Teams unlocked",
            description=f"Successfully unlocked the following teams:\n\n{team_names}",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="unlock_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team unlock request was canceled.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TeamCog(bot))
    log.info("Cog loaded: team")
