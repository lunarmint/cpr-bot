import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import menus

from modules import config, database
from modules.utils import embeds
from modules.utils.pagination import Paginate

log = logging.getLogger(__name__)


class ManageCourseCog(commands.GroupCog, group_name="course"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="manage", description="Manage your courses.")
    @app_commands.checks.has_role(config["roles"]["professor"])
    async def manage_course(self, interaction: discord.Interaction) -> None:
        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/NBaYHQG.png",
            title="Manage Course",
            description="You can manage your courses using this interface.",
            footer="Use the buttons below to start.",
        )
        await interaction.response.send_message(embed=embed, view=ManageCourseButtons(), ephemeral=True)

    @manage_course.error
    async def manage_course_error(self, interaction: discord.Interaction, error: discord.HTTPException) -> None:
        if isinstance(error, discord.app_commands.errors.MissingRole):
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"Role <@&{error.missing_role}> is required to use this command.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class ManageCourseButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Course", style=discord.ButtonStyle.green, custom_id="create_course_button", emoji="📖"
    )
    async def create_course_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("courses")
        query = {"guild_id": interaction.guild.id}
        result = collection.find_one(query)
        if result:
            embed = embeds.make_embed(
                ctx=interaction,
                author=True,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Failed to create course",
                description="This server is already being associated with the following course:",
                fields=[
                    {"name": "Course Name:", "value": result["course_name"], "inline": False},
                    {"name": "Course Abbreviation:", "value": result["course_abbreviation"], "inline": False},
                    {"name": "Course Section:", "value": result["course_section"], "inline": False},
                    {"name": "Semester:", "value": result["semester"], "inline": False},
                    {"name": "CRN:", "value": result["crn"], "inline": False},
                ],
                footer="Use the 'Edit Course' button if you wish to update the course information.",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(CreateCourseModal())
        await interaction.edit_original_response(view=None)

    @discord.ui.button(
        label="Edit Course", style=discord.ButtonStyle.primary, custom_id="edit_course_button", emoji="🔧"
    )
    async def edit_course_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("courses")
        query = {"user_id": interaction.user.id}
        results = collection.find(query)
        data = []
        for result in results:
            data.append(result)

        class Formatter(menus.ListPageSource):
            async def format_page(self, menu, entries):
                embed = embeds.make_embed(title="Your Courses", color=discord.Colour.blurple())
                for key, value in entries:
                    embed.add_field(name="​", value=value, inline=False)

                return embed

        formatter = Formatter(data, per_page=1)
        menu = Paginate(formatter)
        await interaction.response.defer()
        await interaction.edit_original_response(view=None)
        await menu.start(interaction)

    @discord.ui.button(
        label="Remove Course", style=discord.ButtonStyle.red, custom_id="remove_course_button", emoji="⛔"
    )
    async def remove_course_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
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
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "course_name": self.children[0].value,
            "course_abbreviation": self.children[1].value,
            "course_section": self.children[2].value,
            "semester": self.children[3].value,
            "crn": self.children[4].value,
        }
        collection.insert_one(course_document)

        embed = embeds.make_embed(
            ctx=interaction,
            author=True,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Course created",
            description="Successfully created a new course with the following information:",
            fields=[
                {"name": "Course Name:", "value": self.children[0].value, "inline": False},
                {"name": "Course Abbreviation:", "value": self.children[1].value, "inline": False},
                {"name": "Course Section:", "value": self.children[2].value, "inline": False},
                {"name": "Semester:", "value": self.children[3].value, "inline": False},
                {"name": "CRN:", "value": self.children[4].value, "inline": False},
            ],
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        embed = embeds.make_embed(
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/M1WQDzo.png",
            title="Error",
            description="Oops! Something went wrong. Please try again later!",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        log.error(error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ManageCourseCog(bot))
    log.info("Command loaded: course create")
    log.info("Command loaded: course edit")
