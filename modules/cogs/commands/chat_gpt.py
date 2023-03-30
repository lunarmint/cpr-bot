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

    gpt = app_commands.Group(name="gpt", description="GPT-3 commands.")

    @gpt.command(name="chat", description="Generate text using GPT-3.")
    async def chat(self, interaction: discord.Interaction, prompt: str) -> None:
        """/gpt chat command to chat using OpenAI's GPT-3."""
        await interaction.response.defer(ephemeral=True)

        embed = embeds.make_embed(
            color=discord.Color.blurple(), title=prompt, description="*Loading...*"
        )

        await interaction.edit_original_response(embed=embed)

        openai.api_key = config["openai"]["api_key"].as_str_expanded()
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"{prompt}"}],
            )
        except (
            openai.error.APIError,
            openai.error.Timeout,
            openai.error.RateLimitError,
            openai.error.APIError,
            openai.error.APIConnectionError,
            openai.error.InvalidRequestError,
            openai.error.AuthenticationError,
            openai.error.ServiceUnavailableError,
        ) as e:
            embed.description = e.user_message
            await interaction.edit_original_response(embed=embed)
            return

        reply_content = response.choices[0].message.content
        embed.description = reply_content
        await interaction.edit_original_response(embed=embed)

    @gpt.command(name="image", description="Generate image using GPT-3.")
    async def image(self, interaction: discord.Interaction, prompt: str) -> None:
        """/gpt image command to generate image using OpenAI's GPT-3."""
        await interaction.response.defer(ephemeral=True)

        embed = embeds.make_embed(
            color=discord.Color.blurple(), title=prompt, description="*Loading...*"
        )

        await interaction.edit_original_response(embed=embed)

        openai.api_key = config["openai"]["api_key"].as_str_expanded()
        try:
            response = openai.Image.create(
                prompt=f"{prompt}", n=1, size="1024x1024", response_format="url"
            )
        except (
            openai.error.APIError,
            openai.error.Timeout,
            openai.error.RateLimitError,
            openai.error.APIError,
            openai.error.APIConnectionError,
            openai.error.InvalidRequestError,
            openai.error.AuthenticationError,
            openai.error.ServiceUnavailableError,
        ) as e:
            embed.description = e.user_message
            await interaction.edit_original_response(embed=embed)
            return

        image_url = response.data[0].url
        embed.description = None
        embed.set_image(url=image_url)
        await interaction.edit_original_response(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChatGPTCog(bot))
    log.info("Cog loaded: chat_gpt")
