import datetime
from typing import Union

import discord
from discord.ext import commands


def make_embed(
    ctx: Union[commands.Context, discord.Interaction] = None,
    author: bool = None,
    title: str = "",
    description: str = "",
    title_url: str = None,
    thumbnail_url: str = None,
    image_url: str = None,
    fields: list = None,
    footer: str = None,
    color=None,
    timestamp=None,
) -> discord.Embed:
    """
    A wrapper for discord.Embed with added support for non-native attributes.
    `color` can either be of type discord.Color or a hexadecimal value.
    `timestamp` can either be a unix timestamp or a datetime object.
    """

    if not isinstance(color, (int, discord.colour.Colour)):
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
    else:
        embed = discord.Embed(title=title, description=description, color=color)

    if ctx and author:
        if isinstance(ctx, commands.Context):
            embed.set_author(icon_url=ctx.author.display_avatar, name=ctx.author.name)

        if isinstance(ctx, discord.Interaction):
            embed.set_author(icon_url=ctx.user.display_avatar, name=ctx.user.name)

    if title_url:
        embed.url = title_url

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if image_url:
        embed.set_image(url=image_url)

    if fields:
        for field in fields:
            name = field.get("name", "​")
            value = field.get("value", "​")
            inline = field["inline"] if isinstance(field["inline"], bool) else False
            embed.add_field(name=name, value=value, inline=inline)

    if footer:
        embed.set_footer(text=footer)

    if timestamp:
        if isinstance(timestamp, int):
            embed.timestamp = datetime.datetime.fromtimestamp(timestamp)
        else:
            embed.timestamp = timestamp

    return embed
