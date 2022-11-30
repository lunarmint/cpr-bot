import asyncio
import logging
import pathlib
from typing import List

import arrow
import discord
import magic
import requests
from discord import app_commands
from discord.ext import commands
from requests_toolbelt import MultipartEncoder

from modules.utils import database, embeds, helpers

log = logging.getLogger(__name__)


class AssignmentCog(commands.GroupCog, group_name="assignment"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    async def main_view(interaction: discord.Interaction) -> tuple[discord.Embed, discord.ui.View]:
        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/o2yYOnK.png",
            title="Assignments",
            timestamp=True,
        )

        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id}
        assignments = [item for item in collection.find(query).sort("name")]
        options = [discord.SelectOption(label=assignment["name"]) for assignment in assignments]

        view = discord.ui.View()

        if options:
            embed.description = "Use the dropdown below to select an assignment."
            view.add_item(AssignmentDropdown(options=options))
        else:
            embed.description = "No assignments are available at the moment. Please check back later!"

        check = await helpers.instructor_check(interaction)
        if not isinstance(check, discord.Embed):
            edit_assignment_button = EditAssignmentButton()
            remove_assignment_button = RemoveAssignmentButton()

            edit_assignment_button.disabled = True
            remove_assignment_button.disabled = True

            view.add_item(CreateAssignmentButton())
            view.add_item(edit_assignment_button)
            view.add_item(remove_assignment_button)

        return embed, view

    @app_commands.command(name="view", description="View all assignments.")
    async def view(self, interaction: discord.Interaction) -> None:
        embed, view = await self.main_view(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="upload", description="Upload an attachment for an assignment.")
    async def upload(
        self, interaction: discord.Interaction, assignment: str, attachment: discord.Attachment
    ) -> discord.InteractionMessage:
        await interaction.response.defer(ephemeral=True)
        await interaction.edit_original_response(
            embed=embeds.make_embed(color=discord.Color.blurple(), description="*Uploading...*")
        )

        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.followup.send(embed=embed)

        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": assignment}
        result = collection.find_one(query)

        if result is None:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="The specified assignment does not exist.",
                timestamp=True,
            )
            return await interaction.followup.send(embed=embed)

        file_dir = (
            pathlib.Path(__file__).parents[3].joinpath("uploads", str(interaction.guild_id), "assignments", assignment)
        )
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir.joinpath(attachment.filename)
        await attachment.save(file_path)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Attachment uploaded",
            description=f"Successfully uploaded an attachment to '{assignment}'.",
            timestamp=True,
        )

        await interaction.edit_original_response(embed=embed)

    @upload.autocomplete("assignment")
    async def upload_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id}
        assignments = [result["name"] for result in collection.find(query).sort("name")]
        return [
            app_commands.Choice(name=assignment, value=assignment)
            for assignment in assignments
            if current.lower() in assignment.lower()
        ]


class AssignmentDropdown(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]) -> None:
        super().__init__()
        self.options = options

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(
            embed=embeds.make_embed(color=discord.Color.blurple(), description="*Loading...*"), view=None
        )

        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.values[0]}
        result = collection.find_one(query)

        hyperlinks_list = await get_hyperlinks(interaction=interaction, assignment_name=result["name"])
        hyperlinks = "\n".join(hyperlinks_list)

        due_date = arrow.Arrow.fromtimestamp(result["due_date"], tzinfo="EST")
        duration_string = f"{due_date.format('MM/DD/YYYY, hh:mmA')} ({due_date.tzname()})"

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/HcZHHdQ.png",
            title="Assignments",
            description="Use the dropdown below to select an assignment.",
            fields=[
                {"name": "Assignment Name:", "value": result["name"], "inline": False},
                {"name": "Points Possible:", "value": result["points"], "inline": False},
                {"name": "Due Date:", "value": duration_string, "inline": False},
                {"name": "Instructions:", "value": result["instructions"], "inline": False},
                {
                    "name": "Attachment:",
                    "value": f"{hyperlinks if hyperlinks else None}",
                    "inline": False,
                },
            ],
            timestamp=True,
        )

        try:
            self.view.children[2].disabled = False
            self.view.children[3].disabled = False
            self.view.children[2].assignment_name = self.values[0]
            self.view.children[3].assignment_name = self.values[0]
        except IndexError:
            pass

        if len(self.view.children) > 0:
            if result["peer_review"]:
                self.view.add_item(PeerReviewEnabledButton(assignment_name=self.values[0]))
            else:
                self.view.add_item(PeerReviewDisabledButton(assignment_name=self.values[0]))

        await interaction.edit_original_response(embed=embed, view=self.view)


class CreateAssignmentButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Create Assignment"
        self.style = discord.ButtonStyle.green
        self.custom_id = "create_assignment"

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(CreateAssignmentModal())


class EditAssignmentButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Edit Assignment"
        self.style = discord.ButtonStyle.primary
        self.custom_id = "edit_assignment"
        self.assignment_name = None

    async def callback(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.assignment_name}
        result = collection.find_one(query)

        due_date = arrow.Arrow.fromtimestamp(result["due_date"], tzinfo="EST")
        duration_string = f"{due_date.format('MM/DD/YYYY HH:mm')}"

        edit_assignment_modal = EditAssignmentModal(
            name=result["name"],
            points=result["points"],
            due_date=duration_string,
            instructions=result["instructions"],
        )
        await interaction.response.send_modal(edit_assignment_modal)


class RemoveAssignmentButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Remove Assignment"
        self.style = discord.ButtonStyle.red
        self.custom_id = "remove_assignment"
        self.assignment_name = None

    async def callback(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.assignment_name}
        result = collection.find_one(query)

        hyperlinks_list = await get_hyperlinks(interaction=interaction, assignment_name=result["name"])
        hyperlinks = "\n".join(hyperlinks_list)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Warning",
            description="This action is **irreversible**. Please confirm that you want to delete the following assignment:",
            fields=[
                {"name": "Assignment Name:", "value": result["name"], "inline": False},
                {"name": "Points Possible:", "value": result["points"], "inline": False},
                {"name": "Due Date:", "value": result["due_date"], "inline": False},
                {"name": "Instructions:", "value": result["instructions"], "inline": False},
                {
                    "name": "Attachment:",
                    "value": f"{hyperlinks if hyperlinks else None}",
                    "inline": False,
                },
            ],
        )
        await interaction.response.edit_message(embed=embed, view=RemoveAssignmentConfirmButtons(self.assignment_name))


class RemoveAssignmentConfirmButtons(discord.ui.View):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="assignment_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.name}
        collection.delete_one(query)
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Success",
            description="Assignment was successfully deleted.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="assignment_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your assignment removal request was canceled.",
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        await interaction.response.edit_message(embed=embed, view=view)


