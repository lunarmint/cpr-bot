import logging
from typing import Mapping, Any

import discord
from discord import app_commands
from discord.ext import commands

from modules import database
from modules.utils import embeds, helpers

log = logging.getLogger(__name__)


class SettingsCog(commands.GroupCog, group_name="settings"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

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
            ctx=interaction,
            author=True,
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
        if result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.yellow(),
                thumbnail_url="https://i.imgur.com/s1sRlvc.png",
                title="Role already assigned",
                description=(
                    f"The instructor permission is currently being assigned to the role <@&{result['role_id']}>. "
                    f"Do you wish to update it to {role.mention}?"
                ),
            )
        else:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.yellow(),
                thumbnail_url="https://i.imgur.com/s1sRlvc.png",
                title="Role update",
                description=f"Are you sure you want to assign instructor permission to the role {role.mention}?",
            )
        await interaction.response.send_message(embed=embed, view=RoleConfirmButtons(role, result), ephemeral=True)

    @role.error
    async def role_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error(error)
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Manage role permission is required to use this command.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cooldown", description="Set cooldown for commands.")
    async def cooldown(self, interaction: discord.Interaction):
        result = await helpers.instructor_check(interaction)
        if isinstance(result, discord.Embed):
            return await interaction.response.send_message(embed=result, ephemeral=True)

        collection = database.Database().get_collection("cooldown")
        query = {"guild_id": interaction.guild_id}
        results = collection.find(query)
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/PyLyqio.png",
            title="Command cooldown",
            description="Use the dropdown below to select a command and set a cooldown for it.",
        )
        options = [discord.SelectOption(label=result["command"]) for result in results]
        cooldown_dropdown = CooldownDropdownView(options)
        await interaction.response.send_message(embed=embed, view=cooldown_dropdown, ephemeral=True)

    team = app_commands.Group(name="team", description="Set team size limit.")

    @team.command(name="size", description="Set team size limit.")
    async def team_size(self, interaction: discord.Interaction, size: int):
        result = await helpers.instructor_check(interaction)
        if isinstance(result, discord.Embed):
            return await interaction.response.send_message(embed=result, ephemeral=True)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
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
            document = {"guild_id": interaction.guild_id, "role_id": self.role.id, "team_size": 3}
            collection.insert_one(document)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Role updated",
            description=f"Professor permission is now assigned to the role {self.role.mention}.",
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="role_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
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
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Team size updated",
            description=f"Team size limit has been updated to {self.size}.",
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="team_size_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your team size limit update request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


class CooldownDropdownView(discord.ui.View):
    def __init__(self, options: list) -> None:
        super().__init__(timeout=None)
        self.add_item(CooldownDropdown(options))


class CooldownDropdown(discord.ui.Select):
    def __init__(self, options: list) -> None:
        super().__init__()
        self.options = options

    async def callback(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("cooldown")
        query = {"command": self.values[0]}
        result = collection.find_one(query)

        items = (
            discord.ui.TextInput(
                label="Rate:",
                placeholder="Number of times the command can be used before triggering a cooldown.",
                default=result["rate"],
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            ),
            discord.ui.TextInput(
                label="Per:",
                placeholder="The amount of seconds to wait for a cooldown when it’s been triggered.",
                default=result["per"],
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            ),
        )
        cooldown_modal = CooldownModal(result["command"])
        for item in items:
            cooldown_modal.add_item(item)

        await interaction.response.send_modal(cooldown_modal)


class CooldownModal(discord.ui.Modal, title="Cooldown"):
    def __init__(self, command: str) -> None:
        super().__init__()
        self.command = command

    async def on_submit(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("cooldown")
        query = {"command": self.command}
        rate = int(self.children[0].value)
        per = int(self.children[1].value)
        new_value = {"$set": {"rate": rate, "per": per}}
        collection.update_one(query, new_value)

        seconds = "seconds" if per > 1 else "second"
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
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
