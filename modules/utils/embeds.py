import datetime

import discord
from discord.ext import commands


def make_embed(
    ctx: commands.Context | discord.Interaction = None,
    author: bool = None,
    color: int | discord.colour.Colour = None,
    title: str = None,
    description: str = None,
    title_url: str = None,
    thumbnail_url: str = None,
    image_url: str = None,
    fields: list = None,
    footer: str = None,
    timestamp: bool | int | datetime.datetime = None,
) -> discord.Embed:
    """
    A wrapper for discord.Embed with added support for non-native attributes.
    `color` can either be of type discord.Color or a hexadecimal value.
    `timestamp` can either be a unix timestamp or a datetime object.
    """
    embed = discord.Embed()

    if ctx and author:
        if isinstance(ctx, commands.Context):
            embed.set_author(icon_url=ctx.author.display_avatar, name=ctx.author.name)
        elif isinstance(ctx, discord.Interaction):
            embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)

    if isinstance(color, int | discord.colour.Colour):
        embed.colour = color
    else:
        embed.colour = discord.Colour.blurple()

    if fields:
        for field in fields:
            name = field.get("name", "​") or "​"
            value = field.get("value", "​") or "​"
            inline = field["inline"] if isinstance(field["inline"], bool) else False
            embed.add_field(name=name, value=value, inline=inline)

    if isinstance(timestamp, bool):
        embed.timestamp = discord.utils.utcnow() if timestamp else None
    elif isinstance(timestamp, int):
        embed.timestamp = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    elif isinstance(timestamp, datetime.datetime):
        embed.timestamp = timestamp

    embed.title = title
    embed.description = description
    embed.url = title_url
    embed.set_thumbnail(url=thumbnail_url)
    embed.set_image(url=image_url)
    embed.set_footer(text=footer)

    return embed
