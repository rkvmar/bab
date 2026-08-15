import discord
from discord import app_commands
from discord.ext import tasks
import random
import os
from dotenv import load_dotenv
import re
import urllib.request
import json
import requests


load_dotenv()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
TBA_URL = "https://www.thebluealliance.com/api/v3"

@tree.command(name="help", description="how do i use bot")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="bot commands",
        description="here are the commands you can use with this bot",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="/role <role>",
        value="add or remove a role from yourself",
        inline=False,
    )
    embed.add_field(
        name="/roles",
        value="list all roles you can get",
        inline=False,
    )
    embed.add_field(
        name="/match <event> <match>",
        value="get match details from The Blue Alliance",
        inline=False,
    )
    embed.add_field(
        name="/team <team number>",
        value="get team details from The Blue Alliance",
        inline=False,
    )
    embed.add_field(
        name="/xkcd <number|random>",
        value="get an xkcd comic",
        inline=False,
    )
    embed.add_field(
        name="/code",
        value="?????",
        inline=False,
    )

    await interaction.response.send_message(embed=embed)

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
@app_commands.describe(number="comic number or 'random'")
async def xkcd(interaction: discord.Interaction, number: str | None = None):
    try:
        if number and number.lower() == "random":
            with urllib.request.urlopen("https://xkcd.com/info.0.json") as resp:
                latest = json.loads(resp.read())

            number = random.randint(1, latest["num"])

        url = (
            f"https://xkcd.com/{number}/info.0.json"
            if number
            else "https://xkcd.com/info.0.json"
        )

        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

    except urllib.error.HTTPError:
        return await interaction.response.send_message(
            "comic not found", ephemeral=True
        )
    except ValueError:
        return await interaction.response.send_message(
            "please enter a comic number or `random`", ephemeral=True
        )

    embed = discord.Embed(
        title=f"xkcd #{data['num']}: {data['title']}",
        url=f"https://xkcd.com/{data['num']}/",
        color=discord.Color.blurple()
    )
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

@tree.command(name="match", description="get match details")
@app_commands.describe(event="the event to watch", match="the match to watch")
async def match(interaction: discord.Interaction, event: str, match: str):
    try:
        match = match.lower()

        if match.isdigit():
            match = f"qm{match}"

        response = requests.get(
            f"{TBA_URL}/match/{event}_{match}",
            timeout=10,
            headers={"X-TBA-Auth-Key": os.getenv("TBA_KEY")}
        )

        response.raise_for_status()

        data = response.json()
        eventName = requests.get(
            f"{TBA_URL}/event/{event}",
            timeout=10,
            headers={"X-TBA-Auth-Key": os.getenv("TBA_KEY")}
        ).json()["name"]

        url = None
        if data.get("videos"):
            url = f"https://www.youtube.com/watch?v={data['videos'][0]['key']}"

        red_teams = ", ".join(
            team.removeprefix("frc")
            for team in data["alliances"]["red"]["team_keys"]
        )

        blue_teams = ", ".join(
            team.removeprefix("frc")
            for team in data["alliances"]["blue"]["team_keys"]
        )

        description = (
            f"🟥 **{red_teams}**\n"
            f"**{data['alliances']['red']['score']} points** "
            f"({data['score_breakdown']['red']['rp']} rp)\n"
            f"\n"
            f"🟦 **{blue_teams}**\n"
            f"**{data['alliances']['blue']['score']} points** "
            f"({data['score_breakdown']['blue']['rp']} rp)"
        )

        if url:
            description += f"\n\n[Watch Match]({url})"
        if data["winning_alliance"] == "red":
            color = discord.Color.red()
        elif data["winning_alliance"] == "blue":
            color = discord.Color.blue()
        else:
            color = discord.Color.greyple()
        levels = {
            "qm": "Qualification",
            "sf": "Playoffs",
            "f": "Final"}
        num = data['match_number']
        if(data['comp_level'] == 'sf'):
            num = data['set_number']

        embed = discord.Embed(
            title=f"{eventName} {levels.get(data['comp_level'])} {num}",
            description=description,
            color=color
        )

        await interaction.response.send_message(embed=embed)

    except requests.exceptions.Timeout:
        await interaction.response.send_message(
            "The request to TBA timed out",
            ephemeral=True
        )

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            message = f"Match `{event}_{match}` was not found"
        else:
            message = f"The TBA API returned an error (`{response.status_code}`)"

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

    except requests.exceptions.RequestException:
        await interaction.response.send_message(
            "Could not connect to TBA",
            ephemeral=True
        )

    except (KeyError, TypeError, ValueError):
        await interaction.response.send_message(
            "The match data from TBA was invalid or incomplete",
            ephemeral=True
        )

    except Exception as e:
        print(f"Unexpected error in /match: {e}")

        await interaction.response.send_message(
            "Something went wrong while getting that match",
            ephemeral=True
        )

@tree.command(name="team", description="get team details")
@app_commands.describe(team="team number")
async def team(interaction: discord.Interaction, team:int):
    try:
        response = requests.get(
            f"{TBA_URL}/team/frc{team}",
            timeout=10,
            headers={"X-TBA-Auth-Key": os.getenv("TBA_KEY")}
        )

        response.raise_for_status()

        data = response.json()
        print(data)

        embed = discord.Embed(
            title=f"Team {data['team_number']}: {data['nickname']}",
            description=data.get("name", ""),
            color=discord.Color.blurple()
        )

        embed.add_field(name="Location", value=data.get("city", "Unknown"), inline=True)
        embed.add_field(name="Website", value=data.get("website", "Unknown"), inline=True)

        await interaction.response.send_message(embed=embed)

    except requests.exceptions.Timeout:
        await interaction.response.send_message(
            "The request to TBA timed out",
            ephemeral=True
        )

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            message = f"Match `{event}_{match}` was not found"
        else:
            message = f"The TBA API returned an error (`{response.status_code}`)"

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

    except requests.exceptions.RequestException:
        await interaction.response.send_message(
            "Could not connect to TBA",
            ephemeral=True
        )

    except (KeyError, TypeError, ValueError):
        await interaction.response.send_message(
            "The match data from TBA was invalid or incomplete",
            ephemeral=True
        )

    except Exception as e:
        print(f"Unexpected error in /match: {e}")

        await interaction.response.send_message(
            "Something went wrong while getting that match",
            ephemeral=True
        )
@tree.command(name="larp", description="pester someone about larping")
async def larp(interaction: discord.Interaction):
    return await interaction.response.send_message(
        "**Rules update: STOP LARPING**"
    )

@tree.command(name="code", description="?????")
async def code(interaction: discord.Interaction):
    if not CODE:
        return await interaction.response.send_message(
            "Code isn't configured",
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
