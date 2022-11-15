import logging
from typing import Mapping, Any

import discord
from discord import app_commands
from discord.ext import commands

from modules.utils import database, embeds, helpers

log = logging.getLogger(__name__)


class SettingsCog(commands.GroupCog, group_name="settings"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="help", description="Instructions on how to setup the bot.")
    async def help(self, interaction: discord.Interaction) -> None:
        description = (
            "To setup the bot:\n\n"
            "1. Make sure that you have the 'Manage Server' permission. If you don't, please contact your server owner.\n\n"
            "2. Use the command `/settings role` and mention a role to assign the professor permission to it.\n\n"
            "3. Use the command `/course manage` to manage your courses if you're an instructor.\n\n"
            "4. Use the command `/team create` to create a new team.\n\n"
            "5. Use the command `/team add` to add a student to a team, either by name or by ID."
        )
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/NBaYHQG.png",
            title="Help",
            description=description,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="role", description="Setup the professor role.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        collection = database.Database().get_collection("settings")
        query = {"guild_id": interaction.guild_id}
        result = collection.find_one(query)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
        )
        if result:
            embed.title = "Role already assigned"
            embed.description = (
                f"The instructor permission is currently being assigned to the role <@&{result['role_id']}>. "
                f"Do you wish to update it to {role.mention}?"
            )
        else:
            embed.title = "Role update"
            embed.description = f"Are you sure you want to assign instructor permission to the role {role.mention}?"

        await interaction.response.send_message(embed=embed, view=RoleConfirmButtons(role, result), ephemeral=True)

    @role.error
    async def role_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error(error)
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Manage role permission is required to use this command.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cooldown", description="Set cooldown for commands.")
    async def cooldown(self, interaction: discord.Interaction):
        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        cooldown_collection = database.Database().get_collection("cooldown")
        cooldown_query = {"guild_id": interaction.guild_id}
        cooldown_result = cooldown_collection.find_one(cooldown_query)
        if cooldown_result is None:
            commands_list = ["team rename"]
            for command in commands_list:
                document = {
                    "guild_id": interaction.guild_id,
                    "command": command,
                    "rate": 1,
                    "per": 1,
                }
                cooldown_collection.insert_one(document)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/PyLyqio.png",
            title="Command cooldown",
            description="Use the dropdown below to select a command and set a cooldown for it.",
        )
        cooldown_results = cooldown_collection.find(cooldown_query)
        options = [discord.SelectOption(label=result["command"]) for result in cooldown_results]
        view = discord.ui.View()
        view.add_item(CooldownDropdown(options))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    team = app_commands.Group(name="team", description="Set team size limit.")

    @team.command(name="size", description="Set team size limit.")
    async def team_size(self, interaction: discord.Interaction, size: int):
        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        collection = database.Database().get_collection("settings")
        query = {"guild_id": interaction.guild_id}
        result = collection.find_one(query)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Team size update",
            description=f"Update the team size limit from **{result['team_size']}** to **{size}**?",
        )
        await interaction.response.send_message(embed=embed, view=TeamSizeConfirmButtons(size), ephemeral=True)


class RoleConfirmButtons(discord.ui.View):
    def __init__(self, role: discord.Role, result: Mapping[str, Any]) -> None:
        super().__init__(timeout=None)
        self.role = role
        self.result = result

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="role_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("settings")
        query = {"guild_id": interaction.guild_id}
        if self.result:
            new_value = {"$set": {"role_id": self.role.id}}
            collection.update_one(query, new_value)
        else:
            document = {
                "guild_id": interaction.guild_id,
                "role_id": self.role.id,
                "team_size": 3,
                "teams_locked": False,
            }
            collection.insert_one(document)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Role updated",
            description=f"Professor permission is now assigned to the role {self.role.mention}.",
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="role_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your instructor role update request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


class TeamSizeConfirmButtons(discord.ui.View):
    def __init__(self, size: int) -> None:
        super().__init__(timeout=None)
        self.size = size

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="team_size_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("settings")
        query = {"guild_id": interaction.guild_id}
        new_value = {"$set": {"team_size": self.size}}
        collection.update_one(query, new_value)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Team size updated",
            description=f"Team size limit has been updated to {self.size}.",
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="team_size_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team size limit update request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


class CooldownDropdown(discord.ui.Select):
    def __init__(self, options: list) -> None:
        super().__init__()
        self.options = options

    async def callback(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("cooldown")
        query = {"command": self.values[0]}
        result = collection.find_one(query)

        cooldown_modal = CooldownModal(
            command=result["command"],
            rate=result["rate"],
            per=result["per"],
        )
        await interaction.response.send_modal(cooldown_modal)


class CooldownModal(discord.ui.Modal, title="Cooldown"):
    def __init__(self, command: str, rate: int, per: int) -> None:
        super().__init__()
        self.command = command
        self.rate = discord.ui.TextInput(
            label="Rate:",
            placeholder="Number of times the command can be used.",
            default=str(rate),
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.per = discord.ui.TextInput(
            label="Per:",
            placeholder="The amount of seconds to wait for a cooldown.",
            default=str(per),
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )

        self.add_item(self.rate)
        self.add_item(self.per)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("cooldown")
        query = {"guild_id": interaction.guild_id, "command": self.command}
        rate = int(self.rate.value)
        per = int(self.per.value)

        if rate <= 0 or per <= 0:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/40eDcIB.png",
                title="Invalid input",
                description="All of your input values must be equal or greater than 1.",
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        new_value = {"$set": {"rate": rate, "per": per}}
        collection.update_one(query, new_value)

        seconds = "seconds" if per > 1 else "second"
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Command cooldown updated",
            description=f"Successfully updated `/{self.command}` command's rate to {rate} per {per} {seconds}.",
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
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))
    log.info("Cog loaded: settings")
