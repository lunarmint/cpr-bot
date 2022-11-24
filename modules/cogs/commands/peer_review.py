import logging
import random

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
            embed=embed, view=DistributeConfirmButtons(peer_reviews, peer_review_string), ephemeral=True
        )


class DistributeConfirmButtons(discord.ui.View):
    def __init__(self, peer_reviews, peer_review_string) -> None:
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PeerReviewCog(bot))
    log.info("Cog loaded: peer review")
