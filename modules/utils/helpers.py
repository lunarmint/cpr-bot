import logging
from typing import Any, Mapping

import discord

from modules import database
from modules.utils import embeds

log = logging.getLogger(__name__)


async def professor_check(interaction: discord.Interaction) -> discord.Embed:
    collection = database.Database().get_collection("settings")
    query = {"guild_id": interaction.guild_id}
    result = collection.find_one(query)

    embed = embeds.make_embed(
        ctx=interaction,
        author=True,
        color=discord.Color.red(),
        thumbnail_url="https://i.imgur.com/boVVFnQ.png",
        title="Error",
    )

    if result is None:
        embed.description = "No instructor role was found. Use the command `/settings role` to assign a role with the instructor permission."
        return embed

    if not any(role.id == result["role_id"] for role in interaction.user.roles):
        embed.description = f"Role <@&{result['role_id']}> is required to use this command."
        return embed


async def course_check(interaction: discord.Interaction) -> discord.Embed | Mapping[str, Any]:
    collection = database.Database().get_collection("courses")
    query = {"user_id": interaction.user.id, "guild_id": interaction.guild.id}
    result = collection.find_one(query)
    if result:
        return result

    return embeds.make_embed(
        ctx=interaction,
        author=True,
        color=discord.Color.red(),
        thumbnail_url="https://i.imgur.com/boVVFnQ.png",
        title="Error",
        description="Cannot execute this action because this server is not associated with any courses yet.",
    )


async def role_check(interaction: discord.Interaction) -> discord.Embed | Mapping[str, Any]:
    collection = database.Database().get_collection("courses")
    query = {"user_id": interaction.user.id, "guild_id": interaction.guild.id}
    result = collection.find_one(query)
    if result:
        return result

    return embeds.make_embed(
        ctx=interaction,
        author=True,
        color=discord.Color.red(),
        thumbnail_url="https://i.imgur.com/boVVFnQ.png",
        title="Error",
        description="Cannot execute this action because this server is not associated with any courses yet.",
    )
