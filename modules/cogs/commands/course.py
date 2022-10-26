import logging
from typing import Mapping, Any

import discord
from discord import app_commands
from discord.ext import commands

from modules import database
from modules.utils import embeds
from modules.utils import helpers

log = logging.getLogger(__name__)


class CourseCog(commands.GroupCog, group_name="course"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="manage", description="Manage your courses.")
    async def manage_course(self, interaction: discord.Interaction) -> None:
        embed = await helpers.instructor_check(interaction)
        if embed:
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild.id}
        result = collection.find_one(query)

        if result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.blurple(),
                thumbnail_url="https://i.imgur.com/NBaYHQG.png",
                title="Course information",
                description="Your current course information:",
                fields=[
                    {"name": "Course Name:", "value": result["course_name"], "inline": False},
                    {"name": "Course Abbreviation:", "value": result["course_abbreviation"], "inline": False},
                    {"name": "Course Section:", "value": result["course_section"], "inline": False},
                    {"name": "Semester:", "value": result["semester"], "inline": False},
                    {"name": "CRN:", "value": result["crn"], "inline": False},
                ],
                footer="Manage your course using the buttons below.",
            )
        else:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.blurple(),
                thumbnail_url="https://i.imgur.com/NBaYHQG.png",
                title="Course information",
                description="It seems that you haven't created any courses yet...",
                footer="Manage your course using the buttons below.",
            )
        await interaction.response.send_message(embed=embed, view=ManageCourseButtons(result), ephemeral=True)


class ManageCourseButtons(discord.ui.View):
    def __init__(self, result: Mapping[str, Any]) -> None:
        super().__init__(timeout=None)
        self.result = result

    @discord.ui.button(label="Create Course", style=discord.ButtonStyle.green, custom_id="create_course")
    async def create_course(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Failed to create course",
                description="This server is already being associated with the following course:",
                fields=[
                    {"name": "Course Name:", "value": self.result["course_name"], "inline": False},
                    {"name": "Course Abbreviation:", "value": self.result["course_abbreviation"], "inline": False},
                    {"name": "Course Section:", "value": self.result["course_section"], "inline": False},
                    {"name": "Semester:", "value": self.result["semester"], "inline": False},
                    {"name": "CRN:", "value": self.result["crn"], "inline": False},
                ],
                footer="Use the 'Edit Course' button if you wish to update the course information.",
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        await interaction.response.send_modal(CreateCourseModal())

    @discord.ui.button(label="Edit Course", style=discord.ButtonStyle.primary, custom_id="edit_course")
    async def edit_course(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        result = await helpers.course_check(interaction)
        if isinstance(result, discord.Embed):
            return await interaction.response.edit_message(embed=result, view=None)

        items = (
            discord.ui.TextInput(
                label="Course Name:",
                default=result["course_name"],
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            ),
            discord.ui.TextInput(
                label="Course Abbreviation:",
                default=result["course_abbreviation"],
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            ),
            discord.ui.TextInput(
                label="Course Section:",
                default=result["course_section"],
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            ),
            discord.ui.TextInput(
                label="Semester:",
                default=result["semester"],
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            ),
            discord.ui.TextInput(
                label="CRN:",
                default=result["crn"],
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            ),
        )
        edit_course_modal = EditCourseModal()
        for item in items:
            edit_course_modal.add_item(item)

        await interaction.response.send_modal(edit_course_modal)

    @discord.ui.button(label="Remove Course", style=discord.ButtonStyle.red, custom_id="remove_course")
    async def remove_course(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        result = await helpers.course_check(interaction)
        if isinstance(result, discord.Embed):
            return await interaction.response.edit_message(embed=result, view=None)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description="This action is irreversible. Please confirm that you want to delete the following course:",
            fields=[
                {"name": "Course Name:", "value": result["course_name"], "inline": False},
                {"name": "Course Abbreviation:", "value": result["course_abbreviation"], "inline": False},
                {"name": "Course Section:", "value": result["course_section"], "inline": False},
                {"name": "Semester:", "value": result["semester"], "inline": False},
                {"name": "CRN:", "value": result["crn"], "inline": False},
            ],
        )
        await interaction.response.edit_message(embed=embed, view=ConfirmButtons())


class CreateCourseModal(discord.ui.Modal, title="Create Course"):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.TextInput(
                label="Course Name:",
                placeholder="Software Engineering",
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            )
        )

        self.add_item(
            discord.ui.TextInput(
                label="Course Abbreviation:",
                placeholder="CSC495",
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            )
        )

        self.add_item(
            discord.ui.TextInput(
                label="Course Section:",
                placeholder="800",
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            )
        )

        self.add_item(
            discord.ui.TextInput(
                label="Semester:",
                placeholder="Fall 2022",
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            )
        )

        self.add_item(
            discord.ui.TextInput(
                label="CRN:",
                placeholder="12345",
                required=True,
                max_length=1024,
                style=discord.TextStyle.short,
            )
        )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        course_name = self.children[0].value
        course_abbreviation = self.children[1].value
        course_section = self.children[2].value
        semester = self.children[3].value
        crn = self.children[4].value

        collection = database.Database().get_collection("courses")
        document = {
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "course_name": course_name,
            "course_abbreviation": course_abbreviation,
            "course_section": course_section,
            "semester": semester,
            "crn": crn,
        }
        collection.insert_one(document)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Course created",
            description="Successfully created a new course with the following information:",
            fields=[
                {"name": "Course Name:", "value": course_name, "inline": False},
                {"name": "Course Abbreviation:", "value": course_abbreviation, "inline": False},
                {"name": "Course Section:", "value": course_section, "inline": False},
                {"name": "Semester:", "value": semester, "inline": False},
                {"name": "CRN:", "value": crn, "inline": False},
            ],
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


class EditCourseModal(discord.ui.Modal, title="Edit Course"):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        course_name = self.children[0].value
        course_abbreviation = self.children[1].value
        course_section = self.children[2].value
        semester = self.children[3].value
        crn = self.children[4].value

        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild.id}
        new_value = {
            "$set": {
                "course_name": course_name,
                "course_abbreviation": course_abbreviation,
                "course_section": course_section,
                "semester": semester,
                "crn": crn,
            }
        }
        collection.update_one(query, new_value)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Course updated",
            description="Successfully updated course with the following information:",
            fields=[
                {"name": "Course Name:", "value": course_name, "inline": False},
                {"name": "Course Abbreviation:", "value": course_abbreviation, "inline": False},
                {"name": "Course Section:", "value": course_section, "inline": False},
                {"name": "Semester:", "value": semester, "inline": False},
                {"name": "CRN:", "value": crn, "inline": False},
            ],
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


class ConfirmButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="course_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild.id}
        collection.delete_one(query)
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description="Course was successfully deleted.",
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="course_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your course removal request was canceled.",
        )
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CourseCog(bot))
    log.info("Cog loaded: course")
