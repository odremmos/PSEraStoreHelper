import asyncio
import importlib
import json
import logging
import logging.config
import os
import socket
from datetime import datetime
from os import F_OK

import discord

# from psbot_commands import *
from discord.ext import commands

import async_soup_and_data

# discord.py
intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix="/", intents=intents)
logger = logging.getLogger("discord")
handler = logging.handlers.RotatingFileHandler(
    filename="discord.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}.{funcName}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[handler])


@client.tree.command(name="sync")
@commands.is_owner()
async def sync(interaction: discord.Interaction):
    """Syncs the Bots Code

    Parameters
    ----------
    interaction : discord.Interaction
        _description_
    """
    importlib.reload(async_soup_and_data)
    await client.reload_extension("psbot_commands")
    await client.tree.sync()
    await interaction.response.send_message(content="Done", ephemeral=True)


@client.tree.command(name="about")
async def about(interaction: discord.Interaction):
    # with open("token.json", "r") as cfg:
    #        author_id = json.load(cfg)
    appinfo = await client.application_info()
    user = appinfo.owner
    embed = discord.Embed(
        color=user.accent_color,
        timestamp=datetime.now(),
        description="".join(
            [
                "Created for PSEra.\nHope Plato has closed those tabs by now.",
                "\n\n",
                "Author: ",
                user.mention,
                "\n",
                "Version: 0.1.4",
                "\n",
                "Written in Python 3.10",
                "\n",
            ]
        ),
    )
    #
    embed.set_author(icon_url="https://i.imgur.com/KthK23B.png", name="\u200b")
    embed.set_thumbnail(url="https://i.imgur.com/IYO4MSm.png")
    embed.set_footer(text="About")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@client.event
async def on_ready():
    await client.tree.sync()
    print("Ready!")


# Easter Eggs
@client.command()
async def chris(message):
    if message.author == client.user:
        return

    await message.message.delete()
    await message.channel.send(
        "https://tenor.com/view/chris-hey-calling-shout-marmot-gif-16920046"
    )


@client.command()
async def wait(ctx: discord.Interaction):
    if ctx.author == client.user:
        return
    logger.info(ctx)
    await ctx.message.delete()
    await ctx.channel.send("https://i.imgur.com/IYO4MSm.png")


@client.command()
async def xiv(ctx):
    if ctx.author == client.user:
        return
    logger.info(ctx.message)
    await ctx.message.delete()
    await ctx.channel.send(
        "Have you heard of the critically acclaimed MMORPG Final Fantasy XIV which has an expanded free trial that you can play through the entirety of A Realm Reborn and the award-winning HEAVENSWARD and STORMBLOOD expansions up to level 70 for free with no restrictions on playtime? Sign up and enjoy Eorzea today!"
    )


@client.command()
@commands.is_owner()
async def host(ctx: discord.Integration):
    if ctx.author == client.user:
        return
    await ctx.channel.send(
        socket.gethostname(),
        delete_after=5,
    )


async def main():
    async with client:
        try:
            with open("token.json", "r") as cfg:
                data = json.load(cfg)
            await client.load_extension("psbot_commands")
            hostname = socket.gethostbyaddr(socket.gethostname())[0]
            if "fritz" in hostname:
                token = "dev_discord_token"
            else:
                token = "discord_token"
            await client.start(data[token])
        except Exception as error:
            print(error)


if __name__ == "__main__":
    asyncio.run(main())
