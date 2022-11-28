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


class SubmissionCog(commands.GroupCog, group_name="submission"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    async def main_view(interaction: discord.Interaction) -> tuple[discord.Embed, discord.ui.View]:
        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/o2yYOnK.png",
            title="Submissions",
            timestamp=True,
        )

        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id}
        assignments = [item for item in collection.find(query).sort("name")]
        options = [discord.SelectOption(label=assignment["name"]) for assignment in assignments]

        view = discord.ui.View()

        if options:
            embed.description = "Use the dropdown below to select an assignment and view your submissions."
            view.add_item(SubmissionDropdown(options=options))
        else:
            embed.description = "No assignments are available at the moment. Please check back later!"

        return embed, view

    @app_commands.command(name="view", description="View assignments submissions.")
    async def view(self, interaction: discord.Interaction) -> None:
        embed, view = await self.main_view(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="upload", description="Submit an assignment.")
    async def upload(self, interaction: discord.Interaction, assignment: str, attachment: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        assignment_collection = database.Database().get_collection("assignments")
        assignment_query = {"guild_id": interaction.guild_id, "name": assignment}
        assignment_result = assignment_collection.find_one(assignment_query)

        if assignment_result is None:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="The specified assignment does not exist.",
                timestamp=True,
            )
            return await interaction.followup.send(embed=embed)

        current_timestamp = arrow.Arrow.utcnow().timestamp()
        if current_timestamp > assignment_result["due_date"]:
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="This assignment is already past due.",
                timestamp=True,
            )
            return await interaction.followup.send(embed=embed)

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
        team_result = team_collection.find_one(team_query)

        if team_result is None:
            create_team = await helpers.get_command(interaction=interaction, command="team", subcommand_group="create")
            join_team = await helpers.get_command(interaction=interaction, command="team", subcommand_group="join")
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description=f"You are not in any teams yet. Use {create_team.mention} and {join_team.mention} to join a team first.",
                timestamp=True,
            )
            return await interaction.followup.send(embed=embed)

        await interaction.edit_original_response(
            embed=embeds.make_embed(color=discord.Color.blurple(), description="*Uploading...*")
        )

        file_dir = (
            pathlib.Path(__file__).parents[3].joinpath("uploads", str(interaction.guild_id), "submissions", team_result["name"], assignment)
        )
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir.joinpath(attachment.filename)
        await attachment.save(file_path)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/W7VJssL.png",
            title="Assignment submitted",
            description=f"Successfully submitted assignment '{assignment}'.",
            timestamp=True,
        )

        await interaction.edit_original_response(embed=embed)

    @upload.autocomplete("assignment")
    async def upload_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id}
        current_timestamp = arrow.Arrow.utcnow().timestamp()
        assignments = [
            result["name"] for result in collection.find(query).sort("name") if current_timestamp <= result["due_date"]
        ]
        return [
            app_commands.Choice(name=assignment, value=assignment)
            for assignment in assignments
            if current.lower() in assignment.lower()
        ]


class SubmissionDropdown(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]) -> None:
        super().__init__()
        self.options = options

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(
            embed=embeds.make_embed(color=discord.Color.blurple(), description="*Loading...*"), view=self.view
        )

        collection = database.Database().get_collection("assignments")
        query = {"guild_id": interaction.guild_id, "name": self.values[0]}
        result = collection.find_one(query)

        def get_hyperlinks() -> list[str]:
            root = pathlib.Path(__file__).parents[3]
            file_dir = root.joinpath("uploads", str(interaction.guild_id), "submissions", result["name"]).glob("**/*")
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

        hyperlinks_list = await asyncio.to_thread(get_hyperlinks)
        hyperlinks_value = "\n".join(hyperlinks_list)

        due_date = arrow.Arrow.fromtimestamp(result["due_date"], tzinfo="EST")
        duration_string = f"{due_date.format('MM/DD/YYYY, hh:mmA')} ({due_date.tzname()})"

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/HcZHHdQ.png",
            title="Assignments",
            description="Use the dropdown below to select an assignment and view your submissions.",
            fields=[
                {"name": "Assignment Name:", "value": result["name"], "inline": False},
                {"name": "Points Possible:", "value": result["points"], "inline": False},
                {"name": "Due Date:", "value": duration_string, "inline": False},
                {"name": "Instructions:", "value": result["instructions"], "inline": False},
                {
                    "name": "Your Submissions:",
                    "value": f"{hyperlinks_value if hyperlinks_value else None}",
                    "inline": False,
                },
            ],
            timestamp=True,
        )

        await interaction.edit_original_response(embed=embed, view=self.view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SubmissionCog(bot))
    log.info("Cog loaded: submission")
