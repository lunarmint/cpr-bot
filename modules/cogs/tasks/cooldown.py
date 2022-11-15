import logging

import arrow
from discord.ext import commands, tasks

from modules.utils import database

log = logging.getLogger(__name__)


class CooldownCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cooldown_check.start()

    def cog_unload(self) -> None:
        self.cooldown_check.cancel()

    @tasks.loop(seconds=3.0)
    async def cooldown_check(self) -> None:
        collection = database.Database().get_collection("tasks")
        timestamp = arrow.utcnow().timestamp()
        query = {"ready_on": {"$lt": timestamp}}
        result = collection.find(query)
        if result:
            collection.delete_many(query)

    @cooldown_check.before_loop
    async def before_loop(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CooldownCog(bot))
    log.info("Cog loaded: cooldown")
