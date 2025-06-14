import datetime
import json
import logging
import math
from enum import Enum

from psnawp_api import PSNAWP
from psnawp_api.core import psnawp_exceptions

logger = logging.getLogger("discord" + "." + __name__)
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(
    filename="discord.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


async def gather_data_from_api(product, region, store_sets):
    if region in store_sets["am"]:
        account_id = "2832596588443796732"
    elif region == "DE":
        account_id = "7483949895300500506"
    elif region == "FR":
        account_id = "8982354720274779799"
    elif region == "GB":
        account_id == "7532533859249281768"
    elif region in store_sets["eu"]:
        account_id = "5763876686885923346"
    elif region in store_sets["asia"]:
        account_id = "6515971742264256071"
    with open("token.json", "r") as cfg:
        data = json.load(cfg)
    psnawp = PSNAWP(data["ps_api_token"])
    game_id = product.split("-")[1]
    try:
        source_user = psnawp.user(account_id=account_id)
        title = psnawp.game_title(game_id, account_id=source_user.account_id)
        return title
    except Exception:
        return


async def get_user_data(user):
    user_data = {}
    with open("token.json", "r") as cfg:
        data = json.load(cfg)
    psnawp = PSNAWP(data["ps_api_token"])
    try:
        user = psnawp.user(online_id=user)
    except psnawp_exceptions.PSNAWPNotFound:
        message = f"Did not find: {user}"
        return None, message
    profile = user.profile()

    try:
        presence = user.get_presence()
        logger.debug(presence)
        last_seen = (
            presence["basicPresence"]["lastAvailableDate"]
            if "lastAvailableDate" in presence["basicPresence"]
            else presence["basicPresence"]["primaryPlatformInfo"]["lastOnlineDate"]
        )
        online_status = (
            presence["basicPresence"]["primaryPlatformInfo"]["onlineStatus"]
            if presence["basicPresence"]["primaryPlatformInfo"]["onlineStatus"]
            == "online"
            else None
        )
    except psnawp_exceptions.PSNAWPForbidden:
        logger.info("Title Stats Error")
        last_played = None
        online_status = None
        last_seen = None

    try:
        title_stats = list(user.title_stats(limit=1))
        last_played = title_stats[0].name
    except psnawp_exceptions.PSNAWPForbidden:
        logger.info("Title Stats Error")
        last_played = None
    except psnawp_exceptions.PSNAWPServerError:
        try:
            title_stats = list(user.title_stats(limit=1))
            last_played = title_stats[0].name
        except psnawp_exceptions.PSNAWPServerError:
            last_played = None
    except Exception as error:
        logger.error(error)
        last_played = None
    try:
        trophies = user.trophy_summary()
        trophy_level = trophies.trophy_level
        bronzes = trophies.earned_trophies.bronze
        silvers = trophies.earned_trophies.silver
        golds = trophies.earned_trophies.gold
        plat = trophies.earned_trophies.platinum
        trophies_sum = bronzes + silvers + golds + plat
    except psnawp_exceptions.PSNAWPForbidden:
        logger.info("Trophy Summary")
        trophy_level = None
        bronzes = None
        silvers = None
        golds = None
        plat = None
        trophies_sum = None

    user_data = {
        "name": profile["onlineId"],
        "avatar": profile["avatars"][0]["url"],
        "plus": profile["isPlus"],
        "last_seen": last_seen,
        "trophy_level": trophy_level,
        "bronze": bronzes,
        "silver": silvers,
        "gold": golds,
        "plat": plat,
        "trophies_sum": trophies_sum,
        "last_played": last_played,
        "online_status": online_status,
    }
    return user_data, ""


async def get_user_trophies(user, interaction):
    user_data = {}
    with open("token.json", "r") as cfg:
        data = json.load(cfg)
    psnawp = PSNAWP(data["ps_api_token"])
    try:
        user = psnawp.user(online_id=user)
    except psnawp_exceptions.PSNAWPNotFound:
        await interaction.response.send_message(
            content=f"Did not find: {user}", ephemeral=True
        )
        return
    profile = user.profile()
    logger.debug(profile)
    try:
        title_stats = list(user.title_stats(limit=1))
        last_played = title_stats[0].name
    except psnawp_exceptions.PSNAWPForbidden:
        logger.info("Title Stats Error")
        last_played = None
    try:
        trophies = user.trophy_summary()
        trophy_level = trophies.trophy_level
        bronzes = trophies.earned_trophies.bronze
        silvers = trophies.earned_trophies.silver
        golds = trophies.earned_trophies.gold
        plat = trophies.earned_trophies.platinum
        trophies_sum = bronzes + silvers + golds + plat
    except psnawp_exceptions.PSNAWPForbidden:
        logger.info("Trophy Summary")
        trophy_level = None
        bronzes = None
        silvers = None
        golds = None
        plat = None
        trophies_sum = None

    user_data = {
        "name": profile["onlineId"],
        "avatar": profile["avatars"][0]["url"],
        "plus": profile["isPlus"],
        "last_seen": last_seen,
        "trophy_level": trophy_level,
        "bronze": bronzes,
        "silver": silvers,
        "gold": golds,
        "plat": plat,
        "trophies_sum": trophies_sum,
        "last_played": last_played,
        "online_status": online_status,
    }
    return user_data


def ago(t):
    """
    Calculate a '3 hours ago' type string from a python datetime.
    https://gist.github.com/tonyblundell/2652369
    """
    units = {
        "days": lambda diff: diff.days,
        "hours": lambda diff: diff.seconds / 3600,
        "minutes": lambda diff: diff.seconds % 3600 / 60,
    }
    diff = datetime.datetime.now() - t
    for unit in units:
        dur = units[unit](diff)  # Run the lambda function to get a duration
        if dur > 0:
            unit = (
                unit[:-dur] if dur == 1 else unit
            )  # De-pluralize if duration is 1 ('1 day' vs '2 days')
            return "%s %s ago" % (math.floor(dur), unit)
    return "just now"


if __name__ == "__main__":
    exit()
