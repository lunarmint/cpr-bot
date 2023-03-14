import logging

import discord
import openai
from discord import app_commands
from discord.ext import commands

from modules.utils import embeds
from modules.utils.config import config

log = logging.getLogger(__name__)


class ChatGPTCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="gpt", description="Generate text using GPT-3.")
    async def gpt(self, interaction: discord.Interaction, prompt: str) -> None:
        """/gpt command to connect to OpenAI's GPT-3 API and chat."""
        await interaction.response.defer(ephemeral=True)

        embed = embeds.make_embed(
                color=discord.Color.blurple(),
                title=prompt,
                description="*Loading...*"
            )

        await interaction.edit_original_response(embed=embed)

        openai.api_key = config["openai"]["api_key"].as_str_expanded()
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": f"{prompt}"}]
        )
        reply_content = completion.choices[0].message.content
        embed.description = reply_content

        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChatGPTCog(bot))
    log.info("Cog loaded: chat_gpt")
