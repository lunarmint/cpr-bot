import logging

import discord

from modules import database
from modules.utils import embeds

log = logging.getLogger(__name__)


async def professor_check(interaction: discord.Interaction) -> discord.Embed:
    collection = database.Database().get_collection("settings")
    query = {"professor": {"$exists": 1}}
    result = collection.find_one(query)

    embed = embeds.make_embed(
        ctx=interaction,
        author=True,
        color=discord.Color.red(),
        thumbnail_url="https://i.imgur.com/boVVFnQ.png",
        title="Error",
    )

    if result is None:
        embed.description = "No professor role was found. Use `/settings help` for more information."
        return embed

    if not any(role.id == result["professor"] for role in interaction.user.roles):
        embed.description = f"Role <@&{result['professor']}> is required to use this command."
        return embed
