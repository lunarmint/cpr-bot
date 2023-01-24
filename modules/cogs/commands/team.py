import logging

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
        team_query = {"guild_id": interaction.guild_id, "name": name}
        team_result = team_collection.find_one(team_query)
        if team_result and team_result["name"] in (name, name.lower()):
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="A team with this name already exists.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        results = team_collection.find()
        for document in results:
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

    @staticmethod
    async def join_view(interaction: discord.Interaction) -> tuple[discord.Embed, discord.ui.View]:
        view = discord.ui.View()

        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return embed, view

        embed = await helpers.team_lock_check(interaction)
        if isinstance(embed, discord.Embed):
            return embed, view

        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)

        team_collection = database.Database().get_collection("teams")

        current_team_query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
        current_team_result = team_collection.find_one(current_team_query)

        new_team_query = {"guild_id": interaction.guild_id}
        new_team_results = team_collection.find(new_team_query)

        options = []
        for result in new_team_results:
            if current_team_result and current_team_result["name"] == result["name"]:
                continue

            if len(result["members"]) < settings_result["team_size"]:
                options.append(discord.SelectOption(label=result["name"]))

        if not options:
            command = await helpers.get_command(interaction=interaction, command="team", subcommand_group="view")
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"No teams are available to join at the moment. Use {command.mention} to view available teams.",
                timestamp=True,
            )
            return embed, view

        view.add_item(
            JoinTeamDropdown(options=options, current_team=current_team_result["name"] if current_team_result else None)
        )

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/HcZHHdQ.png",
            title="Join team",
            description="Use the dropdown below to join a currently available team.",
            timestamp=True,
        )

        return embed, view

    @app_commands.command(name="join", description="Join a team.")
    async def join(self, interaction: discord.Interaction) -> None:
        embed, view = await self.join_view(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="leave", description="Leave the current team.")
    async def leave(self, interaction: discord.Interaction) -> None:
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = await helpers.team_lock_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
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

        current_team_query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
        current_team_result = team_collection.find_one(current_team_query)

        check = await helpers.instructor_check(interaction)
        instructor = False if isinstance(check, discord.Embed) else True

        teams = []
        for index, value in enumerate(team_result):
            if instructor:
                teams.append(f"{index + 1}. {value['name']} ({len(value['members'])}/{settings_result['team_size']})")
                continue

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

        collection = database.Database().get_collection("teams")
        query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
        result = collection.find_one(query)
        if result is None:
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
        await interaction.response.send_message(embed=embed, view=RenameTeamConfirmButtons(result["name"]), ephemeral=True)

    @staticmethod
    async def edit_view(interaction: discord.Interaction) -> tuple[discord.Embed, discord.ui.View]:
        view = discord.ui.View()
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return embed, view

        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            command = await helpers.get_command(interaction=interaction, command="team", subcommand_group="rename")
            embed.description += f"\nTo update your team name, please use {command.mention} instead."
            return embed, view

        collection = database.Database().get_collection("teams")
        query = {"guild_id": interaction.guild_id}
        options = [discord.SelectOption(label=result["name"]) for result in collection.find(query)]

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/HcZHHdQ.png",
            title="Edit a team",
            timestamp=True,
        )

        if not options:
            embed.description = "It seems that no teams are available at the moment. Please check back later!"
            return embed, view

        embed.description = "Select a team to edit using the dropdown below."
        view = discord.ui.View()
        view.add_item(EditTeamDropdown(options))
        return embed, view

    @app_commands.command(name="edit", description="Edit a team.")
    async def edit(self, interaction: discord.Interaction):
        embed, view = await self.edit_view(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @staticmethod
    async def remove_view(interaction: discord.Interaction) -> tuple[discord.Embed, discord.ui.View]:
        view = discord.ui.View()
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return embed, view

        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return embed, view

        collection = database.Database().get_collection("teams")
        query = {"guild_id": interaction.guild_id}
        options = [discord.SelectOption(label=result["name"]) for result in collection.find(query)]

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/HcZHHdQ.png",
            title="Remove a team",
            timestamp=True,
        )

        if not options:
            embed.description = "It seems that no teams are available at the moment. Please check back later!"
            return embed, view

        embed.description = "Select a team to remove using the dropdown below."
        view = discord.ui.View()
        view.add_item(RemoveTeamDropdown(options))
        return embed, view

    @app_commands.command(name="remove", description="Remove a team.")
    async def remove(self, interaction: discord.Interaction):
        embed, view = await self.remove_view(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
        super().__init__()
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
            interaction.client.user: discord.PermissionOverwrite(read_messages=True),
        }

        embed = await helpers.instructor_check(interaction)
        instructor = False if isinstance(embed, discord.Embed) else True
        if not instructor:
            permission[interaction.user] = discord.PermissionOverwrite(read_messages=True)

        category = await interaction.guild.create_category(name=self.name, overwrites=permission)
        channel = await interaction.guild.create_text_channel(name=self.name, category=category)
        voice_channel = await interaction.guild.create_voice_channel(
            name=self.name, category=category, bitrate=96000, overwrites=permission
        )

        team_document = {
            "guild_id": interaction.guild_id,
            "channel_id": channel.id,
            "voice_channel_id": voice_channel.id,
            "name": self.name,
            "members": [] if instructor else [interaction.user.id],
            "peer_review": [],
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


class JoinTeamDropdown(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption], current_team: str = None) -> None:
        super().__init__()
        self.options = options
        self.current_team = current_team

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
        )

        if self.current_team is None:
            embed.description = f"You are about to join the team '{self.values[0]}'. Do you wish to continue?"
        else:
            embed.description = (
                f"You are currently in the team '{self.current_team}'. "
                f"Do you wish to leave and join the team '{self.values[0]}'?"
            )

        await interaction.response.edit_message(
            embed=embed,
            view=JoinTeamConfirmButtons(current_team=self.current_team, new_team=self.values[0]),
        )


