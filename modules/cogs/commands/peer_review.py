import logging
import random

import arrow
import discord
import discord.ui
from discord import app_commands
from discord.ext import commands

from modules.utils import embeds, database, helpers

log = logging.getLogger(__name__)


class PeerReviewCog(commands.GroupCog, group_name="peer"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    peer_review = app_commands.Group(name="review", description="Peer review commands.")

    @peer_review.command(name="distribute", description="Distribute the peer reviews.")
    async def distribute(self, interaction: discord.Interaction):
        embed = await helpers.instructor_check(interaction)
        if isinstance(embed, discord.Embed):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        settings_collection = database.Database().get_collection("settings")
        settings_query = {"guild_id": interaction.guild_id}
        settings_result = settings_collection.find_one(settings_query)
        peer_review_size = settings_result["peer_review_size"]

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id}
        teams = [team["name"] for team in team_collection.find(team_query)]

        if peer_review_size >= len(teams):
            command = await helpers.get_command(
                interaction=interaction, command="settings", subcommand_group="peer", subcommand="review"
            )
            embed = embeds.make_embed(
                interaction=interaction,
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/OidhOOU.png",
                title="Error",
                description=f"Peer review size must be smaller than the current number of teams. Use {command.mention} to update the value.",
                timestamp=True,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        random.shuffle(teams)
        peer_reviews = {}
        for index, value in enumerate(teams):
            reviews_index = list(range(index + 1, index + peer_review_size + 1))
            peer_reviews[value] = [teams[i % len(teams)] for i in reviews_index]

        peer_reviews_list = [
            f"{index + 1}. {key}: {', '.join(value)}\n" for index, (key, value) in enumerate(peer_reviews.items())
        ]
        peer_review_string = "".join(peer_reviews_list)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.yellow(),
            thumbnail_url="https://i.imgur.com/s1sRlvc.png",
            title="Peer review distribution",
            description=(
                "You are about to distribute teams for peer review. Please note that if you run this command again, "
                "all teams will be redistributed randomly again.\n\n"
                "Distribution preview:\n\n"
                f"{peer_review_string}"
            ),
        )

        await interaction.response.send_message(
            embed=embed,
            view=DistributeConfirmButtons(peer_reviews=peer_reviews, peer_review_string=peer_review_string),
            ephemeral=True,
        )

    @staticmethod
    async def grade_view(interaction: discord.Interaction):
        view = discord.ui.View()

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
        team_result = team_collection.find_one(team_query)

        if team_result and not team_result["peer_review"]:
            embed = embeds.make_embed(
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="Peer review distribution for teams has not been performed yet. Please check back later!",
                timestamp=True,
            )
            return embed, view

        assignment_collection = database.Database().get_collection("assignments")
        assignment_query = {"guild_id": interaction.guild_id}
        assignment_results = assignment_collection.find(assignment_query)

        check = await helpers.instructor_check(interaction)
        if isinstance(check, discord.Embed):
            current_timestamp = arrow.Arrow.utcnow().timestamp()
            assignment_options = [
                discord.SelectOption(label=assignment["name"])
                for assignment in assignment_results
                if assignment["due_date"] > current_timestamp
            ]
        else:
            assignment_options = [discord.SelectOption(label=assignment["name"]) for assignment in assignment_results]

        if not assignment_options:
            embed = embeds.make_embed(
                color=discord.Color.red(),
                thumbnail_url="https://i.imgur.com/boVVFnQ.png",
                title="Error",
                description="No assignments are available for grading at the moment. Please check back later!",
                timestamp=True,
            )
            return embed, view

        team_options = [discord.SelectOption(label=name) for name in team_result["peer_review"]]

        view.add_item(GradeDropdown(options=assignment_options))
        view.add_item(GradeDropdown(options=team_options))

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/o2yYOnK.png",
            title="Grading",
            description="Select a team and an assignment using the dropdowns below.",
            timestamp=True,
        )

        return embed, view

    @peer_review.command(name="grade", description="Grade peer reviews.")
    async def grade(self, interaction: discord.Interaction):
        embed, view = await self.grade_view(interaction)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class DistributeConfirmButtons(discord.ui.View):
    def __init__(self, peer_reviews: dict, peer_review_string: str) -> None:
        super().__init__()
        self.peer_reviews = peer_reviews
        self.peer_review_string = peer_review_string

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="distribute_confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        collection = database.Database().get_collection("teams")
        query = {"guild_id": interaction.guild_id}
        results = collection.find(query)

        for result in results:
            if result["name"] in self.peer_reviews:
                peer_review = self.peer_reviews[result["name"]] if result["name"] in self.peer_reviews else None
                temp_query = {"guild_id": interaction.guild_id, "name": result["name"]}
                new_value = {"$set": {"peer_review": peer_review}}
                collection.update_one(temp_query, new_value)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/oPlYcu6.png",
            title="Peer review distributed",
            description=f"Successfully distributed peer review teams as following:\n\n" f"{self.peer_review_string}",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="distribute_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.blurple(),
            thumbnail_url="https://i.imgur.com/QQiSpLF.png",
            title="Action cancelled",
            description="Your peer review distribution request was canceled.",
            timestamp=True,
        )
        await interaction.response.edit_message(embed=embed, view=None)


