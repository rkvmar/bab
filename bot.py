import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
from dotenv import load_dotenv
import re
import urllib.request
import json

load_dotenv()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


def role_sort_key(role: discord.Role):
    match = re.search(r"\((.*?)\)", role.name)

    if not match:
        return (2, 0)

    value = match.group(1)

    if value.isdigit():
        return (0, int(value))

    return (1, value.lower())


async def role_autocomplete(
    interaction: discord.Interaction,
    current: str,
):
    return [
        app_commands.Choice(name=r.name, value=str(r.id))
        for r in interaction.guild.roles
        if "(" in r.name and current.lower() in r.name.lower()
    ][:25]


@tree.command(name="role", description="get a team role")
@app_commands.describe(role="the role to assign")
@app_commands.autocomplete(role=role_autocomplete)
async def role(interaction: discord.Interaction, role: str):
    if role.lower() == os.getenv("SECRET"):
            r = discord.utils.get(
                interaction.guild.roles,
                name="puzzle gang"
            )

            if not r:
                return await interaction.response.send_message(
                    "role not found"
                )
            if r in interaction.user.roles:
                await interaction.user.remove_roles(r)
                await interaction.response.send_message(f"removed **{r.name}**", ephemeral=True)
            else:
                await interaction.user.add_roles(r)
                await interaction.response.send_message(f"congradulatis! you found the **{r.name}** role. please don't spoil the solution for anyone else!", ephemeral=True)
    else:
        try:
            r = interaction.guild.get_role(int(role))
        except ValueError:
            return await interaction.response.send_message(
                f"invalid role: {role}"
            )

        if not r or "(" not in r.name:
            return await interaction.response.send_message(
                f"invalid role: {r.name if r else role}"
            )
        icon = ""
        if isinstance(r.display_icon, discord.PartialEmoji):
            icon = f"{r.display_icon} "
        if r in interaction.user.roles:
            await interaction.user.remove_roles(r)
            await interaction.response.send_message(f"removed {icon}**{r.name}**")
        else:
            await interaction.user.add_roles(r)
            await interaction.response.send_message(f"added {icon}**{r.name}**")


@tree.command(name="roles", description="list all roles you can get")
async def roles(interaction: discord.Interaction):
    available = [r for r in interaction.guild.roles if "(" in r.name]

    lines = []
    for r in sorted(available, key=role_sort_key):
        icon = ""

        if isinstance(r.display_icon, discord.PartialEmoji):
            icon = f"{r.display_icon} "

        lines.append(f"{icon}{r.mention}")

    embed = discord.Embed(
        title="available roles",
        description="\n".join(lines),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="use /role to add or remove roles")

    await interaction.response.send_message(embed=embed)


@tree.command(name="xkcd", description="get an xkcd comic")
@app_commands.describe(number="comic number")
async def xkcd(interaction: discord.Interaction, number: int | None = None):
    url = f"https://xkcd.com/{number}/info.0.json" if number else "https://xkcd.com/info.0.json"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError:
        return await interaction.response.send_message("comic not found", ephemeral=True)
    embed = discord.Embed(title=f"xkcd #{data['num']}: {data['title']}", url=f"https://xkcd.com/{data['num']}/", color=discord.Color.blurple())
    embed.set_image(url=data["img"])
    embed.set_footer(text=data["alt"])
    await interaction.response.send_message(embed=embed)

CODE = os.getenv("CODE")
revealed_index = None


CODE = os.getenv("CODE")

rotation = 0


def get_masked_code(user_id: int):
    if not CODE:
        return "code is not configured."

    index = (user_id + rotation) % len(CODE)

    return "".join(
        char if i == index else "?"
        for i, char in enumerate(CODE)
    )


@tasks.loop(minutes=1)
async def rotate_code():
    global rotation

    rotation += 1


@tree.command(name="code", description="?????")
async def code(interaction: discord.Interaction):
    if not CODE:
        return await interaction.response.send_message(
            "Code isn't configured.",
            ephemeral=True
        )

    masked = get_masked_code(interaction.user.id)

    await interaction.response.send_message(
        masked,
        ephemeral=True
    )

@client.event
async def on_ready():
    await tree.sync()
    if not rotate_code.is_running():
            rotate_code.start()
    print(f"Logged in as {client.user}")


client.run(os.getenv("TOKEN"))
