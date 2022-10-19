import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules import database
from modules.utils import embeds

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
            "2. Use the command `/settings role` and mention a role to assign the professor permission to it."
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
    @app_commands.checks.has_permissions(manage_guild=True)
    async def role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        collection = database.Database().get_collection("settings")
        query = {"professor": {"$exists": 1}}
        result = collection.find_one(query)
        if result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.yellow(),
                thumbnail_url="https://i.imgur.com/s1sRlvc.png",
                title="Role already assigned",
                description=f"The professor permission is currently being assigned to the role <@&{result['professor']}>. "
                f"Do you wish to update it to {role.mention}?",
                footer="Run this command again to change the role.",
            )
        else:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.yellow(),
                thumbnail_url="https://i.imgur.com/s1sRlvc.png",
                title="Role update",
                description=f"Are you sure you want to assign professor permission to the role {role.mention}?",
            )
        await interaction.response.send_message(embed=embed, view=UpdateRoleConfirmButtons(role), ephemeral=True)


class UpdateRoleConfirmButtons(discord.ui.View):
    def __init__(self, role: discord.Role) -> None:
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="update_role_yes")
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("settings")
        query = {"professor": {"$exists": 1}}
        result = collection.find_one(query)

        if result:
            new_value = {"$set": {"professor": self.role.id}}
            collection.update_one(query, new_value)
        else:
            document = {"professor": self.role.id}
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

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="update_role_no")
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your professor role update request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SettingsCog(bot))
    log.info("Cog loaded: settings")
