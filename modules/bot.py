import glob
import logging
import os

import discord
from discord.ext import commands

import __init__  # noqa
import database
from config import config

bot = commands.Bot(
    command_prefix=config["bot"]["prefix"],
    intents=discord.Intents(
        messages=True,
        message_content=True,
        guilds=True,
        members=True,
        bans=True,
        reactions=True,
    ),
    case_insensitive=True,
    help_command=None,
)
log = logging.getLogger(__name__)


@bot.event
async def on_ready() -> None:
    """
    Called when the client is done preparing the data received from Discord.
    """
    log.info(f"Logged in as: {str(bot.user)}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name=config["bot"]["status"])
    )


if __name__ == "__main__":
    for cog in glob.iglob(os.path.join("modules/cogs", "**", "[!^_]*.py"), root_dir="modules", recursive=True):
        bot.load_extension(cog.replace("/", ".").replace("\\", ".").replace(".py", ""))
    # database.Database().setup()
    bot.run(config["bot"]["token"])
