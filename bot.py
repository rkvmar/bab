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
import time
import csv

load_dotenv()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
TBA_URL = "https://www.thebluealliance.com/api/v3"


@tree.command(name="help", description="how do i use bot")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="bot commands",
        color=discord.Color.blurple(),
    )
    embed.add_field(
        name="/team <role>",
        value="add or remove a team role from yourself",
        inline=False,
    )
    embed.add_field(
        name="/role <role>",
        value="get a misc role",
        inline=False,
    )
    embed.add_field(
        name="/teams",
        value="list all team roles you can get",
        inline=False,
    )
    embed.add_field(
        name="/getmatch <event> <match> <type (optional)>",
        value="get match details from The Blue Alliance",
        inline=False,
    )
    embed.add_field(
        name="/getteam <team number>",
        value="get team details from The Blue Alliance",
        inline=False,
    )
    embed.add_field(
        name="/xkcd <number|random>",
        value="get an xkcd comic",
        inline=False,
    )
    embed.add_field(
        name="/market show",
        value="show the stock market",
        inline=False,
    )
    embed.add_field(
        name="/market leaderboard",
        value="show the stock leaderboard",
        inline=False,
    )
    embed.add_field(
        name="/market portfolio",
        value="show your stock portfolio",
        inline=False,
    )
    embed.add_field(
        name="/market buy <team> <shares>",
        value="buy shares of a team",
        inline=False,
    )
    embed.add_field(
        name="/market sell <team> <shares>",
        value="sell shares of a team",
        inline=False,
    )
    embed.add_field(
        name="/profile <name> [image]",
        value="set your leaderboard name and avatar",
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


@tree.command(name="team", description="get a team role")
@app_commands.describe(role="the role to assign")
@app_commands.autocomplete(role=role_autocomplete)
async def team_role(interaction: discord.Interaction, role: str):
    if role.lower() == os.getenv("SECRET"):
        r = discord.utils.get(interaction.guild.roles, name="puzzle gang")

        if not r:
            return await interaction.response.send_message("role not found")
        if r in interaction.user.roles:
            await interaction.user.remove_roles(r)
            await interaction.response.send_message(
                f"removed **{r.name}**", ephemeral=True
            )
        else:
            await interaction.user.add_roles(r)
            await interaction.response.send_message(
                f"congradulatis! you found the **{r.name}** role. please don't spoil the solution for anyone else!",
                ephemeral=True,
            )
    else:
        try:
            r = interaction.guild.get_role(int(role))
        except ValueError:
            return await interaction.response.send_message(
                f"invalid role: {role}", ephemeral=True
            )

        if not r or "(" not in r.name:
            return await interaction.response.send_message(
                f"invalid role: {r.name if r else role}", ephemeral=True
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


@tree.command(name="teams", description="list all roles you can get")
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
    embed.set_footer(text="use /team to add or remove roles")

    await interaction.response.send_message(embed=embed)


ROLE_REQUIREMENTS = {
    "serious": "level 17",
}


@tree.command(name="role", description="get an opt-in role")
@app_commands.describe(role="the role to assign")
@app_commands.choices(
    role=[app_commands.Choice(name=name, value=name) for name in ROLE_REQUIREMENTS]
)
async def role(interaction: discord.Interaction, role: str):
    required_name = ROLE_REQUIREMENTS[role]

    required = discord.utils.get(
        interaction.guild.roles,
        name=required_name,
    )
    r = discord.utils.get(interaction.guild.roles, name=role)

    if not required or not r:
        return await interaction.response.send_message("role not found", ephemeral=True)

    if required not in interaction.user.roles:
        return await interaction.response.send_message(
            f"you need to be **{required.name}** to get **{r.name}**",
            ephemeral=True,
        )

    if r in interaction.user.roles:
        await interaction.user.remove_roles(r)
        await interaction.response.send_message(f"removed **{r.name}**", ephemeral=True)
    else:
        await interaction.user.add_roles(r)
        await interaction.response.send_message(f"added **{r.name}**", ephemeral=True)


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
        color=discord.Color.blurple(),
    )
    embed.set_image(url=data["img"])
    embed.set_footer(text=data["alt"])

    await interaction.response.send_message(embed=embed)


CODE = os.getenv("CODE")
revealed_index = None

rotation = 0


def get_masked_code(user_id: int):
    if not CODE:
        return "code is not configured."

    index = (user_id + rotation) % len(CODE)

    return "".join(char if i == index else "?" for i, char in enumerate(CODE))


@tasks.loop(minutes=1)
async def rotate_code():
    global rotation

    rotation += random.randint(2, 4)


events_cache = {"timestamp": 0, "events": []}

EVENT_CACHE_SECONDS = 60 * 60
MATCH_TYPES = [
    app_commands.Choice(name="Qualification", value="qm"),
    app_commands.Choice(name="Playoffs", value="sf"),
    app_commands.Choice(name="Finals", value="f"),
]


def get_this_year_events():
    now = time.time()

    if events_cache["events"] and now - events_cache["timestamp"] < EVENT_CACHE_SECONDS:
        return events_cache["events"]

    year = discord.utils.utcnow().year

    response = requests.get(
        f"{TBA_URL}/events/{year}",
        timeout=10,
        headers={"X-TBA-Auth-Key": os.getenv("TBA_KEY")},
    )

    response.raise_for_status()

    events = response.json()

    events_cache["events"] = events
    events_cache["timestamp"] = now

    return events


async def event_autocomplete(interaction: discord.Interaction, current: str):
    try:
        events = get_this_year_events()

        current = current.lower().strip()

        choices = []

        for event in events:
            name = event.get("name", "")
            key = event.get("key", "")

            if current in name.lower() or current in key.lower():
                display_name = f"{name} ({key})"

                display_name = display_name[:100]

                choices.append(app_commands.Choice(name=display_name, value=key))

        return choices[:25]

    except Exception as e:
        print(f"Autocomplete error: {e}")
        return []


def resolve_event(event_input: str):
    event_input = event_input.strip()

    events = get_this_year_events()

    for event in events:
        if event.get("key", "").lower() == event_input.lower():
            return event["key"], event["name"]

    for event in events:
        if event.get("name", "").lower() == event_input.lower():
            return event["key"], event["name"]

    matches = [
        event
        for event in events
        if event_input.lower() in event.get("name", "").lower()
    ]

    if len(matches) == 1:
        return matches[0]["key"], matches[0]["name"]

    raise ValueError("Event was not found")


@tree.command(name="match", description="get match details")
@app_commands.describe(
    event="the event to watch", match="the match to watch", type="the type of match"
)
@app_commands.choices(type=MATCH_TYPES)
@app_commands.autocomplete(event=event_autocomplete)
async def match(
    interaction: discord.Interaction, event: str, match: str, type: str = "qm"
):
    try:
        event_key, event_name = resolve_event(event)

        match = match.lower().strip()

        if match.isdigit():
            if type == "f":
                match = f"f1m{match}"
            elif type == "sf":
                match = f"sf{match}m1"
            else:
                match = f"{type}{match}"

        response = requests.get(
            f"{TBA_URL}/match/{event_key}_{match}",
            timeout=10,
            headers={"X-TBA-Auth-Key": os.getenv("TBA_KEY")},
        )

        response.raise_for_status()

        data = response.json()

        url = None

        if data.get("videos"):
            video = data["videos"][0]

            if video.get("type") == "youtube":
                url = f"https://www.youtube.com/watch?v={video['key']}"

        red_teams = ", ".join(
            team.removeprefix("frc") for team in data["alliances"]["red"]["team_keys"]
        )

        blue_teams = ", ".join(
            team.removeprefix("frc") for team in data["alliances"]["blue"]["team_keys"]
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

        levels = {"qm": "Qualification", "sf": "Playoffs", "f": "Final"}

        num = data["match_number"]

        if data["comp_level"] == "sf":
            num = data["set_number"]

        level = levels.get(data["comp_level"], data["comp_level"].upper())

        embed = discord.Embed(
            title=f"{event_name} {level} {num}", description=description, color=color
        )

        await interaction.response.send_message(embed=embed)

    except ValueError:
        await interaction.response.send_message(
            f"Event `{event}` was not found.", ephemeral=True
        )

    except requests.exceptions.Timeout:
        await interaction.response.send_message(
            "The request to TBA timed out.", ephemeral=True
        )

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            message = f"Match `{event}_{match}` was not found."
        else:
            message = f"The TBA API returned an error (`{response.status_code}`)."

        await interaction.response.send_message(message, ephemeral=True)

    except requests.exceptions.RequestException:
        await interaction.response.send_message(
            "Could not connect to TBA.", ephemeral=True
        )

    except (KeyError, TypeError, ValueError):
        await interaction.response.send_message(
            "The match data from TBA was invalid or incomplete.", ephemeral=True
        )

    except Exception as e:
        print(f"Unexpected error in /match: {e}")

        await interaction.response.send_message(
            "Something went wrong while getting that match.", ephemeral=True
        )


@tree.command(name="getteam", description="get team details")
@app_commands.describe(team="team number")
async def getteam(interaction: discord.Interaction, team: int):
    try:
        response = requests.get(
            f"{TBA_URL}/team/frc{team}",
            timeout=10,
            headers={"X-TBA-Auth-Key": os.getenv("TBA_KEY")},
        )

        response.raise_for_status()

        data = response.json()

        embed = discord.Embed(
            title=f"Team {data['team_number']}: {data['nickname']}",
            description=data.get("name", ""),
            color=discord.Color.blurple(),
        )

        embed.add_field(name="Location", value=data.get("city", "Unknown"), inline=True)
        embed.add_field(
            name="Website", value=data.get("website", "Unknown"), inline=True
        )

        await interaction.response.send_message(embed=embed)

    except requests.exceptions.Timeout:
        await interaction.response.send_message(
            "The request to TBA timed out", ephemeral=True
        )

    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            message = f"Match `{event}_{match}` was not found"
        else:
            message = f"The TBA API returned an error (`{response.status_code}`)"

        await interaction.response.send_message(message, ephemeral=True)

    except requests.exceptions.RequestException:
        await interaction.response.send_message(
            "Could not connect to TBA", ephemeral=True
        )

    except (KeyError, TypeError, ValueError):
        await interaction.response.send_message(
            "The match data from TBA was invalid or incomplete", ephemeral=True
        )

    except Exception as e:
        print(f"Unexpected error in /match: {e}")

        await interaction.response.send_message(
            "Something went wrong while getting that match", ephemeral=True
        )


BAG_API = "https://financeapi.rkmr.dev"
BAG_SITE = "https://finance.rkmr.dev"


market_group = app_commands.Group(name="market", description="stock market commands")
tree.add_command(market_group)


@market_group.command(name="show", description="show the stock market")
async def market_info(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        response = requests.get(f"{BAG_API}/api/events", timeout=10)
        response.raise_for_status()
        event_key = response.json()["event"]["key"]

        response = requests.get(f"{BAG_API}/api/prices/{event_key}", timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return await interaction.followup.send(f"couldn't reach the market: {e}")

    openings = {}
    for point in data["points"]:
        openings.setdefault(str(point["team"]), point["before"])

    lines = [f"\u001b[2m{'Team':>6}  {'Price':>9}  {'Change':>8}\u001b[0m"]
    for team, price in sorted(data["prices"].items(), key=lambda kv: int(kv[0])):
        opening = openings.get(team, price)
        change = price / opening - 1
        color = "\u001b[32m" if change > 0 else "\u001b[31m" if change < 0 else ""
        row = f"{team:>6}  {f'${price:.2f}':>9}  {change:>+7.1%}"
        lines.append(f"{color}{row}\u001b[0m")

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.link,
            label="Open",
            url=BAG_SITE,
        )
    )

    embed = discord.Embed(
        title=f"Stocks — {data['event']['name']}",
        description="```ansi\n" + "\n".join(lines) + "\n```",
        color=discord.Color.blurple(),
    )

    await interaction.followup.send(embed=embed, view=view)


@market_group.command(name="leaderboard", description="show the stock leaderboard")
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        response = requests.get(f"{BAG_API}/api/events", timeout=10)
        response.raise_for_status()
        event_key = response.json()["event"]["key"]

        prices = requests.get(f"{BAG_API}/api/prices/{event_key}", timeout=10).json()[
            "prices"
        ]
        users = requests.get(f"{BAG_API}/api/leaderboard", timeout=10).json()["users"]
    except Exception as e:
        return await interaction.followup.send(f"couldn't reach the market: {e}")

    def net_worth(user):
        return user["cash_cents"] / 100 + sum(
            shares * prices.get(team, 0) for team, shares in user["shares"].items()
        )

    users.sort(key=lambda u: (-net_worth(u), u.get("name") or u["id"]))

    lines = [
        f"**{i}.** <@{u['id']}> — **${net_worth(u):,.2f}**"
        for i, u in enumerate(users[:50], 1)
    ]
    if len(users) > 50:
        lines.append(f"…and {len(users) - 50} more")

    embed = discord.Embed(
        title="Stocks Leaderboard",
        description="\n".join(lines) or "no players yet",
        color=discord.Color.gold(),
    )

    await interaction.followup.send(embed=embed)


@market_group.command(name="portfolio", description="show your stock portfolio")
async def portfolio(interaction: discord.Interaction):
    await interaction.response.defer()

    user_id = str(interaction.user.id)
    try:
        response = requests.get(f"{BAG_API}/api/portfolio/{user_id}", timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return await interaction.followup.send(f"couldn't reach the market: {e}")

    cash = data["cash_cents"] / 100
    shares = data["shares"]

    try:
        event_resp = requests.get(f"{BAG_API}/api/events", timeout=10)
        event_resp.raise_for_status()
        event_key = event_resp.json()["event"]["key"]

        prices_resp = requests.get(f"{BAG_API}/api/prices/{event_key}", timeout=10)
        prices_resp.raise_for_status()
        prices = prices_resp.json()["prices"]
    except Exception as e:
        return await interaction.followup.send(f"couldn't fetch prices: {e}")

    lines = [f"\u001b[2m{'Team':>6}  {'Shares':>7}  {'Value':>10}\u001b[0m"]
    total_value = cash
    for team, qty in sorted(shares.items(), key=lambda kv: int(kv[0])):
        price = prices.get(team, 0)
        value = qty * price
        total_value += value
        lines.append(f"{team:>6}  {qty:>7}  ${value:>9,.2f}")

    lines.append(f"\u001b[2m{'Cash':>6}  {'':>7}  ${cash:>9,.2f}\u001b[0m")
    lines.append(f"\u001b[1m{'Total':>6}  {'':>7}  ${total_value:>9,.2f}\u001b[0m")

    embed = discord.Embed(
        title=f"Portfolio — {interaction.user.display_name}",
        description="```ansi\n" + "\n".join(lines) + "\n```",
        color=discord.Color.blurple(),
    )

    await interaction.followup.send(embed=embed)


@market_group.command(name="buy", description="buy shares of a team")
@app_commands.describe(team="team number", shares="number of shares (1-100000)")
async def buy(interaction: discord.Interaction, team: int, shares: int):
    await interaction.response.defer()

    if shares < 1 or shares > 100000:
        return await interaction.followup.send(
            "shares must be 1-100000", ephemeral=True
        )

    user_id = str(interaction.user.id)
    try:
        response = requests.post(
            f"{BAG_API}/api/trade",
            json={"user_id": user_id, "team": team, "side": "buy", "shares": shares},
            timeout=10,
        )
        if response.status_code == 400:
            return await interaction.followup.send(
                f"trade failed: {response.json().get('detail', 'bad request')}",
                ephemeral=True,
            )
        if response.status_code == 409:
            detail = response.json().get("detail", "team has no price yet")
            return await interaction.followup.send(detail, ephemeral=True)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return await interaction.followup.send(f"trade failed: {e}", ephemeral=True)

    cash = data["cash_cents"] / 100
    await interaction.followup.send(
        f"bought **{shares}** shares of **{team}** — cash: **${cash:,.2f}**"
    )


@market_group.command(name="sell", description="sell shares of a team")
@app_commands.describe(team="team number", shares="number of shares")
async def sell(interaction: discord.Interaction, team: int, shares: int):
    await interaction.response.defer()

    if shares < 1 or shares > 100000:
        return await interaction.followup.send("invalid share number", ephemeral=True)

    user_id = str(interaction.user.id)
    try:
        response = requests.post(
            f"{BAG_API}/api/trade",
            json={"user_id": user_id, "team": team, "side": "sell", "shares": shares},
            timeout=10,
        )
        if response.status_code == 400:
            return await interaction.followup.send(
                f"trade failed: {response.json().get('detail', 'bad request')}",
                ephemeral=True,
            )
        if response.status_code == 409:
            detail = response.json().get("detail", "team has no price yet")
            return await interaction.followup.send(detail, ephemeral=True)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return await interaction.followup.send(f"trade failed: {e}", ephemeral=True)

    cash = data["cash_cents"] / 100
    await interaction.followup.send(
        f"sold **{shares}** shares of **{team}** — cash: **${cash:,.2f}**"
    )


@tree.command(name="larp", description="pester someone about larping")
async def larp(interaction: discord.Interaction):
    return await interaction.response.send_message("**Rules update: STOP LARPING**")


@tree.command(name="code", description="?????")
async def code(interaction: discord.Interaction):
    if not CODE:
        return await interaction.response.send_message(
            "Code isn't configured", ephemeral=True
        )

    masked = get_masked_code(interaction.user.id)
    print(f"WHENER TENER HUNT ALERT: {interaction.user} got code: {masked}")
    await interaction.response.send_message(masked, ephemeral=True)


import csv


@tree.command(name="scrape", description="scrape messages")
@app_commands.describe(
    start_id="ID of first message",
    end_id="ID of last message",
    channel_id="ID of channel to scrape",
)
async def scrape(
    interaction: discord.Interaction, start_id: str, end_id: str, channel_id: str
):
    await interaction.response.defer()

    try:
        start_id = int(start_id)
        end_id = int(end_id)
        channel_id = int(channel_id)
    except ValueError:
        return await interaction.followup.send("one or more IDs are invalid")

    channel = interaction.client.get_channel(channel_id)

    if channel is None:
        return await interaction.followup.send("channel not found.")

    if not isinstance(channel, discord.TextChannel):
        return await interaction.followup.send("not a text channel")

    try:
        start_message = await channel.fetch_message(start_id)
        end_message = await channel.fetch_message(end_id)
    except discord.NotFound:
        return await interaction.followup.send("couldnt find one of the messages")
    except discord.Forbidden:
        return await interaction.followup.send("check channel permissions")

    if start_message.id > end_message.id:
        start_message, end_message = end_message, start_message

    filename = "messages.csv"
    count = 0

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)

        writer.writerow(["timestamp", "author_id", "author", "content", "message_id"])

        writer.writerow(
            [
                start_message.created_at.isoformat(),
                start_message.author.id,
                str(start_message.author),
                start_message.content,
                start_message.id,
            ]
        )
        count += 1

        async for message in channel.history(
            limit=None, after=start_message, before=end_message, oldest_first=True
        ):
            writer.writerow(
                [
                    message.created_at.isoformat(),
                    message.author.id,
                    str(message.author),
                    message.content,
                    message.id,
                ]
            )

            count += 1

        writer.writerow(
            [
                end_message.created_at.isoformat(),
                end_message.author.id,
                str(end_message.author),
                end_message.content,
                end_message.id,
            ]
        )
        count += 1

    print(f"scraped {count} messages")

    await interaction.followup.send(
        f"scraped **{count} messages** from <#{channel_id}>.",
        file=discord.File(filename),
    )


@client.event
async def on_ready():
    await tree.sync()
    if not rotate_code.is_running():
        rotate_code.start()
    print(f"Logged in as {client.user}")


client.run(os.getenv("TOKEN"))