class CreateAssignmentModal(discord.ui.Modal, title="Create Assignment"):
    def __init__(self) -> None:
        super().__init__()
        self.assignment_name = discord.ui.TextInput(
            label="Assignment Name:",
            placeholder="Assignment 1",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.points = discord.ui.TextInput(
            label="Points Possible:",
            placeholder="10",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.due_date = discord.ui.TextInput(
            label="Due Date:",
            placeholder="MM/DD/YYYY HH:mm",
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.instructions = discord.ui.TextInput(
            label="Instructions:",
            placeholder="Your assignment instructions here.",
            required=True,
            style=discord.TextStyle.paragraph,
        )

        self.add_item(self.assignment_name)
        self.add_item(self.points)
        self.add_item(self.due_date)
        self.add_item(self.instructions)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.assignment_name.value}
        result = collection.find_one(query)
        if result and result["name"] in (self.assignment_name.value, self.assignment_name.value.lower()):
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="An assignment with this name already exist.",
                timestamp=True,
            )

            view = discord.ui.View()
            view.add_item(BackButton())
            return await interaction.response.edit_message(embed=embed, view=view)

        points = int(self.points.value)
        if points < 0:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Points cannot be a negative value.",
                timestamp=True,
            )

            view = discord.ui.View()
            view.add_item(BackButton())
            return await interaction.response.edit_message(embed=embed, view=view)

        try:
            time = arrow.Arrow(
                year=int(self.due_date.value[6:10]),
                month=int(self.due_date.value[:2]),
                day=int(self.due_date.value[3:5]),
                hour=int(self.due_date.value[11:13]),
                minute=int(self.due_date.value[14:16]),
                tzinfo="EST",
            )
        except ValueError:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=(
                    "Time input must **strictly** follow the format `MM/DD/YYYY hh:mm`.\n\n"
                    "Example:\n\n"
                    "04/30/2022 23:59\n"
                    "12/24/2022 08:30\n\n"
                    "Invalid date and time values will also not be accepted."
                ),
                timestamp=True,
            )
            view = discord.ui.View()
            view.add_item(BackButton())
            return await interaction.response.edit_message(embed=embed, view=view)

        document = {
            "guild_id": interaction.guild_id,
            "name": self.assignment_name.value,
            "points": points,
            "due_date": time.timestamp(),
            "instructions": self.instructions.value,
            "peer_review": False,
        }
        collection.insert_one(document)

        upload_command = await helpers.get_command(interaction=interaction, command="assignment", subcommand_group="upload")

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Assignment created",
            description="Successfully created a new assignment:",
            fields=[
                {"name": "Assignment Name:", "value": self.assignment_name.value, "inline": False},
                {"name": "Points Possible:", "value": points, "inline": False},
                {"name": "Due Date:", "value": f"{time.format('MM/DD/YYYY, hh:mmA')} ({time.tzname()})", "inline": False},
                {"name": "Instructions:", "value": self.instructions.value, "inline": False},
                {
                    "name": "Attachment:",
                    "value": f"Use the command {upload_command.mention} to create an attachment for this assignment.",
                    "inline": False,
                },
            ],
            timestamp=True,
            footer="Use the button below to enable or disable peer review for this assignment.",
        )

        view = discord.ui.View()
        view.add_item(BackButton())
        view.add_item(PeerReviewDisabledButton(assignment_name=self.assignment_name.value))
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