class JoinTeamConfirmButtons(discord.ui.View):
    def __init__(self, current_team: str, new_team: str) -> None:
        super().__init__()
        self.current_team = current_team
        self.new_team = new_team

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="join_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("teams")

        current_team_query = {"guild_id": interaction.guild_id, "name": self.current_team}
        current_team_result = collection.find_one(current_team_query)

        new_team_query = {"guild_id": interaction.guild_id, "name": self.new_team}
        new_team_result = collection.find_one(new_team_query)

        if current_team_result:
            channel = interaction.guild.get_channel(current_team_result["channel_id"])
            await channel.category.set_permissions(target=interaction.user, overwrite=None)

            current_team_query = {"guild_id": interaction.guild_id, "name": current_team_result["name"]}
            current_team_value = {"$pull": {"members": interaction.user.id}}
            collection.update_one(current_team_query, current_team_value)

        channel = interaction.guild.get_channel(new_team_result["channel_id"])
        await channel.category.set_permissions(target=interaction.user, read_messages=True)

        new_team_value = {"$push": {"members": interaction.user.id}}
        collection.update_one(new_team_query, new_team_value)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"You were successfully added to the team '{self.new_team}'.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(JoinTeamBackButton())
        await interaction.response.edit_message(embed=embed, view=view)

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

        view = discord.ui.View()
        view.add_item(JoinTeamBackButton())
        await interaction.response.edit_message(embed=embed, view=view)


class JoinTeamBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Go Back"
        self.style = discord.ButtonStyle.gray
        self.custom_id = "join_team_back"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed, view = await TeamCog.join_view(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class LeaveTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str, channel_id: int) -> None:
        super().__init__()
        self.name = name
        self.channel_id = channel_id

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="leave_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("teams")
        query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
        value = {"$pull": {"members": interaction.user.id}}
        collection.update_one(query, value)

        channel = interaction.guild.get_channel(self.channel_id)
        await channel.category.set_permissions(target=interaction.user, overwrite=None)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description=f"You were successfully removed from the team '{self.name}'.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)

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
        super().__init__()
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
        super().__init__()
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
        team_query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
        team_result = team_collection.find_one(team_query)

        new_value = {"$set": {"name": new_name}}
        team_collection.update_one(team_query, new_value)

        team_query = {"guild_id": interaction.guild_id, "peer_review": self.name}
        new_value = {"$set": {"peer_review.$": new_name}}
        team_collection.update_many(team_query, new_value)

        channel = interaction.guild.get_channel(team_result["channel_id"])
        await channel.edit(name=new_name)

        voice_channel = interaction.guild.get_channel(team_result["voice_channel_id"])
        await voice_channel.edit(name=new_name)

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


class EditTeamDropdown(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__()
        self.options = options

    async def callback(self, interaction: discord.Interaction) -> None:
        edit_team_modal = EditTeamModal(self.values[0])
        edit_team_modal.title = f"{self.values[0]}"
        await interaction.response.send_modal(edit_team_modal)


class EditTeamModal(discord.ui.Modal, title=None):
    def __init__(self, name: str) -> None:
        super().__init__()
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
        team_query = {"guild_id": interaction.guild_id, "name": self.name}
        team_result = team_collection.find_one(team_query)

        new_value = {"$set": {"name": new_name}}
        team_collection.update_one(team_query, new_value)

        team_query = {"guild_id": interaction.guild_id, "peer_review": self.name}
        new_value = {"$set": {"peer_review.$": new_name}}
        team_collection.update_many(team_query, new_value)

        channel = interaction.guild.get_channel(team_result["channel_id"])
        await channel.edit(name=new_name)

        voice_channel = interaction.guild.get_channel(team_result["voice_channel_id"])
        await voice_channel.edit(name=new_name)

        category = channel.category
        await category.edit(name=new_name)

        await helpers.set_cooldown(interaction=interaction, command="team rename")

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Team renamed",
            description=f"Successfully updated team name from '{self.name}' to '{new_name}'.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(RemoveTeamBackButton())
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error(error)
        embed = embeds.make_embed(
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/M1WQDzo.png",
            title="Error",
            description="Oops! Something went wrong. Please try again later!",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(RemoveTeamBackButton())
        await interaction.response.edit_message(embed=embed, view=view)


class EditTeamBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Go Back"
        self.style = discord.ButtonStyle.gray
        self.custom_id = "edit_team_back"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed, view = await TeamCog.edit_view(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class RemoveTeamDropdown(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__()
        self.options = options

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description=f"You are about to remove the team '{self.values[0]}'. This action is **irreversible**. Do you wish to continue?",
        )
        await interaction.response.edit_message(embed=embed, view=RemoveTeamConfirmButtons(self.values[0]))


class RemoveTeamConfirmButtons(discord.ui.View):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="remove_team_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("teams")
        query = {"guild_id": interaction.guild_id, "name": self.name}
        result = collection.find_one(query)

        channel = interaction.guild.get_channel(result["channel_id"])
        for channel in channel.category.channels:
            await channel.delete()

        await channel.category.delete()
        collection.delete_one(query)

        query = {"guild_id": interaction.guild_id}
        new_value = {"$pull": {"peer_review": self.name}}
        collection.update_many(query, new_value)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/oPlYcu6.png",
            title="Team removed",
            description=f"Successfully removed team '{self.name}'.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(RemoveTeamBackButton())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="remove_team_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team removal request was canceled.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(RemoveTeamBackButton())
        await interaction.response.edit_message(embed=embed, view=view)


class RemoveTeamBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Go Back"
        self.style = discord.ButtonStyle.gray
        self.custom_id = "remove_team_back"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed, view = await TeamCog.remove_view(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class LockTeamConfirmButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()

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
        super().__init__()

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
