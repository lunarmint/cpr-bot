import logging

import discord
from discord import app_commands
from discord.ext import commands

from modules import config, database
from modules.utils import embeds

log = logging.getLogger(__name__)


class ManageCourseCog(commands.GroupCog, group_name="course"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="manage", description="Manage your courses.")
    async def manage_course(self, interaction: discord.Interaction) -> None:
        embed = embeds.make_embed(
            title="Manage Course",
            description="You can manage your courses using this interface.",
            footer="Use the buttons below to start.",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, view=CreateCourseButton(), ephemeral=True)


class CreateCourseButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Course", style=discord.ButtonStyle.green, custom_id="create_course_button", emoji="📖"
    )
    async def create_course_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(CreateCourseModal())
        await interaction.edit_original_response(view=None)


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
        collection = database.Database().get_collection("courses")
        course_document = {
            "course_name": self.children[0].value,
            "course_abbreviation": self.children[1].value,
            "course_section": self.children[2].value,
            "semester": self.children[3].value,
            "crn": self.children[4].value,
        }
        collection.insert_one(course_document)

        embed = embeds.make_embed(
            title="Course Created",
            description="Successfully created a new course with the following information:",
            fields=[
                {"name": "Course Name:", "value": self.children[0].value, "inline": True},
                {"name": "Course Abbreviation:", "value": self.children[1].value, "inline": True},
                {"name": "Course Section:", "value": self.children[2].value, "inline": True},
                {"name": "Semester:", "value": self.children[3].value, "inline": True},
                {"name": "CRN:", "value": self.children[4].value, "inline": True},
            ],
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        embed = embeds.make_embed(
            description="Oops! Something went wrong. Please try again!",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        log.error(error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ManageCourseCog(bot), guild=discord.Object(id=config["guild_id"]))
    log.info("Command loaded: course create")
    log.info("Command loaded: course edit")