class EditAssignmentModal(discord.ui.Modal, title="Edit Assignment"):
    def __init__(self, name: str, points: int, due_date: str, instructions: str) -> None:
        super().__init__()
        self.name = discord.ui.TextInput(
            label="Assignment Name:",
            placeholder="Assignment 1",
            default=name,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.points = discord.ui.TextInput(
            label="Points Possible:",
            placeholder="10",
            default=str(points),
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.due_date = discord.ui.TextInput(
            label="Due Date:",
            placeholder="MM/DD/YYYY HH:mm",
            default=due_date,
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.instructions = discord.ui.TextInput(
            label="Instructions:",
            placeholder="Your assignment instructions here.",
            default=str(instructions),
            required=True,
            max_length=1024,
            style=discord.TextStyle.paragraph,
        )

        self.add_item(self.name)
        self.add_item(self.points)
        self.add_item(self.due_date)
        self.add_item(self.instructions)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        points = int(self.points.value)
        if points < 0:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Points cannot be a negative value",
                timestamp=True,
            )

            view = discord.ui.View()
            view.add_item(BackButton())
            return await interaction.response.edit_message(embed=embed, view=view)

        try:
            time = arrow.Arrow(
                year=int(self.due_date.value[6:10]),
                month=int(self.due_date.value[:2]),
                day=int(self.due_date.value[3:5]),
                hour=int(self.due_date.value[11:13]),
                minute=int(self.due_date.value[14:16]),
                tzinfo="EST",
            )
        except ValueError:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=(
                    "Time input must **strictly** follow the format `MM/DD/YYYY HH:mm`.\n\n"
                    "Example:\n\n"
                    "04/30/2022 23:59\n"
                    "12/24/2022 08:30\n\n"
                    "Invalid date and time values will also not be accepted."
                ),
                timestamp=True,
            )
            view = discord.ui.View()
            view.add_item(BackButton())
            return await interaction.response.edit_message(embed=embed, view=view)

        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.name.value}
        new_value = {
            "$set": {
                "name": self.name.value,
                "points": points,
                "due_date": time.timestamp(),
                "instructions": self.instructions.value,
            }
        }
        collection.update_one(query, new_value)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Assignment updated",
            description="Successfully updated an assignment:",
            fields=[
                {"name": "Assignment Name:", "value": self.name.value, "inline": False},
                {"name": "Points Possible:", "value": self.points.value, "inline": False},
                {"name": "Due Date:", "value": f"{time.format('MM/DD/YYYY, hh:mmA')} ({time.tzname()})", "inline": False},
                {"name": "Instructions:", "value": self.instructions.value, "inline": False},
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
        self.custom_id = "assignment_back"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed, view = await AssignmentCog.main_view(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class PeerReviewEnabledButton(discord.ui.Button):
    def __init__(self, assignment_name: str) -> None:
        super().__init__()
        self.label = "Peer Review Enabled"
        self.style = discord.ButtonStyle.green
        self.custom_id = "peer_review_enabled"
        self.assignment_name = assignment_name

    async def callback(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.assignment_name}
        new_value = {"$set": {"peer_review": False}}
        collection.update_one(query, new_value)

        for index, children in enumerate(self.view.children):
            if children.custom_id == self.custom_id:
                self.view.remove_item(self.view.children[index])
                self.view.add_item(PeerReviewDisabledButton(assignment_name=self.assignment_name))

        await interaction.response.edit_message(embed=interaction.message.embeds[0], view=self.view)


class PeerReviewDisabledButton(discord.ui.Button):
    def __init__(self, assignment_name: str) -> None:
        super().__init__()
        self.label = "Peer Review Disabled"
        self.style = discord.ButtonStyle.red
        self.custom_id = "peer_review_disabled"
        self.assignment_name = assignment_name

    async def callback(self, interaction: discord.Interaction) -> None:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.assignment_name}
        new_value = {"$set": {"peer_review": True}}
        collection.update_one(query, new_value)

        for index, children in enumerate(self.view.children):
            if children.custom_id == self.custom_id:
                self.view.remove_item(self.view.children[index])
                self.view.add_item(PeerReviewEnabledButton(assignment_name=self.assignment_name))

        await interaction.response.edit_message(embed=interaction.message.embeds[0], view=self.view)


async def get_hyperlinks(interaction: discord.Interaction, assignment_name: str) -> list[str]:
    def task():
        root = pathlib.Path(__file__).parents[3]
        file_dir = root.joinpath("uploads", str(interaction.guild_id), "assignments", assignment_name).glob("**/*")
        hyperlinks = []
        for item in file_dir:
            if item.is_file():
                file = item.open(mode="rb")
                mime_type = magic.from_buffer(file.read(2048), mime=True)
                file.seek(0)
                fields = {"time": "1h", "reqtype": "fileupload", "fileToUpload": (item.name, file, mime_type)}
                encoder = MultipartEncoder(fields=fields)
                response = requests.post(
                    url="https://litterbox.catbox.moe/resources/internals/api.php",
                    data=encoder,
                    headers={"Content-Type": encoder.content_type},
                )
                hyperlinks.append(f"[Download]({response.text})")
        return hyperlinks

    return await asyncio.to_thread(task)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AssignmentCog(bot))
    log.info("Cog loaded: assignment")
