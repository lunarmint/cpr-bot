import logging

import arrow
import discord
from discord.app_commands import AppCommand, AppCommandGroup

from modules.utils import database, embeds

log = logging.getLogger(__name__)


async def instructor_check(interaction: discord.Interaction) -> discord.Embed | None:
    collection = database.Database().get_collection("settings")
    query = {"guild_id": interaction.guild_id}
    result = collection.find_one(query)

    embed = embeds.make_embed(
        interaction=interaction,
        color=discord.Color.red(),
        thumbnail_url="https://i.imgur.com/boVVFnQ.png",
        title="Error",
        timestamp=True,
    )

    if result is None:
        role_command = await get_command(
            interaction=interaction, command="settings", subcommand_group="role"
        )
        embed.description = f"Use {role_command.mention} first to assign a role with the instructor permission."
        return embed

    if not any(role.id == result["role_id"] for role in interaction.user.roles):
        embed.description = (
            f"Role <@&{result['role_id']}> is required to use this command."
        )
        return embed


async def course_check(interaction: discord.Interaction) -> discord.Embed | None:
    collection = database.Database().get_collection("courses")
    query = {"guild_id": interaction.guild_id}
    result = collection.find_one(query)
    if result is None:
        return embeds.make_embed(
            interaction=interaction,
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/boVVFnQ.png",
            title="Error",
            description="Cannot execute this action because this server is not associated with any courses yet.",
            timestamp=True,
        )


async def role_availability_check(
    interaction: discord.Interaction,
) -> discord.Embed | None:
    collection = database.Database().get_collection("settings")
    query = {"guild_id": interaction.guild_id}
    result = collection.find_one(query)
    if result is None:
        return embeds.make_embed(
            interaction=interaction,
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/boVVFnQ.png",
            title="Error",
            description="No instructor role was found. Use the command `/settings role` to assign a role with the instructor permission.",
            footer="Please contact your instructor or server owner if you are not one.",
            timestamp=True,
        )


async def team_lock_check(interaction: discord.Interaction) -> discord.Embed | None:
    collection = database.Database().get_collection("settings")
    query = {"guild_id": interaction.guild_id}
    result = collection.find_one(query)

    if result and any(result["role_id"] == role.id for role in interaction.user.roles):
        return

    if result is None:
        return embeds.make_embed(
            interaction=interaction,
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/boVVFnQ.png",
            title="Error",
            description="No instructor role was found. Use the command `/settings role` to assign a role with the instructor permission.",
            footer="Please contact your instructor or server owner if you are not one.",
            timestamp=True,
        )

    if result["teams_locked"]:
        return embeds.make_embed(
            interaction=interaction,
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/TwBPBrs.png",
            title="Error",
            description="You can no longer create, join, leave, or update teams.",
            footer="Contact your instructor for more information.",
            timestamp=True,
        )


async def team_check(interaction: discord.Interaction) -> discord.Embed | None:
    collection = database.Database().get_collection("teams")
    query = {"guild_id": interaction.guild_id, "members": interaction.user.id}
    result = collection.find_one(query)

    if result is None:
        create_team = await get_command(
            interaction=interaction, command="team", subcommand_group="create"
        )
        join_team = await get_command(
            interaction=interaction, command="team", subcommand_group="join"
        )
        return embeds.make_embed(
            interaction=interaction,
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/boVVFnQ.png",
            title="Error",
            description=f"You are not in any teams yet. Use {create_team.mention} and {join_team.mention} to join a team first.",
            timestamp=True,
        )


async def cooldown_check(
    interaction: discord.Interaction, command: str
) -> discord.Embed | None:
    settings_collection = database.Database().get_collection("settings")
    settings_query = {"guild_id": interaction.guild_id}
    settings_result = settings_collection.find_one(settings_query)
    if settings_result and any(
        settings_result["role_id"] == role.id for role in interaction.user.roles
    ):
        return

    task_collection = database.Database().get_collection("tasks")
    task_query = {
        "guild_id": interaction.guild_id,
        "user_id": interaction.user.id,
        "command": command,
    }
    task_result = task_collection.find_one(task_query)
    if task_result and task_result["remaining"] == 0:
        present = arrow.utcnow()
        future = present.shift(seconds=task_result["ready_on"] - present.timestamp())
        duration_string = future.humanize(
            present, only_distance=True, granularity=["hour", "minute", "second"]
        )
        return embeds.make_embed(
            interaction=interaction,
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/40eDcIB.png",
            title="Error",
            description=f"Command is on cooldown. Please try again in:\n\n {duration_string}.",
            timestamp=True,
        )


async def bot_owner_check(interaction: discord.Interaction) -> discord.Embed | None:
    if not await interaction.client.is_owner(interaction.user):
        return embeds.make_embed(
            interaction=interaction,
            color=discord.Color.red(),
            thumbnail_url="https://i.imgur.com/boVVFnQ.png",
            title="Error",
            description="You must be the bot owner to use this command.",
            timestamp=True,
        )


async def set_cooldown(interaction: discord.Interaction, command: str) -> None:
    setting_collection = database.Database().get_collection("settings")
    setting_query = {"guild_id": interaction.guild_id}
    setting_result = setting_collection.find_one(setting_query)
    if setting_result and any(
        setting_result["role_id"] == role.id for role in interaction.user.roles
    ):
        return

    cooldown_collection = database.Database().get_collection("cooldown")
    cooldown_query = {"guild_id": interaction.guild_id, "command": command}
    cooldown_result = cooldown_collection.find_one(cooldown_query)
    if cooldown_result is None:
        return

    task_collection = database.Database().get_collection("tasks")
    task_query = {
        "guild_id": interaction.guild_id,
        "user_id": interaction.user.id,
        "command": command,
    }
    tasks_result = task_collection.find_one(task_query)
    if tasks_result:
        remaining = (
            tasks_result["remaining"] - 1 if tasks_result["remaining"] > 1 else 0
        )
        new_value = {"$set": {"remaining": remaining}}
        task_collection.update_one(task_query, new_value)

    timestamp = arrow.utcnow().timestamp()
    task_document = {
        "guild_id": interaction.guild_id,
        "user_id": interaction.user.id,
        "command": command,
        "ready_on": timestamp + cooldown_result["per"],
        "remaining": cooldown_result["rate"] - 1,
    }
    task_collection.insert_one(task_document)


async def get_command(
    interaction: discord.Interaction,
    command: str,
    subcommand_group: str = None,
    subcommand: str = None,
) -> AppCommand | AppCommandGroup:
    app_commands = await interaction.client.tree.fetch_commands()
    for index, value in enumerate(app_commands):
        if value.name == command and subcommand_group is None:
            return value

        for option in value.options:
            if (
                value.name == command
                and option.name == subcommand_group
                and subcommand is None
            ):
                return option

            for item in option.options:
                if (
                    value.name == command
                    and option.name == subcommand_group
                    and item.name == subcommand
                ):
                    return item
