import asyncio
import glob
import logging
import os

import discord
from discord.ext import commands

import __init__  # noqa
import database
from config import config

bot = commands.Bot(
    activity=discord.Activity(type=discord.ActivityType.listening, name=config["bot"]["status"]),
    command_prefix=config["bot"]["prefix"],
    help_command=None,
    intents=discord.Intents(
        emojis_and_stickers=True,
        members=True,
        messages=True,
        message_content=True,
    ),
)
log = logging.getLogger(__name__)


async def main():
    for cog in glob.iglob(os.path.join("cogs", "**", "[!^_]*.py"), root_dir="modules", recursive=True):
        await bot.load_extension(cog.replace("/", ".").replace("\\", ".").replace(".py", ""))

    await bot.start(config["bot"]["token"])
    log.info(f"Logged in as: {bot.user}")

    guilds = [guild.id for guild in bot.guilds]
    log.info(f"Currently in {len(guilds)} guilds: {guilds}")

if __name__ == "__main__":
    asyncio.run(main())
