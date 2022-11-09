import logging

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

    @staticmethod
    async def main_view(interaction: discord.Interaction) -> tuple[discord.Embed, discord.ui.View]:
        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild_id}
        result = collection.find_one(query)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            thumbnail_url="https://i.imgur.com/NBaYHQG.png",
            title="Course information",
            timestamp=True,
        )

        create_course_button = CreateCourseButton()
        edit_course_button = EditCourseButton()
        remove_course_button = RemoveCourseButton()

        if result:
            embed.description = "Your current course information:"
            embed.add_field(name="Course Name:", value=result["course_name"], inline=False)
            embed.add_field(name="Course Abbreviation:", value=result["course_abbreviation"], inline=False)
            embed.add_field(name="Course Section:", value=result["course_section"], inline=False)
            embed.add_field(name="Semester:", value=result["semester"], inline=False)
            embed.add_field(name="CRN:", value=result["crn"], inline=False)
            create_course_button.disabled = True
        else:
            embed.description = "It seems that you haven't created any courses yet..."
            edit_course_button.disabled = True
            remove_course_button.disabled = True

        manage_course_buttons = discord.ui.View()
        manage_course_buttons.add_item(create_course_button)
        manage_course_buttons.add_item(edit_course_button)
        manage_course_buttons.add_item(remove_course_button)

        return embed, manage_course_buttons

    @app_commands.command(name="view", description="View your current course.")
    async def view(self, interaction: discord.Interaction) -> None:
        embed, manage_course_buttons = await self.main_view(interaction)

        check = await helpers.instructor_check(interaction)
        if isinstance(check, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_message(embed=embed, view=manage_course_buttons, ephemeral=True)


class CreateCourseButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Create Course"
        self.style = discord.ButtonStyle.green
        self.custom_id = "create_course"

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(CreateCourseModal())


class EditCourseButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Edit Course"
        self.style = discord.ButtonStyle.primary
        self.custom_id = "edit_course"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.edit_message(embed=embed, view=None)

        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild_id}
        result = collection.find_one(query)

        edit_course_modal = EditCourseModal(
            course_name=result["course_name"],
            course_abbreviation=result["course_abbreviation"],
            course_section=result["course_section"],
            semester=result["semester"],
            crn=result["crn"],
        )
        await interaction.response.send_modal(edit_course_modal)


class RemoveCourseButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Remove Course"
        self.style = discord.ButtonStyle.red
        self.custom_id = "remove_course"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = await helpers.course_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.edit_message(embed=embed, view=None)

        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild_id}
        result = collection.find_one(query)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description="This action is **irreversible**. Please confirm that you want to delete the following course:",
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
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.course_name = discord.ui.TextInput(
            label="Course Name:",
            placeholder="Software Engineering",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.course_abbreviation = discord.ui.TextInput(
            label="Course Abbreviation:",
            placeholder="CSC495",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.course_section = discord.ui.TextInput(
            label="Course Section:",
            placeholder="800",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.semester = discord.ui.TextInput(
            label="Semester:",
            placeholder="Fall 2022",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.crn = discord.ui.TextInput(
            label="CRN:",
            placeholder="12345",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )

        self.add_item(self.course_name)
        self.add_item(self.course_abbreviation)
        self.add_item(self.course_section)
        self.add_item(self.semester)
        self.add_item(self.crn)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("courses")
        document = {
            "guild_id": interaction.guild_id,
            "user_id": interaction.user.id,
            "course_name": self.course_name.value,
            "course_abbreviation": self.course_abbreviation.value,
            "course_section": self.course_section.value,
            "semester": self.semester.value,
            "crn": self.crn.value,
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
                {"name": "Course Name:", "value": self.course_name.value, "inline": False},
                {"name": "Course Abbreviation:", "value": self.course_abbreviation.value, "inline": False},
                {"name": "Course Section:", "value": self.course_section.value, "inline": False},
                {"name": "Semester:", "value": self.semester.value, "inline": False},
                {"name": "CRN:", "value": self.crn.value, "inline": False},
            ],
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error(error)
        embed = embeds.make_embed(
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/M1WQDzo.png",
            title="Error",
            description="Oops! Something went wrong. Please try again later!",
            footer="Contact Mint#0504 if you wish to report the bug.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)


class EditCourseModal(discord.ui.Modal, title="Edit Course"):
    def __init__(
        self,
        course_name: str,
        course_abbreviation: str,
        course_section: str,
        semester: str,
        crn: str,
    ) -> None:
        super().__init__(timeout=None)
        self.course_name = discord.ui.TextInput(
            label="Course Name:",
            default=course_name,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.course_abbreviation = discord.ui.TextInput(
            label="Course Abbreviation:",
            default=course_abbreviation,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.course_section = discord.ui.TextInput(
            label="Course Section:",
            default=course_section,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.semester = discord.ui.TextInput(
            label="Semester:",
            default=semester,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.crn = discord.ui.TextInput(
            label="CRN:",
            default=crn,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )

        self.add_item(self.course_name)
        self.add_item(self.course_abbreviation)
        self.add_item(self.course_section)
        self.add_item(self.semester)
        self.add_item(self.crn)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild_id}
        new_value = {
            "$set": {
                "course_name": self.course_name.value,
                "course_abbreviation": self.course_abbreviation.value,
                "course_section": self.course_section.value,
                "semester": self.semester.value,
                "crn": self.crn.value,
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
                {"name": "Course Name:", "value": self.course_name.value, "inline": False},
                {"name": "Course Abbreviation:", "value": self.course_abbreviation.value, "inline": False},
                {"name": "Course Section:", "value": self.course_section.value, "inline": False},
                {"name": "Semester:", "value": self.semester.value, "inline": False},
                {"name": "CRN:", "value": self.crn.value, "inline": False},
            ],
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        log.error(error)
        embed = embeds.make_embed(
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/M1WQDzo.png",
            title="Error",
            description="Oops! Something went wrong. Please try again later!",
            footer="Contact Mint#0504 if you wish to report the bug.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="course_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id, "guild_id": interaction.guild_id}
        collection.delete_one(query)
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description="Course was successfully deleted.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="course_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your course removal request was canceled.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)


class BackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Go Back"
        self.style = discord.ButtonStyle.gray
        self.custom_id = "course_back"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed, manage_course_buttons = await CourseCog.main_view(interaction)
        await interaction.response.edit_message(embed=embed, view=manage_course_buttons)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CourseCog(bot))
    log.info("Cog loaded: course")
