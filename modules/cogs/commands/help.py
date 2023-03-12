import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules.utils import embeds, helpers

log = logging.getLogger(__name__)


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="help", description="Information for how to use the bot for instructors."
    )
    async def help(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(
            embed=embeds.make_embed(
                color=discord.Color.blurple(), description="*Loading...*"
            ),
            view=None,
        )

        assignment_view = await helpers.get_command(
            interaction=interaction, command="assignment", subcommand_group="view"
        )
        assignment_upload = await helpers.get_command(
            interaction=interaction, command="assignment", subcommand_group="upload"
        )
        course_view = await helpers.get_command(
            interaction=interaction, command="course", subcommand_group="view"
        )
        help_command = await helpers.get_command(
            interaction=interaction, command="help"
        )
        peer_review_distribute = await helpers.get_command(
            interaction=interaction,
            command="peer",
            subcommand_group="review",
            subcommand="distribute",
        )
        peer_review_grade = await helpers.get_command(
            interaction=interaction,
            command="peer",
            subcommand_group="review",
            subcommand="grade",
        )
        peer_review_download = await helpers.get_command(
            interaction=interaction,
            command="peer",
            subcommand_group="review",
            subcommand="download",
        )
        settings_team_size = await helpers.get_command(
            interaction=interaction,
            command="settings",
            subcommand_group="team",
            subcommand="size",
        )
        settings_peer_review = await helpers.get_command(
            interaction=interaction,
            command="settings",
            subcommand_group="peer",
            subcommand="review",
        )
        settings_role = await helpers.get_command(
            interaction=interaction, command="settings", subcommand_group="role"
        )
        settings_cooldown = await helpers.get_command(
            interaction=interaction, command="settings", subcommand_group="cooldown"
        )
        submission_view = await helpers.get_command(
            interaction=interaction, command="submission", subcommand_group="view"
        )
        submission_upload = await helpers.get_command(
            interaction=interaction, command="submission", subcommand_group="upload"
        )
        team_create = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="create"
        )
        team_join = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="join"
        )
        team_leave = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="leave"
        )
        team_view = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="view"
        )
        team_rename = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="rename"
        )
        team_edit = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="edit"
        )
        team_remove = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="remove"
        )
        team_lock = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="lock"
        )
        team_unlock = await helpers.get_command(
            interaction=interaction, command="team", subcommand_group="unlock"
        )

        description = (
            "**__BASIC SETUP:__**\n\n"
            "Make sure that you have the 'Manage Server' permission. If you don't, please contact your server owner.\n\n"
            f"{settings_role.mention}: Instructor only. Assign the instructor permission to a role. Users with this role will "
            f"be able to manage course, teams, assignments, and grades. **This is a dangerous permission to grant.**\n\n"
            f"{course_view.mention}: Associate the server with a course. Instructors can update the course information at any time.\n\n"
            f"{help_command.mention}: Summon a list of commands and their usage.\n\n"
            "**__COMMANDS:__**\n\n"
            "__Settings:__\n\n"
            f"{settings_peer_review.mention}: Instructor only. Set the number of peer reviews each team will receive. The default value is 1.\n\n"
            f"{settings_team_size.mention}: Instructor only. Set the maximum number of students allowed per team. The default value is 1.\n\n"
            f"{settings_cooldown.mention}: Instructor only. Limit the rate of usage of a command to prevent abuse. The default value is once "
            f"per minute.\n\n"
            "__Team:__\n\n"
            f"{team_create.mention}: Create a new team and automatically join that team if you are not an instructor.\n\n"
            f"{team_join.mention}: Join an existing team and leave the current team if possible.\n\n"
            f"{team_leave.mention}: Leave your current team.\n\n"
            f"{team_view.mention}: View all teams. The current team you are in will be bolded. For instructors, they will see the exact "
            f"member count for each team, but students can only see whether if a team is full or not.\n\n"
            f"{team_rename.mention}: Rename a team. This is the student version of {team_edit.mention} that only allows updating their own team.\n\n"
            f"{team_edit.mention}: Instructor only. Forcefully update the name of any team.\n\n"
            f"{team_remove.mention}: Instructor only. Remove a team. This is strongly discouraged unless the team is empty.\n\n"
            f"{team_lock.mention}: Instructor only. Lock all current teams, disallowing students from creating, updating, leaving, or "
            f"joining a team.\n\n"
            f"{team_unlock.mention}: Instructor only. Unlock all current teams, re-allowing students to create, update, leave, or join a team.\n\n"
            "__Assignment:__\n\n"
            f"{assignment_view.mention}: View and manage your current assignments, or create a new one. Instructors can update the assignment.\n\n"
            f"{assignment_upload.mention}: Instructor only. Upload an attachment to an assignment.\n\n"
            "__Peer review:__\n\n"
            f"{peer_review_distribute.mention}: Instructor only. Distribute peer review to teams. Note that every time you use this command, "
            f"the peer review result for all teams will be reshuffled.\n\n"
            f"{peer_review_grade.mention}: Grade a peer review submission. Students can only peer review assignments that are not due yet on "
            f"teams they were assigned.\n\n"
            f"{peer_review_download.mention}: Download all submissions of a peer review assignment by a team. Students can only download "
            f"peer reviews of teams they were assigned.\n\n"
            "__Submission:__\n\n"
            f"{submission_view.mention}: View submissions of a team. Students can only view submissions of their own team.\n\n"
            f"{submission_upload.mention}: Submit an assignment.\n\n"
        )

        embed = embeds.make_embed(
            color=discord.Color.blurple(),
            title="Help",
            description=description,
        )
        embed.set_author(icon_url=self.bot.user.display_avatar, name=self.bot.user.name)

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
    log.info("Cog loaded: help")
