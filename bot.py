import discord
from discord import app_commands
import os
from dotenv import load_dotenv
import re

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
    r = interaction.guild.get_role(int(role))
    if not r or "(" not in r.name:
        return await interaction.response.send_message("role not found")
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


@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")


client.run(os.getenv("TOKEN"))