class GradeDropdown(discord.ui.Select):
    def __init__(self, options: list[discord.SelectOption]):
        super().__init__()
        self.options = options
        self.value = None

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self.value = self.values[0]

        assignment = self.view.children[0].value
        team = self.view.children[1].value
        if not assignment or not team:
            return

        embed = embeds.make_embed(
            interaction=interaction,
            thumbnail_url="https://i.imgur.com/o2yYOnK.png",
            title="Grading",
            description="Currently updating grade for:",
            fields=[
                {"name": "Assignment:", "value": assignment, "inline": False},
                {"name": "Team:", "value": team, "inline": False},
            ],
            timestamp=True,
        )

        grade_collection = database.Database().get_collection("grades")
        grade_query = {"guild_id": interaction.guild_id, "name": assignment, "team": team}
        grade_result = grade_collection.find_one(grade_query)
        current_points = grade_result["points"] if grade_result else 0

        assignment_collection = database.Database().get_collection("assignments")
        assignment_query = {"guild_id": interaction.guild_id, "name": assignment}
        assignment_result = assignment_collection.find_one(assignment_query)
        max_points = assignment_result["points"]

        grade_update_button = GradeUpdateButton(
            assignment=assignment,
            team=team,
            current_points=current_points,
            max_points=max_points,
        )

        team_collection = database.Database().get_collection("teams")
        team_query = {"guild_id": interaction.guild_id, "name": team}
        team_result = team_collection.find_one(team_query)

        check = await helpers.instructor_check(interaction)
        if interaction.user.id not in team_result["members"] and isinstance(check, discord.Embed):
            grade_update_button.disabled = True
            embed.set_footer(text="You don't have the permission to update this team's grade.")

        view = discord.ui.View()
        view.add_item(GradeBackButton())
        view.add_item(grade_update_button)

        await interaction.edit_original_response(embed=embed, view=view)


class GradeBackButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__()
        self.label = "Go Back"
        self.style = discord.ButtonStyle.gray
        self.custom_id = "grade_back"

    async def callback(self, interaction: discord.Interaction) -> None:
        embed, view = await PeerReviewCog.grade_view(interaction)
        await interaction.response.edit_message(embed=embed, view=view)


class GradeUpdateButton(discord.ui.Button):
    def __init__(self, assignment: str, team: str, max_points: int, current_points: int = None) -> None:
        super().__init__()
        self.label = "Update Grade"
        self.style = discord.ButtonStyle.blurple
        self.custom_id = "grade_update"
        self.assignment = assignment
        self.team = team
        self.current_points = current_points
        self.max_points = max_points

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            GradeUpdateModal(
                assignment=self.assignment,
                team=self.team,
                current_points=self.current_points,
                max_points=self.max_points,
            )
        )


class GradeUpdateModal(discord.ui.Modal, title="Update Grade"):
    def __init__(self, assignment: str, team: str, max_points: int, current_points: int = None) -> None:
        super().__init__()
        self.assignment = assignment
        self.team = team
        self.current_points = current_points
        self.max_points = max_points
        self.points = discord.ui.TextInput(
            label="Points:",
            default=str(current_points),
            placeholder=str(max_points),
            required=True,
            max_length=1024,
            style=discord.TextStyle.short,
        )
        self.add_item(self.points)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        new_points = int(self.points.value)
        collection = database.Database().get_collection("grades")
        query = {"guild_id": interaction.guild_id, "assignment": self.assignment, "team": self.team}
        result = collection.find_one(query)
        if result:
            new_value = {"$set": {"points": new_points}}
            collection.update_one(query, new_value, upsert=True)
        else:
            document = {
                "guild_id": interaction.guild_id,
                "assignment": self.assignment,
                "team": self.team,
                "points": new_points,
            }
            collection.insert_one(document)

        embed = embeds.make_embed(
            interaction=interaction,
            color=discord.Color.green(),
            thumbnail_url="https://i.imgur.com/oyNpZD5.png",
            title="Grade updated",
            description="Successfully updated grade as following:",
            fields=[
                {"name": "Assignment:", "value": self.assignment, "inline": False},
                {"name": "Team:", "value": self.team, "inline": False},
                {"name": "Points:", "value": f"**{self.current_points}** -> **{new_points}**", "inline": False},
            ],
            timestamp=True,
        )

        view = discord.ui.View()
        view.add_item(GradeBackButton())
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
        view.add_item(GradeBackButton())
        await interaction.response.edit_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PeerReviewCog(bot))
    log.info("Cog loaded: peer review")
