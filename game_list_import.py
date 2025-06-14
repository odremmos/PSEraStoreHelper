import asyncio
from database import custom_list_import, sync_out_of_date, synchronize_list_data
import logging
from datetime import datetime, timezone
import argparse


logger = logging.getLogger("discord")
handler = logging.handlers.RotatingFileHandler(
    filename="import.log",
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


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", action="store_true")
    custom_games = {
        205353: "UNCHARTED™ The Nathan Drake Collection",
        205354: "UNCHARTED 4",
        221698: "Gravity Rush™ 2",
        226357: "Gravity Rush",
        232654: "Hollow Knight",
        225857: "SHADOW OF THE COLOSSUS",
        201597: "xv",
        10002100: "xvi",
        10008047: "pentiment",
        10008685: "Hi-Fi RUSH",
        203974: "shovel",
        203902: "rayman legends",
        10002648: "hades",
        10002344: "FINAL FANTASY VI",
        205354: "UNCHARTED Lost Legacy",
        10002342: "FINAL FANTASY IV",
        229480: "FINAL FANTASY VIII",
        228618: "God of War III Remastered",
        234823: "Tales of Arise",
        229066: "Granblue Fantasy: Relink",
        10005211: "Ghost Trick: Phantom Detective",
        10004480: "Like a Dragon: Ishin!",
        231819: "Control",
        10005262: "Sherlock Holmes: The Awakened",
        10000846: "Forspoken",
        225697: "kingdom hearts",
        229826: "Outer Wilds",
        10003386: "Rise of The Ronin",
        202214: "Jak and Daxter: The Precursor Legacy",
        217223: "Knack 2",
        10001815: "ARMORED CORE",
        203200: "Odin Sphere",
        232995: "Ni no Kuni: Wrath of the White Witch Remastered",
        228797: "Ni no Kuni II: Revenant Kingdom",
        221809: "Ys VIII: Lacrimosa of DANA",
        10002771: "Persona 5 Royal",
        233095: "13 Sentinels: Aegis Rim",
        228903: "A Hat in Time",
        10000669: "rift apart",
        234733: "Return of the Obra Dinn",
        234026: "The House In Fata Morgana",
        235227: "Ghost of Tsushima",
        10001235: "Kena: Bridge of Spirits",
        10000176: "Returnal",
        10002458: "The Forgotten City",
        10003533: "Sword and Fairy 7: Together Forever",
        234427: "Medievil",
        10000177: "Sackboy",
        228887: "Undertale",
        10005446: "Cocoon",
        10003808: "Deaths door",
        10004409: "Wild Arms",
        205041: "The Order: 1886",
        10002422: "Psychonauts 2",
        217641: "Root Letter",
        203706: "Resogun",
        227151: "Hellblade",
        201204: "Inquisition",
        203705: "Rogue Galaxy",
        10003382: "Persona 4 Golden",
        10004508: "VALKYRIE PROFILE: LENNETH",
        10004428: "VALKYRIE ELYSIUM",
        10004707: "Inscryption",
        234756: "Trials of Mana",
        231335: "Monkey King: Hero is back",
        205307: "Wild Arms™ 3",
        232977: "Castlevania Requiem: Symphony of the Night & Rondo of Blood",
        10008568: "Tomb Raider I-III Remastered Starring Lara Croft",
        232844: "Ketsui Deathtiny -Kizuna Jigoku Tachi",
        230138: "Valkyria Chronicles Remastered + Valkyria Chronicles 4 Bundle",
        10001956: "Tactics Ogre: Reborn",
        228209: "Final Fantasy XII The Zodiac Age",
        10005249: "Ray'z Arcade Chronology",
        10009757: "Arcade Archives Rainbow Islands",
        10000990: "Bubble Bobble 4 Friends",
        221826: "バトルガレッガ",
        216026: "Arcade Archives Bubble Bobble",
        233467: "ESP RA.DE. PSY",
        "UP0082-PPSA10664_00-0799424989786604": "XVI Expansion Pass",
        "EP0082-PPSA10665_00-ADDCONT000000300": "Rising Tide",
        10003612: "Tchia",
        10007911: "Granblue Versus Rising",
        10004698: "dd",
        10007905: "en",
        "JP9000-PPSA09382_00-UCJS101170000000": "Oreshika",
        "JP9000-PPSA06790_00-UCJS100900000000": "Resistance Retribution",
        212779: "Minecraft",
    }
    # custom_games = {208810: "Tchia"}
    # args = parser.parse_args()
    logger.info("Starting custom list")
    await custom_list_import(custom_games=custom_games, dry_run=False, force=False)
    logger.info("Starting out of date")
    await sync_out_of_date(dry_run=False, force=False)
    logger.info("Starting list synchro")
    await synchronize_list_data(dry_run=False)
    logging.info("Exit Import")


if __name__ == "__main__":
    asyncio.run(main())
