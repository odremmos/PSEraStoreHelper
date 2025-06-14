import asyncio
import base64
import datetime
import gc
import io
import json
import logging
import os
import re
import traceback
from datetime import datetime as dt
from datetime import timezone
from logging.handlers import RotatingFileHandler
from typing import Union

# import PIL.Image
import aiohttp
import cchardet
import cloudscraper

# import PIL
import requests
from aioEasyPillow import Canvas, Editor, load_image
from asyncache import cached
from bs4 import BeautifulSoup, SoupStrainer
from cachetools import TTLCache
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("discord" + f".{__name__}")


# Custom Exceptions
# class AmazonThrottle(Exception):
#    pass
#
#
# class AmazonRetryThrottle(Exception):
#    pass


class PSNBlock(Exception):
    pass


# Gets the parse of the Store page that is targeted and returns to the calling instance, if the conncetion fails it returns false
# @cached(cache=TTLCache(maxsize=50, ttl=0.5 * 24 * 60 * 60))
# @profile(stream=fp)
async def get_soup(
    sem: asyncio.Semaphore, region, link_type, next_data: bool = True, cloudflare=False
):
    # the url is build, the region is the country that gets passed, type is the last part of the store page.
    # Depending on what information or storepage is wanted  a different aspect oft the store is accessed
    # psbot_commands.link_types holds the possible values

    # async
    if sem:
        await asyncio.sleep(0.3)
        await sem.acquire()
    try:
        # cloudflare circumvention
        if cloudflare:
            url = link_type
            scraper = cloudscraper.create_scraper()
            r = scraper.get(url)
            logger.info(url)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
            else:
                logger.info(r)
                return None
        else:
            if region:
                url = "https://store.playstation.com/" + region + link_type
            else:
                url = link_type
            logger.debug(url)
            logger.debug(link_type)
            header = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OSX 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko)Chrome/71.0.3578.98 Safari/537.36"
            }
            # , allow_redirects=True
            connected = False
            timeout = 0
            while not connected:
                async with aiohttp.ClientSession(headers=header) as session:
                    async with session.get(url=url, allow_redirects=True) as response:
                        if response.status == 500:
                            connected = True
                            return
                        elif response.status == 200:
                            # If the connection was successful parse the page with lxml. Lxml is a faster parser than the default provided by BeautifulSoup
                            if next_data:
                                strainer = SoupStrainer(
                                    "script", attrs={"id": "__NEXT_DATA__"}
                                )
                                soup = BeautifulSoup(
                                    await response.text(), "lxml", parse_only=strainer
                                )
                                # logger.info(response.status)
                                connected = True
                            elif "browse" in link_type:
                                strainer = SoupStrainer(
                                    "ul", attrs={"class": "psw-grid-list psw-l-grid"}
                                )
                                soup = BeautifulSoup(
                                    await response.text(), "lxml", parse_only=strainer
                                )
                                connected = True
                            elif "famitsu" in link_type:
                                strainer = SoupStrainer(
                                    "div", attrs={"class": "col-12 col-md-12 col-lg-8"}
                                )
                                soup = BeautifulSoup(
                                    await response.text(), "lxml", parse_only=strainer
                                )
                                connected = True
                            else:
                                soup = BeautifulSoup(await response.text(), "lxml")
                                connected = True
                        elif response.status == 403:
                            raise PSNBlock("Block")
                        elif response.status == 504:
                            await asyncio.sleep(2)
                            timeout += 1
                            if timeout == 5:
                                connected = True
                        else:
                            logger.info(response)
                            connected = True
                            return None
            if sem:
                sem.release()
            return soup
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        logger.info(region, link_type, next_data)
    finally:
        # some cleanup
        del soup
        gc.collect()


# Nearly the same as above. The difference is that it targets the search page for the autocomplete
# Since this information is not too time sensitive it gets cached #
@cached(cache=TTLCache(maxsize=128, ttl=1 * 24 * 60 * 60))
# @profile(stream=fp)
async def get_search_soup(region: str, search_term: str):
    logger.debug("Method: get_search_soup")

    try:
        url = f"https://store.playstation.com/{region}/search/{search_term}"
        # logger.info(f"SearchUrl: {url}")
        logger.debug(url)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:

                    if response.status == 200:
                        strainer = SoupStrainer("script", attrs={"id": "__NEXT_DATA__"})
                        soup = BeautifulSoup(
                            await response.text(), "lxml", parse_only=strainer
                        )
                        logger.debug("Connection Successful")
                        return soup
                    else:
                        logger.error(
                            f"Request failed with status code: {response.status}"
                        )
                        return None

    except Exception as error:
        logger.error(f"Request Exception: {error}")
        logger.error(traceback.format_exc())
        return None


# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait


# Function that gets the html body via chromedriver
# chromedriver needs to be installed for it
# This is used to get the Amazon sales charts
# async def get_other_chromedriver_soup_(link: str, retry: bool = False):
#    chrome_options = webdriver.ChromeOptions()
#    chrome_options.add_argument("--headless")  # ensure GUI is off
#    chrome_options.add_argument("--no-sandbox")
#    chrome_options.add_argument("--window-size=1920,1080")
#    # chrome_options.add_argument("--window-size=3840,2160")
#    driver = webdriver.Chrome(options=chrome_options)
#
#    if "amazon" in link:
#        driver.get(link)
#        # driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.35)")
#        try:
#            element = driver.find_element(
#                By.ID,
#                "sp-cc-accept",
#            )
#            if element:
#                element.click()
#        except:
#            if "throttled" in driver.page_source:
#                if retry:
#                    return "ending"
#                else:
#                    return "retry"
#        driver.save_screenshot("1.png")
#        try:
#            element = driver.find_element(
#                By.XPATH,
#                "/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div[30]/div/div/div[1]/div[1]/span",
#            )
#            # sp-cc-accept
#            # driver.execute_script("document.body.style.zoom = '0.5'")
#            # driver.execute_script("window.scrollTo(0, document.body.scrollHeight/1.5)")
#
#            driver.execute_script("arguments[0].scrollIntoView(true)", element)
#            driver.save_screenshot("2.png")
#            WebDriverWait(driver, 10).until(
#                EC.presence_of_element_located(
#                    (
#                        By.XPATH,
#                        "/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div[40]/div/div/div[1]/div[1]/span",
#                    )
#                )
#            )
#            element = driver.find_element(
#                By.XPATH,
#                "/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div[40]/div/div/div[1]/div[1]/span",
#            )
#            driver.execute_script("arguments[0].scrollIntoView(true)", element)
#            driver.save_screenshot("3.png")
#            # driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
#            WebDriverWait(driver, 10).until(
#                EC.presence_of_element_located(
#                    (
#                        By.XPATH,
#                        "/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div[44]/div/div/div[1]/div[1]/span",
#                    )
#                )
#            )
#            element = driver.find_element(
#                By.XPATH,
#                "/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div[44]/div/div/div[1]/div[1]/span",
#            )
#            driver.execute_script("arguments[0].scrollIntoView(true)", element)
#            driver.save_screenshot("4.png")
#            # driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
#            WebDriverWait(driver, 10).until(
#                EC.presence_of_element_located(
#                    (
#                        By.XPATH,
#                        "/html/body/div[1]/div[2]/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div[46]/div/div/div[1]/div[1]/span",
#                    )
#                )
#            )
#            driver.save_screenshot("5.png")
#            # driver.implicitly_wait(4)
#            # /html/body/div[1]/div[2]/div/div/div[1]/div/div/div[2]/div[1]/div[1]/div[54]/div/div/div[1]/div[1]/span
#            element = driver.find_element(
#                By.XPATH,
#                "//*[@id='zg_banner']",
#            )
#        except Exception:
#            driver.quit()
#            return "fail"
#        driver.execute_script("arguments[0].scrollIntoView(true)", element)
#        driver.execute_script("document.body.style.zoom = '0.5'")
#        driver.save_screenshot("list_shot.png")
#        strainer = SoupStrainer("div", attrs={"data-reftag": "zg_bs_g_videogames"})
#        soup = BeautifulSoup(driver.page_source, "lxml", parse_only=strainer)
#
#    driver.quit()
#    return soup


def get_other_soup(link: str):
    # Send a GET request to the website
    url = link
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "lxml")
    return soup


# __NEXT_DATA__ is a json file on the PS Store, its content contains almost all necessary data
async def get_next_data_json(soup: BeautifulSoup, context: str = ""):
    try:
        next_data = soup.find(attrs={"id": "__NEXT_DATA__"})
        if next_data:
            json_data = json.loads(next_data.text)
        else:
            return "alien"
        return json_data
    except Exception as error:
        logger.error(error)
        logger.error(traceback.format_exc())
        logger.error(context)
        return "alien"


### Validation ###
# Validates the given Game. If by autocmplete or as string itself or as concept number it will be passed if not it returns False.
# @profile(stream=fp)
def validate_game(game: str):
    # Product Ids in the PS store are 6 Alphanumerical characters dash 9 alphanumericals low score 2 characters(usually zeros) dash and finall 16 alphanumericals
    # There are two return booleans because the first confirms its valid and the second decides if its a concept id
    if re.search("^[A-Z0-9]{6}-[A-Z0-9]{9}_[0-9]{2}-[A-Z0-9]{16}$", game):
        return True, False
    # concept ids are 8 alphanumerical characters
    # If true it is both valid and a concept id
    elif re.search(r"\b\d{6,9}\b", game):
        return True, True
    else:
        return False, False


# Quick check if a game exists on a store. Data is a json which carries information which page it is.
# If the game doesnt exist, it will be an error page.
# @profile(stream=fp)
def store_has_game(data: dict):
    try:
        if data["page"] == "/[locale]/error":
            return False
    except Exception as e:
        return False
    return True


# validates if the given key exists in the store_dict Dict. If not the method returns false and the command wont execute
# @profile(stream=fp)
def validate_storekey(key: str, store_dict: dict):
    if key.upper() in store_dict:
        return True
    else:
        return False


# Checks if the given stores are a list of stores(set)
# or if the given stores are valid stores in the store_dict
def validate_stores(
    stores: str,
    store_dict: dict,
    store_sets: bool = False,
    custom_sets: list = None,
    single: bool = False,
    id: str = "",
):

    if custom_sets and id in custom_sets:
        if not single and stores.lower() in custom_sets[id].keys():
            return True, custom_sets[id][stores.lower()]
    if store_sets:
        if not single and stores.lower() in store_sets.keys():
            return True, store_sets[stores.lower()]
    # If its a list seperated by commas it gets split
    # ANd each entry gets validated
    if not single and "," in stores:
        storelist = stores.split(",")
        return_storelist = []
        for store in storelist:
            if not validate_storekey(store, store_dict):
                return False, None
            else:
                return_storelist.append(store.upper())
        return True, return_storelist
    # No list, no set single check
    else:
        if not validate_storekey(stores, store_dict):
            return False, None
        else:
            return True, [stores.upper()]


### Data Functions ###
# checks whether a store  also has the same edition of a game as the us store
# deluxe, collectors,bundle etc. in the given dict (made of the json information)
# us_ variables -> data of the editions in the us store
# upsells -> upsell data of a non us store game
async def same_edition_exists(us_eo: str, us_et: str, upsells: dict):
    edition_exists = False
    product = ""
    for key in upsells["cache"].keys():
        if "edition" in upsells["cache"][key].keys():
            if (
                us_eo == upsells["cache"][key]["edition"]["ordering"]
                and us_et == upsells["cache"][key]["edition"]["type"]
            ):
                edition_exists = True
                product = key

    return product, edition_exists


# This function gathers information about a given game(id) and returns it as a number for bitwise operations
async def get_flags(id: str, region: str, next: str, target_region: bool):
    bits = 0
    # Does it exist in the US store?
    if not store_has_game(next):
        bits = 32
        return bits
    # Is it a concept id?
    _, is_concept = validate_game(id)
    if is_concept:
        bits += 1
    # Does it have upsell data?
    if next["props"]["pageProps"]["batarangs"]["upsells"]["text"] != "":
        bits += 2
    # Is it a different region? Default is a request for the US store every other is not
    if target_region:
        bits += 4
    # Is it concept and does it have a defaultProduct? Then it already has an SKU
    if is_concept and "apolloState" in next["props"]:
        if next["props"]["apolloState"] != "":
            if (
                next["props"]["apolloState"][f"Concept:{id}:{region}"]["defaultProduct"]
                != None
            ):
                bits += 8
        else:
            found_default = False
            sp = BeautifulSoup(
                next["props"]["pageProps"]["batarangs"]["game-title"]["text"], "lxml"
            )
            game_info = json.loads(sp.find("script").text)
            for key in game_info["cache"]:
                if key.startswith("Conce"):
                    if game_info["cache"][key]["defaultProduct"]["__ref"]:
                        found_default = True
                    break
            if found_default:
                bits += 8
            else:
                bits += 16
    # Concept but no defaultProduct
    elif is_concept:
        bits += 16
    # Product
    if not is_concept:
        bits += 64
    return bits


# Returns whether a game is a concept and gives it a fitting rpefix
def set_prefix(flags):
    if flags & 1 == 1:
        is_concept = True
        id_prefix = "Concept:"
    else:
        is_concept = False
        id_prefix = "Product:"
    return is_concept, id_prefix


# Returns the screenshots that are stored in a given games "media" property
async def get_screenshots(media):
    i = 0
    screens = [medium["url"] for medium in media if medium["role"] == "SCREENSHOT"]
    return screens


# gathers a games data
# goes through the games json and fetches all necessary data from it
# various safety measures to handle edge cases or announced games etc. which have unique or marginal data
# It goes the content of the store jsons and depending how they are build it extracts the data
# Dependding whether a game is announced, pre order or released the web pages and json files can have different muster
@cached(cache=TTLCache(maxsize=128, ttl=0.8 * 24 * 60 * 60))
async def gather_game_data(
    sem: asyncio.Semaphore,
    id: str,
    link_type: str,
    region: str = "en-us",
    target_region: str = False,
    is_gameinfo: bool = False,
):
    error_count = 0
    keep_alive = True
    while keep_alive:
        try:
            check_next_data = True
            game_dict = {}
            orig_soup = await get_soup(sem, region, link_type + id)
            if orig_soup == None:
                logger.info("No Soup")
                logger.info(region)
                logger.info(id)
                logger.info(link_type)
                return
            orig_next = await get_next_data_json(soup=orig_soup, context=id + region)
            if orig_next == "alien":
                game_dict = await gather_alien_game_data(
                    sem=sem, id=id, link_type=link_type + id, region=region
                )
                if game_dict:
                    return game_dict
                else:
                    return
            while check_next_data:
                if (
                    not orig_next
                    or "error" in orig_next["props"]["pageProps"]
                    and not is_gameinfo
                ):
                    if link_type == "/concept/" and region != "en-us":
                        region = "en-us"
                        orig_soup = await get_soup(sem, region, link_type + id)
                        orig_next = await get_next_data_json(
                            soup=orig_soup, context=id + region
                        )
                    elif link_type == "/concept/" and region != "en-us":
                        region = "en-gb"
                        orig_soup = await get_soup(sem, region, link_type + id)
                        orig_next = await get_next_data_json(
                            soup=orig_soup, context=id + region
                        )
                    else:
                        check_next_data = False
                else:
                    check_next_data = False
            if not orig_next:
                return
            flags = await get_flags(id, region, orig_next, target_region)
            is_concept, id_prefix = set_prefix(flags)

            if flags & 32 == 32:
                logger.warning("Game not in Store")
                logger.warning(region)
                logger.warning(id)
                logger.warning(link_type)
                return None
            # Gives store region, product type store link and the product id to the scraper
            if flags & 4 == 4:
                # logger.info("different store")
                sp = BeautifulSoup(
                    orig_next["props"]["pageProps"]["batarangs"]["background-image"][
                        "text"
                    ],
                    "lxml",
                )
                media = json.loads(sp.find("script").text)
                # if concept and has no upsell
                if flags & 2 == 2:
                    sp = BeautifulSoup(
                        orig_next["props"]["pageProps"]["batarangs"]["upsells"]["text"],
                        "lxml",
                    )
                    upsells = json.loads(sp.find("script").text)
                    edition_product = (
                        orig_next["props"]["apolloState"][f"{id_prefix}{id}:en-us"][
                            "defaultProduct"
                        ]["id"]
                        if is_concept
                        else f"{id_prefix}{id}"
                    )
                    us_edition_ordering = upsells["cache"][edition_product]["edition"][
                        "ordering"
                    ]
                    us_edition_type = upsells["cache"][edition_product]["edition"][
                        "type"
                    ]

                for key in media["cache"].keys():
                    if key.startswith("Concept"):
                        id = str(key.split(":")[1])
                        break
                region = target_region
                soup = await get_soup(sem, region, "/concept/" + id)
                if soup == None:
                    print("hier")
                    return
                next = await get_next_data_json(soup=soup, context=id + region)
                flags = await get_flags(id, region, next, target_region=False)
                is_concept, id_prefix = set_prefix(flags=flags)
            else:
                next = orig_next

            if not store_has_game(next):
                return None
            batarangs = next["props"]["pageProps"]["batarangs"]
            sp = BeautifulSoup(batarangs["background-image"]["text"], "lxml")
            media = json.loads(sp.find("script").text)
            sp = BeautifulSoup(batarangs["game-title"]["text"], "lxml")
            game_info = json.loads(sp.find("script").text)
            sp = BeautifulSoup(batarangs["star-rating"]["text"], "lxml")
            star = json.loads(sp.find("script").text)
            sp = BeautifulSoup(batarangs["cta"]["text"], "lxml")
            cta = json.loads(sp.find("script").text)
            if batarangs["info"]["text"] != "":
                sp = BeautifulSoup(batarangs["info"]["text"], "lxml")
                info = json.loads(sp.find("script").text)
                localized_genres = info["cache"][list(info["cache"].keys())[0]][
                    "localizedGenres"
                ]
                if not localized_genres:
                    genres = None
                else:
                    genres = ",".join(genre["value"] for genre in localized_genres)
            else:
                genres = None
            if batarangs["content-rating"]["text"] != "":
                sp = BeautifulSoup(batarangs["content-rating"]["text"], "lxml")
                content_rating = json.loads(sp.find("script").text)
                age_rating = content_rating["cache"][
                    list(content_rating["cache"].keys())[0]
                ]["contentRating"]["description"]

                age_content = ",".join(
                    [
                        content["description"]
                        for content in content_rating["cache"][
                            list(content_rating["cache"].keys())[0]
                        ]["contentRating"]["descriptors"]
                    ]
                )

            else:
                age_rating = None
                age_content = None
            if flags & 2 == 2:
                sp = BeautifulSoup(
                    next["props"]["pageProps"]["batarangs"]["upsells"]["text"], "lxml"
                )
                upsells = json.loads(sp.find("script").text)
                cta_info = upsells
            else:
                cta_info = cta

            # Is it Concept and not a game without SKU
            if is_concept:
                concept = id
                publisher = game_info["cache"]["Concept:" + concept]["publisherName"]
                if flags & 8 == 8:
                    default_product = next["props"]["apolloState"][
                        f"Concept:{id}:{region}"
                    ]["defaultProduct"]["id"]
                    default_product = default_product[:-6]
                    product = default_product.split(":")[1]
                    release_date = game_info["cache"]["Concept:" + concept][
                        "releaseDate"
                    ]["value"]
                    if release_date == None:
                        release_date = game_info["cache"]["Product:" + product][
                            "releaseDate"
                        ]

            if flags & 15 == 15:
                product, edition_exists = await same_edition_exists(
                    us_edition_type, us_edition_ordering, upsells
                )
                product = product.split(":")[1]
            # If its a product
            if not is_concept:
                product = id
                concept = None
                for key in media["cache"]:
                    if key.startswith("Concept:"):
                        concept = media["cache"][key]["id"]
                        break
                default_product = f"Product:{product}"
                publisher = game_info["cache"]["Product:" + product]["publisherName"]
                release_date = game_info["cache"]["Product:" + product]["releaseDate"]
                if release_date == None:
                    release_date = game_info["cache"]["Concept:" + concept][
                        "releaseDate"
                    ]["value"]

            if flags & 72 != 0:
                star = star["cache"][default_product]["starRating"]
                rtings_distribution = [
                    "".join(
                        [
                            re.findall(r"\d+", entry["percentage"])[0].zfill(2),
                            "%",
                        ]
                    )
                    for entry in star["ratingsDistribution"]
                ]
                starRating = {
                    "rating": star["averageRating"],
                    "ratingCount": star["totalRatingsCount"],
                    "ratingDistribution": rtings_distribution,
                }
                active_cta_id = ":".join(
                    ["GameCTA", cta_info["cache"]["Product:" + product]["activeCtaId"]]
                )
                invariant_name = cta["cache"]["Product:" + product]["invariantName"]
                name = cta_info["cache"]["Product:" + product]["name"]
                # name = (
                #    cta_info["cache"]["Product:" + product]["invariantName"]
                #    if cta_info["cache"]["Product:" + product]["invariantName"]
                #    else cta_info["cache"]["Product:" + product]["name"]
                # )
                url = "https://store.playstation.com/" + region + "/product/" + product
                master = [
                    x
                    for x in media["cache"][default_product]["media"]
                    if x["role"] == "MASTER"
                ]
                if not master or len(master) != 1:
                    cover = media["cache"][default_product]["media"][
                        len(media["cache"][default_product]["media"]) - 1
                    ]["url"]
                else:
                    cover = f"{master[0]['url']}"
                screens = await get_screenshots(
                    media["cache"][default_product]["media"]
                )
                if active_cta_id == "GameCTA:undefined:undefined":
                    price = "Not Available"
                    discounted_price = "Not Available"
                else:
                    # upsellText
                    default_price = True
                    if flags & 2 == 2:
                        if "TRIAL" in cta_info["cache"][active_cta_id]["type"]:
                            default_price = False
                            for key in cta_info["cache"]:
                                if key.startswith("GameCTA") and key != active_cta_id:
                                    if "CART" in cta_info["cache"][key]["type"]:
                                        price = cta_info["cache"][key]["price"][
                                            "basePrice"
                                        ]
                                        discounted_price = cta_info["cache"][key][
                                            "price"
                                        ]["discountedPrice"]
                                        break
                    else:
                        if (
                            cta_info["cache"][active_cta_id]["price"]["upsellText"]
                            == "Trial"
                        ):
                            default_price = False
                            for key in cta_info["cache"]:
                                if key.startswith("GameCTA") and key != active_cta_id:
                                    if (
                                        cta_info["cache"][key]["price"]["applicability"]
                                        != "UPSELL"
                                    ):
                                        price = cta_info["cache"][key]["price"][
                                            "basePrice"
                                        ]
                                        discounted_price = cta_info["cache"][key][
                                            "price"
                                        ]["discountedPrice"]
                                        break

                    if default_price:
                        price = cta_info["cache"][active_cta_id]["price"]["basePrice"]
                        discounted_price = cta_info["cache"][active_cta_id]["price"][
                            "discountedPrice"
                        ]

                platforms = game_info["cache"][default_product]["platforms"]
                top_category = game_info["cache"]["Product:" + product]["topCategory"]
                if flags & 2 == 0:
                    edition_type = None
                    edition_ordering = None
                else:
                    if upsells["cache"]["Product:" + product]["edition"]:
                        edition_ordering = upsells["cache"]["Product:" + product][
                            "edition"
                        ]["ordering"]
                        edition_type = upsells["cache"]["Product:" + product][
                            "edition"
                        ]["type"]
                    else:
                        edition_type = None
                        edition_ordering = None
            elif flags & 8 == 0:
                product = "TBA"
                name = media["cache"]["Concept:" + concept]["name"]
                starRating = {
                    "rating": "0",
                    "ratingCount": "0",
                    "ratingDistribution": ["00%", "00%", "00%", "00%", "00%"],
                }
                url = "https://store.playstation.com/" + region + "/concept/" + concept
                price = "TBA"
                discounted_price = "TBA"
                cover = media["cache"]["Concept:" + concept]["media"][
                    len(media["cache"]["Concept:" + concept]["media"]) - 1
                ]["url"]
                screens = await get_screenshots(
                    media["cache"]["Concept:" + concept]["media"]
                )
                release_date = "TBA"
                platforms = "TBA"
                top_category = "TBA"
                edition_ordering = None
                edition_type = None
                invariant_name = ""

            # stores all the gathered data in a new dict
            game_dict = {
                "concept": concept,
                "name": name,
                "product": product,
                "starRating": starRating,
                "url": url,
                "cover": cover,
                "price": price,
                "discounted_price": discounted_price,
                "date": release_date,
                "pub": publisher,
                "platforms": platforms,
                "edition_ordering": edition_ordering,
                "edition_type": edition_type,
                "screens": screens,
                "top_category": top_category,
                "invariant_name": invariant_name,
                "genres": genres,
                "age_rating": age_rating,
                "age_content": age_content,
                "region": region.split("-")[1].upper(),
            }
            # clean up
            sp = None
            soup = None
            keep_alive = False
            return game_dict
        except Exception as error:
            error_count += 1
            if error_count == 3:
                keep_alive = False
                logger.error(error)
                logger.error(traceback.format_exc())
                logger.error(f"product: {product}")
                return


def print_html_file(data):
    print(data)
    with open("output.html", "w") as file:
        file.write(data)


# formats a json file
def pretty_file(data, name: str):
    with open(name + ".txt", "w") as convert_file:
        convert_file.write(json.dumps(data, indent=4))


# tries to get the core product of a game. As in, the non deluxe or limited edition
def get_main_product(soup: BeautifulSoup):
    soup = soup.find("button", attrs={"data-qa": "inline-toast#hiddenCta"})
    product = json.loads(soup["data-telemetry-meta"])["productId"]
    return product


# announced games have a different set of data that needs to be handled
async def is_just_announced(next: dict, id: str):
    sp = BeautifulSoup(
        next["props"]["pageProps"]["batarangs"]["background-image"]["text"], "lxml"
    )
    media = json.loads(sp.find("script").text)
    product = media["cache"]["Concept:" + id]["defaultProduct"]
    sp = None
    if product == None:
        return True
    else:
        return False


# In Order to display the bestseller and preorders the various editions need to be labeled
async def get_game_product_ids(
    sem: asyncio.Semaphore, game: dict, region: str, link_type: str
):
    concept = game["concept"]
    logger.debug("get_game_product_ids")
    logger.debug(f"concept: {concept}")
    sku_letters = [
        "\U0001f535",
        "\U0001f7e1",
        "\U0001f7e2",
        "\U0001f7e3",
        "\U0001f7e4",
    ]
    skulist = []
    soup = await get_soup(sem, region, "".join([link_type, concept]))
    if soup == None:
        return
    next = await get_next_data_json(soup)
    if not next:
        return
    if not store_has_game(next) or await is_just_announced(next, concept):
        return False
    else:
        if game["top_category"] == "ADD_ON":
            sp = BeautifulSoup(
                next["props"]["pageProps"]["batarangs"]["add-ons"]["text"], "lxml"
            )
            add_ons = json.loads(sp.find("script").text)
            add_on_ids = [
                add_ons["cache"][x]["id"][0:-5]
                for x in add_ons["cache"]
                if "type" in add_ons["cache"][x]
                if add_ons["cache"][x]["type"] == "PREORDER"
            ]

            i = 0
            for product in add_on_ids:
                # variable that can be overwritten
                product_to_ow = product
                name = add_ons["cache"][f"Product:{product_to_ow}"]["invariantName"]
                found = False
                if game["product"][-16:] == product[-16:]:
                    found = True
                    logger.info("Substring")
                else:
                    if (
                        game["invariant_name"]
                        == add_ons["cache"][f"Product:{product}"]["invariantName"]
                    ):
                        logger.info("Invariant")
                        found = True
                    else:
                        possible_sku = await gather_game_data(
                            sem,
                            product,
                            "/product/",
                            region,
                        )

                        if game["date"][:7] == possible_sku["date"][:7]:
                            logger.info("Request")
                            name = (
                                possible_sku["invariant_name"]
                                if possible_sku["invariant_name"]
                                else possible_sku["name"]
                            )
                            product_to_ow = possible_sku["product"]
                            found = True
                if found:
                    sku_letter = sku_letters[i]
                    i += 1
                    skulist.append(
                        {
                            "sku": f"Product:{product_to_ow}",
                            "name": name,
                            "letter": sku_letter,
                        }
                    )
        else:
            sp = BeautifulSoup(
                next["props"]["pageProps"]["batarangs"]["upsells"]["text"], "lxml"
            )
            if next["props"]["pageProps"]["batarangs"]["upsells"]["statusCode"] == 204:
                if game["product"]:
                    if game["region"] != region.split("-")[1].upper():
                        product = next["props"]["apolloState"][
                            f"Concept:{concept}:{region}"
                        ]["defaultProduct"]["id"][:-6]
                    else:
                        product = f"Product:{game['product']}"
                    sku_letter = sku_letters[0]
                    skulist.append(
                        {
                            "sku": product,
                            "name": (
                                game["invariant_name"]
                                if game["invariant_name"]
                                else game["name"]
                            ),
                            "letter": sku_letter,
                        }
                    )
                else:
                    return
            else:

                upsells = json.loads(sp.find("script").text)
                products = upsells["cache"]["Concept:" + concept]["products"]
                i = 0
                for p in products:
                    if (
                        upsells["cache"][p["__ref"]]["topCategory"].lower() != "demo"
                        and upsells["cache"][p["__ref"]]["edition"]["name"].lower()
                        != "demo"
                    ):
                        invariant_name = upsells["cache"][p["__ref"]]["invariantName"]
                        name = (
                            invariant_name
                            if invariant_name
                            else upsells["cache"][p["__ref"]]["name"]
                        )
                        """name = (
                            upsells["cache"][p["__ref"]]["name"]
                            if region == "ja-jp"
                            else (
                                invariant_name
                                if invariant_name
                                else upsells["cache"][p["__ref"]]["name"]
                            )
                        )
                        """
                        sku_letter = sku_letters[i]
                        skulist.append(
                            {"sku": p["__ref"], "name": name, "letter": sku_letter}
                        )
                        i += 1
        soup = None
        sp = None

        return skulist


# Gets the first 5(or all if less) search resultes for the searchterm
# To be exact, this method, gets the json_data with the search results handed and looks up the data in the json
# @profile(stream=fp)
async def create_game_search_dict(region: str, json_data: dict, searchterm: str):
    logger.debug("Method: create_game_search_dict")
    region = region.split("-")
    """The JSON attribute the results are saved in is a specific key that gets build here.

    The country url component, the country key and the searchterm are combined with the prepared strings.
    """
    """_summary_

    Returns:
        _type_: _description_
    """
    try:
        querykey = "".join(
            [
                'universalSearch({"countryCode":"',
                region[1].upper(),
                '","languageCode":"',
                region[0],
                '","nextCursor":"","pageOffset":0,"pageSize":24,"searchTerm":"',
                searchterm,
                '"})',
            ]
        )
        game_dict = {}
        i = 0
        entry = False
        for result in json_data["props"]["apolloState"]["ROOT_QUERY"][querykey][
            "results"
        ]:
            # for x in range(5):
            if i == 5:
                break

            # type_name = json_data["props"]["apolloState"][result["id"]]["__typename"]
            type_name = json_data["props"]["apolloState"][result["__ref"]]["__typename"]
            # name = json_data["props"]["apolloState"][result["id"]]["name"]
            name = json_data["props"]["apolloState"][result["__ref"]]["name"]
            # game_id = result["id"]
            # game_id = json_data["props"]["apolloState"][result["__ref"]]  # ["id"]
            game_id = result["__ref"]
            classifications = [
                "FULL_GAME",
                "PREMIUM_EDITION",
                "GAME_BUNDLE",
                "ADD_ON_PACK",
                "LEVEL",
            ]

            if (
                "storeDisplayClassification"
                in json_data["props"]["apolloState"][game_id]
            ):
                entry = (
                    True
                    if json_data["props"]["apolloState"][game_id][
                        "storeDisplayClassification"
                    ]
                    in classifications
                    else False
                )

            elif type_name == "Concept":
                entry = True

            if entry:
                game_dict |= {name: game_id.split(":")[1]}
                i += 1
            entry = False

    except Exception as error:
        logger.error(error)
        logger.error(traceback.format_exc())
        pass
    return game_dict


@cached(cache=TTLCache(maxsize=300, ttl=1 * 24 * 60 * 60))
async def get_games_collection(store: str, searchterm: str):
    logger.debug("Before Search Soup")
    soup = await get_search_soup(store, searchterm)
    logger.debug("Before Get Next Data")

    json_data = await get_next_data_json(soup)
    if not json_data:
        return
    logger.debug("Before create_game_search_dict")
    search_dict = await create_game_search_dict(store, json_data, searchterm)
    soup = None
    return search_dict


# For games from non Latin using Stores this gets the western Name from the US store.
# Fetches the game from the us store
async def getWesternName(id: str, link_type: str):
    url = "https://store.playstation.com/en-us" + link_type + str(id)
    req = requests.get(url)
    soup = BeautifulSoup(req.text, features="html.parser")
    name = soup.find(attrs={"data-qa": "mfe-game-title#name"}).text
    soup = None
    return name


# Collects the best selling games from the front page
# they are in a specific strand of the next data json
@cached(cache=TTLCache(maxsize=128, ttl=0.8 * 24 * 60 * 60))
async def get_best_selling_games(sem: asyncio.Semaphore, region: str, link_type: str):
    soup = await get_soup(sem, region, link_type)
    if soup == None:
        return
    json_data = await get_next_data_json(soup)
    if not json_data:
        return
    if link_type == "/category/4dfd67ab-4ed7-40b0-a937-a549aece13d0/":
        ranking_key = "".join(
            ["CategoryGrid:4dfd67ab-4ed7-40b0-a937-a549aece13d0:", region, ":0:24"]
        )
    else:
        ranking_key = "".join(
            ["CategoryStrand:fbb563aa-c602-476d-bb92-fe7f35080205:", region, ":0:10"]
        )
    gdict = {}
    game_array = []
    x = 1
    region = region.split("-")[1].lower()
    try:
        for product in json_data["props"]["apolloState"][ranking_key]["concepts"]:
            game = json_data["props"]["apolloState"][
                product["__ref"]
            ]  # [product["id"]]
            cover_link = game["media"][len(game["media"]) - 1]["url"]
            # cover_link = json_data["props"]["apolloState"][cover_key]["url"]
            name = game["name"]
            concept = game["id"]
            game_array.append(
                {
                    "name": name,
                    "rank": x,
                    "cover": cover_link,
                    "region": region,
                    "id": concept,
                }
            )

            x = x + 1
    except KeyError as error:
        logger.error(traceback.format_exc())
        logger.error(error)
        return
    gdict[region] = game_array

    return gdict


# @profile(stream=fp)
async def check_browse_page(
    next_data: dict,
    concept: str,
    region: str,
    exclude_f2p: bool,
    pager: int,
):

    f2p_counter = 0
    returnvalue = None
    if exclude_f2p:
        f2p = load_json_file(name="f2p")
        next_concepts = next_data["props"]["apolloState"][
            f"CategoryGrid:28c9c2b2-cecc-415c-9a08-482a605cb104:{region}:{pager}:24"
        ]["concepts"]
        for entry in next_concepts:
            if entry["__ref"].split(":")[1] in f2p["concepts"]:
                f2p_counter = f2p_counter + 1
            if f"Concept:{concept}:{region}" == entry["__ref"]:
                returnvalue = next_concepts.index(entry) + 1
                break
    else:
        next_concepts = next_data["props"]["apolloState"][
            f"CategoryGrid:28c9c2b2-cecc-415c-9a08-482a605cb104:{region}:{pager}:24"
        ]["concepts"]
        concept_dict = {
            entry["__ref"]: next_concepts.index(entry) + 1 for entry in next_concepts
        }
        if f"Concept:{concept}:{region}" in concept_dict:
            returnvalue = concept_dict[f"Concept:{concept}:{region}"]
    return returnvalue, f2p_counter


# gets the top 100 selling games
# the code goes to the browse page and then loads the next few pages until the 100th game is hit
async def get_best_one_hundred_selling_games(
    sem: asyncio.Semaphore, game: dict, region: str, link_type: str, exclude_f2p: bool
):
    concept = game["concept"]
    logger.debug("get_best_one_hundred_selling_games")
    logger.debug(region)
    returnvalue = None
    soup = await get_soup(sem, region, link_type, True)

    if soup == None:
        return
    else:
        next_data = await get_next_data_json(soup)
    f2p_counter = 0
    returnvalue, f2p_counter = await check_browse_page(
        next_data, concept, region, exclude_f2p, 0
    )
    # CategoryGrid:28c9c2b2-cecc-415c-9a08-482a605cb104:de-de:0:24

    # First page was already worked through, thus we can reduce popcount by one but have to add 1 to i(since /1 was already done)
    if not returnvalue:
        j = 1
        for i in range(2, 6):
            temp_f2p_counter = 0
            soup = await get_soup(sem, region, link_type + str(i), True)
            next_data = await get_next_data_json(soup)
            returnvalue, temp_f2p_counter = await check_browse_page(
                next_data, concept, region, exclude_f2p, j * 24
            )
            j += 1
            f2p_counter += temp_f2p_counter
            if returnvalue:
                returnvalue = returnvalue + 24 * (i - 1)
                break
            i += 1
    country = region.split("-")[1]
    if not returnvalue:
        result = {
            country: [
                {
                    "name": game["name"],
                    "id": concept,
                    "rank": "-",
                    "letter": "",
                    "region": country,
                }
            ]
        }
    else:
        if exclude_f2p:
            returnvalue -= f2p_counter
        result = {
            country: [
                {
                    "name": game["name"],
                    "id": concept,
                    "rank": returnvalue,
                    "letter": "",
                    "region": country,
                }
            ]
        }
    soup = None
    return result


# checks whether a game is in the bestselling pages
# parameter are the semaphore, the game data, the region, link type and the bit operator
async def is_game_in_bestselling(
    sem: asyncio.Semaphore, game: dict, region: str, link_type: str, bits: int = 0
):
    id = game["concept"]
    exclude_f2p = True if bits & 2 == 2 else False
    # if bits is one it only fetches the top hundred
    if bits & 1 == 1:
        result = await get_best_one_hundred_selling_games(
            sem, game, region, link_type, exclude_f2p
        )
        return result
    else:
        bestsellers = await get_best_selling_games(sem, region, link_type)
    if exclude_f2p:
        f2p = load_json_file()
    f2p_counter = 0
    if bestsellers:
        country = region.split("-")[1]
        for key in bestsellers:
            for entry in bestsellers[key]:
                if exclude_f2p:
                    if entry["id"] in f2p["concepts"]:
                        f2p_counter += 1
                if id == entry["id"]:
                    entry["rank"] -= f2p_counter
                    return {country: [entry]}

        return {
            country: [
                {
                    "name": game["name"],
                    "rank": "-",
                    "cover": "",
                    "region": country,
                    "id": id,
                }
            ]
        }
    else:
        return


#
async def get_bestselling_preorders(
    sem: asyncio.Semaphore, region: str, link_type: str
):
    soup = await get_soup(sem, region, link_type)
    if soup == None:
        return
    json_data = await get_next_data_json(soup)
    if not json_data:
        return
    preorderkey = "".join(
        ["CategoryStrand:3bf499d7-7acf-4931-97dd-2667494ee2c9:", region, ":0:12"]
    )
    #  if preorderkey in key:
    game_dict = {}
    game_array = []
    x = 1
    for product in json_data["props"]["apolloState"][preorderkey]["products"]:
        game = json_data["props"]["apolloState"][product["__ref"]]  # [product["id"]]
        cover_link = game["media"][len(game["media"]) - 1]["url"]  # ["id"]
        # cover_link = json_data["props"]["apolloState"][cover_key]["url"]
        name = game["name"]
        product = game["id"]
        game_array.append(
            {
                "name": name,
                "rank": x,
                "cover": cover_link,
                "region": region.split("-")[1],
                "id": product,
            }
        )
        x += 1
    game_dict[region.split("-")[1].lower()] = game_array
    soup = None

    return game_dict


# @profile(stream=fp)
async def is_bestselling_preorder(
    region: str, json_data: dict, sku: dict, counter: int
):
    logger.debug("is_bestselling_preorder")
    found = False
    x = counter
    id_check = sku["sku"] + ":" + region
    preorderkey = "".join(
        [
            "CategoryGrid:3bf499d7-7acf-4931-97dd-2667494ee2c9:",
            region,
            ":",
            str(counter),
            ":24",
        ]
    )
    apollostate = json_data["props"]["apolloState"][preorderkey]["products"]
    for product in apollostate:
        if id_check == product["__ref"]:
            result = {
                "id": id_check,
                "name": sku["name"],
                "letter": sku["letter"],
                "rank": x + 1,
                "region": region.split("-")[1],
            }
            found = True
            break
        x += 1
    if found == True:
        return result
    else:
        return


# For a given game list it this functions checks if they a best selling preorder
async def search_for_game_in_preorders(
    sem: asyncio.Semaphore, SKU_list: list, region: str, link_type: str
):
    logger.debug("search_for_game_in_preorders")
    logger.debug(region)
    logger.debug(SKU_list)
    returnvalue = None
    soup = await get_soup(sem, region, link_type, False)
    if soup == None:
        return
    li = soup.find(
        attrs={"class": "psw-l-space-x-1 psw-l-line-center psw-list-style-none"}
    )
    pages = li.findChildren("button")
    popcount = pages[len(pages) - 1]["value"]
    json_data = await get_next_data_json(soup)
    if not json_data:
        return
    sku_list_result = []
    sku_list_length = len(SKU_list)
    for sku in SKU_list:
        returnvalue = await is_bestselling_preorder(region, json_data, sku, 0)
        if returnvalue:
            sku_list_result.append(returnvalue)

    # First page was already worked through, thus we can reduce popcount by one but have to add 1 to i(since /1 was already done)
    if len(sku_list_result) != sku_list_length:
        j = 1
        for i in range(2, int(popcount) + 1):
            # Slowing down the function as limit rate
            await asyncio.sleep(0.2)
            soup = await get_soup(sem, region, link_type + str(i))
            json_data = await get_next_data_json(soup)
            for sku in SKU_list:
                returnvalue = await is_bestselling_preorder(
                    region, json_data, sku, j * 24
                )
                if returnvalue:
                    sku_list_result.append(returnvalue)
                if len(sku_list_result) == sku_list_length:
                    break
            if len(sku_list_result) == sku_list_length:
                break
            j += 1

    if len(sku_list_result) != sku_list_length:
        for sku in SKU_list:
            result = {
                "id": sku["sku"],
                "rank": "-",
                "region": region.split("-")[1],
                "name": sku["name"],
                "letter": sku["letter"],
            }
            sku_list_result.append(result)

    soup = None
    li = None

    return sku_list_result


async def process_products(
    sem: asyncio.Semaphore, game: dict, region: str, concept_link: str
):

    logger.debug(f"function: {process_products}")
    product_link = "/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/"
    return_result = {}
    return_array = []
    SKU = await get_game_product_ids(sem, game, region, concept_link)
    if not SKU:
        logger.debug(f"region: {region}")
        logger.debug(f"NO SKU: {SKU}")
        return_array.append(
            {"id": False, "letter": "", "rank": "-", "region": region.split("-")[1]}
        )
    else:
        logger.debug(f"region: {region}")
        logger.debug(f"SKU: {SKU}")
        return_array = await search_for_game_in_preorders(
            sem, SKU, region, product_link
        )
    return_result[region.split("-")[1]] = return_array
    return return_result


# this function gets the trending games
async def get_trending_games(sem: asyncio.Semaphore, region: str, link_type: str):
    trending_key = f"EMSView:ec022651-cce6-11ee-a31f-a2110459ffc0:{region}"
    soup = await get_soup(sem, region, link_type, True)
    next = await get_next_data_json(soup=soup)
    apollo_state = next["props"]["apolloState"]
    trending_view_ids = [c["id"] for c in apollo_state[trending_key]["components"]]
    trending_dict = {}
    trending_dict_entry = {}
    trending_dict_array = []
    for id in trending_view_ids:
        ordinal = apollo_state[id]["ordinal"]
        image = apollo_state[id]["imageUrl"]
        trending_link = apollo_state[id]["link"]["id"]
        id_type = apollo_state[trending_link]["type"]
        id = apollo_state[trending_link]["target"]
        game = await get_trending_game(sem=sem, region=region, id=id, id_type=id_type)
        if game:
            id = game["concept"]
            name = game["name"]
        else:
            id = "Uknown"
            name = "Unknown"
        trending_dict_entry[ordinal] = {
            "id": id,
            "ordinal": ordinal,
            "cover": image,
            "region": region.split("-")[1],
            "type": id_type,
            "name": name,
            "rank": None,
            "trending_id": id,
        }
    ordinals = [entry for entry in trending_dict_entry]
    ordinals.sort()
    j = 1
    for i in ordinals:
        trending_dict_entry[i]["rank"] = j
        trending_dict_array.append(trending_dict_entry[i])
        j += 1
    region = region.split("-")[1]
    trending_dict[region] = trending_dict_array
    soup = None

    return trending_dict


# @profile(stream=fp)
async def get_trending_game(sem: asyncio.Semaphore, region: str, id: str, id_type: str):
    game = {}
    if id_type != "CONCEPT":
        if id_type == "EMS_CATEGORY":
            link = f"https://store.playstation.com/{region}/category/{id}/1"
            soup = await get_soup(sem=sem, region=None, link_type=link, next_data=True)
            next_data = await get_next_data_json(soup)
            key = f"CategoryGrid:{id}:{region}:0:24"
            for p in next_data["props"]["apolloState"][key]["products"]:
                p = p["id"].split(":")[1]
                game = await gather_game_data(
                    sem=sem, id=p, link_type="/product/", region=region
                )
                break
            soup = None

        else:
            game = await gather_game_data(
                sem=sem, id=id, link_type="/product/", region=region
            )

    else:
        game = await gather_game_data(
            sem=sem, id=id, link_type="/concept/", region=region
        )

    return game


async def update_message(ctx):
    pass


# This bot makes a lot of calls to the ps store and handles quite a bit of data
# this function parallelises the workload
async def async_process_data(
    store_dict: dict,
    function,
    store_list: list,
    game: dict = None,
    link_type: str = None,
    limit_rate: Union[int, bool] = False,
    top120: bool = False,
    exclude_f2p: bool = False,
    ctx=None,
):
    bits = 0
    # search in top120?
    if top120:
        bits += 1
    # exclude f2p?
    if exclude_f2p:
        bits += 2
    limit_rate = limit_rate if limit_rate else 8 if len(store_list) > 15 else 12
    results = {}
    tasks = []
    sem = asyncio.Semaphore(limit_rate)
    for store in store_list:
        if game:
            if bits > 0:
                task = asyncio.create_task(
                    function(sem, game, store_dict[store]["sub"], link_type, bits)
                )
            else:
                task = asyncio.create_task(
                    function(sem, game, store_dict[store]["sub"], link_type)
                )
            tasks.append(task)
        else:
            tasks.append(
                asyncio.create_task(function(sem, store_dict[store]["sub"], link_type))
            )
    completed_tasks = await asyncio.gather(*tasks)
    for future in completed_tasks:
        results.update(future)
    return results


async def async_import(
    auto_import: bool,
    store_list: list,
    store_dict: dict,
    link_type: str,
    function: callable,
):
    limit_rate = 4
    results = {}
    tasks = []
    sem = asyncio.Semaphore(limit_rate)
    for store in store_list:
        task = asyncio.create_task(
            function(sem=sem, region=store_dict[store]["sub"], link_type=link_type)
        )
        tasks.append(task)
    completed_tasks = await asyncio.gather(*tasks)
    for future in completed_tasks:
        results.update(future)
    return results


#### Image Functions ####


#
@cached(cache=TTLCache(maxsize=40, ttl=2 * 24 * 60 * 60))
async def procure_images(cover, i):
    try:
        url = cover
        image = await load_image(url)
        return {i: image}
    except Exception as error:
        logger.error(error)
        return {i: "NO_DATA"}


# Thus function creates the banner for the topseller
# It does this by being given the images and then creating a canvas where the cover are pasted onto
async def create_banner_image(image_dict: dict, grid_type: str):
    x = 0
    images = 0
    width = 0
    height = 0
    banner_image = None
    if grid_type == "topten" or grid_type == "preorders":
        if grid_type == "topten":
            images = 10
            banner_canvas = Canvas((102 * 5, 102 * 2), "RGB")
            banner_image = Editor(banner_canvas)
        elif grid_type == "preorders":
            images = 12
            banner_canvas = Canvas((102 * 6, 102 * 2), "RGB")
            banner_image = Editor(banner_canvas)
        resize_width = 102
        resize_height = 102
    elif grid_type == "igea" or grid_type == "sell":
        if grid_type == "igea":
            images = 10
            banner_canvas = Canvas((169 * 5, 211 * 2), "RGB")
            banner_image = Editor(banner_canvas)
        if grid_type == "sell":
            images = 5
            banner_canvas = Canvas((169 * 5, 211), "RGB")
            banner_image = Editor(banner_canvas)
        resize_width = 169
        resize_height = 211
    elif grid_type == "trending":
        images = len(image_dict)
        calc_height = (
            int(images / 6) if (images / 6).is_integer() else int(images / 6) + 1
        )
        banner_canvas = Canvas((102 * 6, 102 * calc_height), "RGB")
        banner_image = Editor(banner_canvas)
        resize_width = 102
        resize_height = 102
    elif grid_type == "famitsu":
        images = 30
        banner_canvas = Canvas((102 * 6, 102 * 5), "RGB")
        banner_image = Editor(banner_canvas)
        size = 110, 200
    for ctr in range(len(image_dict)):
        image = image_dict[ctr]
        if images == 10:
            if x == 5:
                width = 0
                height = 1
        elif images == 12:
            if x == 6:
                width = 0
                height = 1
        elif grid_type == "trending":
            if x == 6:
                x = 0
                width = 0
                height += 1

        if grid_type == "famitsu":
            if x == 6:
                x = 0
                width = 0
                height += 1
            image.thumbnail(size)
            left = 1
            top = 28
            right = 103
            bottom = 130
            image = image.crop((left, top, right, bottom))
            rs_image = Image.new("RGB", (30, 30), (220, 6, 16))
            image.paste(rs_image, (0, 0))
            draw = ImageDraw.Draw(image)
            draw.text(
                (10, 10), str(ctr + 1).zfill(2), font_size=50, fill=(255, 255, 255)
            )
        else:
            image = image.resize((resize_width, resize_height))

        await banner_image.paste(
            image,
            (image.width * width, image.height * height),
        )
        image = None
        width += 1
        x += 1
    in_mem_file = io.BytesIO()
    await banner_image.save(in_mem_file, format="PNG")
    in_mem_file.seek(0)
    img_bytes = in_mem_file.getvalue()
    base64_data = base64.b64encode(img_bytes)
    #### Clean Ram ####
    in_mem_file.flush()
    in_mem_file.close()
    del banner_image
    del in_mem_file
    del img_bytes
    del image_dict
    gc.collect()

    return base64_data


# Since Rankings have 10 or 12 games and thus images its best to use multiprocessing to speed things up.
# Method takes array of games and starts the image creation for them
@cached(cache=TTLCache(maxsize=128, ttl=0.7 * 24 * 60 * 60))
async def setup_procure_images(image_string: str, grid_type: str):
    futures = []
    results = {}

    if grid_type != "amazon":
        cover_array = image_string.split(";")
        i = 0
        for entry in cover_array:
            futures.append(procure_images(entry, i))
            i += 1
        for future in asyncio.as_completed(futures):
            results.update(await future)
        if not results or "NO_DATA" in results.values():
            return
        else:

            base64_data = await create_banner_image(results, grid_type=grid_type)
            if len(cover_array) > 3:
                await asyncio.sleep(2)

            url = await upload_to_imgur(base64_data)
            del results
            del base64_data
            gc.collect()
            if not url:
                return
            else:
                logger.info(url)
                return url
    else:
        image = Image.open(r"list_shot.png")
        # image = image.crop((340, 85, 3631, 2119))
        image = image.crop((170, 43, 1815.5, 1059.5))
        in_mem_file = io.BytesIO()
        image.save(in_mem_file, format="PNG")
        in_mem_file.seek(0)
        img_bytes = in_mem_file.getvalue()
        base64_data = base64.b64encode(img_bytes)
        # 405, 153, 3561, 2119
        url = await upload_to_imgur(base64_data)
        in_mem_file.flush()
        in_mem_file.close()
        del in_mem_file
        del img_bytes
        del base64_data
        gc.collect()
        if not url:
            return
        else:
            logger.info(url)
            return url


# uploads the created ranking banner image to imgur
@cached(cache=TTLCache(maxsize=128, ttl=0.9 * 24 * 60 * 60))
async def upload_to_imgur(base64_data: base64):
    url = "https://api.imgur.com/3/image"
    # token is taken from the token file
    with open("token.json", "r") as cfg:
        data = json.load(cfg)
    token = "Client-ID " + data["imgur_token"]
    logger.debug("upload_to_imgur")
    headers = {"Authorization": token}
    # Upload image to Imgur and get URL
    response = requests.post(url, headers=headers, data={"image": base64_data})
    logger.debug(response.text)
    if response.status_code != 200:
        logger.error(response)
        return
    else:
        url = response.json()["data"]["link"]
    return url


# @cached(cache=TTLCache(maxsize=128, ttl=3 * 24 * 60 * 60))
# def find_week_chart_from_igea(
#    link: str, target_week: int, year: int, month_number: int
# ):
#    link = f"{link}{year}/{month_number}"
#    soup = get_other_chromedriver_soup_(link)
#    inner_wrap = soup.find("div", attrs={"class": "Inner-Wrap"})
#    # wrap_children = inner_wrap.findChildren()
#    weeks = inner_wrap.find_all("h1")
#    i = 0
#    charts_dict = {}
#    charts_tags = []
#    for week in weeks:
#        if week.text == target_week:
#            au_chart_tags = week.find_next_sibling().find_next_sibling()
#            nz_chart_tags = (
#                au_chart_tags.find_next_sibling()
#                .find_next_sibling()
#                .find_next_sibling()
#            )
#            charts_tags.append(au_chart_tags)
#            charts_tags.append(nz_chart_tags)
#            # soup = BeautifulSoup(week.find_next_sibling().find_next_sibling(), "lxml")
#            charts_dict = get_igea_dict(charts_tags)
#            # charts_dict = get_igea_dict(wrap_children[i + 2].text)
#            break
#        i += 1
#    return charts_dict


# @cached(cache=TTLCache(maxsize=128, ttl=3 * 24 * 60 * 60))
## @profile(stream=fp)
# async def find_current_chart_from_igea(link: str):
#    charts_tags = []
#    charts_dict = {}
#    week = ""
#    soup = await get_soup(sem=None, region=None, link_type=link, next_data=False)
#    if soup == None:
#        return
#    for country in ["Top-Ten-AU", "Top-Ten-NZ"]:
#        country_wrap = soup.find("div", attrs={"id": country})
#        if week == "":
#            week = soup.find("h3")
#            week = week.text
#        charts_tags.append(country_wrap)
#    charts_dict = get_igea_dict(charts_tags)
#    country_wrap = None
#    soup = None
#    return charts_dict, week


## @cached(cache=TTLCache(maxsize=50 * 1024 * 1024, ttl=3 * 24 * 60 * 60))
## @profile(stream=fp)
# def get_igea_dict(soup_array: list, lookup_type: str = ""):
#    charts_dict = {}
#    countries = ["AU", "NZ"]
#    week = ""
#    # Find the div with class "charts"
#
#    for soup in soup_array:
#        table = soup.find_all("li", attrs={"class": "top-10-wrap"})
#        country_code = next(iter(countries))
#        countries.pop(0)
#        table_dict = {}
#        table_dict[country_code] = []
#        if lookup_type == "past" and week == "":
#            week = soup.find("h3")
#            week = week.text
#        for item in table:
#            image_src = item.find("img")["src"]
#            position = item.find("span").text
#            name = item.find("h3").text
#            publisher = item.find("p").text
#
#            table_dict[country_code].append(
#                {
#                    "name": name,
#                    "position": position,
#                    "publisher": publisher,
#                    "cover": image_src,
#                    "region": country_code,
#                }
#            )
#            charts_dict.update(table_dict)
#    if lookup_type == "past":
#        return charts_dict, week
#    return charts_dict


@cached(cache=TTLCache(maxsize=128, ttl=3 * 24 * 60 * 60))
async def get_current_sell_chart(link: str):
    soup = await get_soup(sem=False, region=False, link_type=link, next_data=False)
    if soup == None:
        return
    logger.debug("get_current_sell_chart - after soup")
    entry_list = soup.find(
        "div",
        attrs={"class": "top-details top-details-all top-ventes__field-classement-all"},
    ).find_all("div", attrs={"class": "field__item"})
    table_dict = {}
    table_dict["fr"] = []
    week = soup.find("option", attrs={"selected": "selected"}).text.split(" ")[1]
    for child in entry_list:
        position = child.find("div", attrs={"class": "jeu-position"}).text.strip()
        name = child.find("div", attrs={"class": "jeux__name"}).text
        platform = child.find("div", attrs={"class": "jeux__plateforme"}).text
        pub = child.find("div", attrs={"class": "jeux__field-editeur"}).text
        src = child.find("img")["src"]
        if "https://www.sell.fr" in src:
            cover = f"{src}"
        else:
            cover = f"https://www.sell.fr{src}"

        table_dict["fr"].append(
            {
                "name": name,
                "position": position,
                "publisher": pub,
                "cover": cover,
                "platform": platform,
            }
        )
    soup = None
    return table_dict, week


async def get_famitsu_sale_chart(link: str):
    soup = await get_soup(sem=False, region=False, link_type=link, next_data=False)
    if soup == None:
        return
    table_dict = {}
    table_dict["jp"] = []
    week = soup.find("span", attrs={"class": "heading__sub-text-body"}).text
    digits = re.findall(r"\d+", week)
    iso_c = datetime.date(int(digits[0]), int(digits[1]), int(digits[2])).isocalendar()
    iso_week = iso_c[1]
    written_week, _ = get_iso_week(iso_c[0], iso_week)

    data = soup.find("div", attrs={"class": "row border-col-bottom"})
    games = data.find_all(
        "div",
        attrs={
            "class": "card card-game-sale-rank card-game-sale-rank--col-12 card-game-sale-rank--col-sm-12 card-game-sale-rank--col-md-12 card-game-sale-rank--col-lg-8"
        },
    )

    for game in games:
        title = game.find("div", attrs={"class": "card-game-sale-rank__title"}).text
        position = game.find(
            "span", attrs={"class": "icon-ranking icon-ranking--primary"}
        ).text
        cover = game.find("div", attrs={"class": "card-game-sale-rank__media-inner"})
        cover = f"https:{cover.find('div')['data-src']}"
        weekly_sales = game.find(
            "p",
            attrs={
                "class": "card-game-sale-rank__sales-num-past card-game-sale-rank__sales-num"
            },
        ).text[:-1]
        overall_sales = (
            game.find(
                "p",
                attrs={
                    "class": "card-game-sale-rank__sales-num-total card-game-sale-rank__sales-num"
                },
            )
            .text[:-1]
            .split(":")[1]
        )
        stock = game.find(
            "span", attrs={"class": "card-game-sale-rank__sales-meter-num"}
        ).text
        pub = game.find(
            "p",
            attrs={
                "class": "card-game-sale-rank__publisher card-game-sale-rank__sub-info"
            },
        ).text
        price = game.find(
            "p",
            attrs={"class": "card-game-sale-rank__price card-game-sale-rank__sub-info"},
        ).text
        platform = game.find(
            "li",
            attrs={"class": "card-game-sale-rank__status-item"},
        )
        platform = platform.find("span").text

        table_dict["jp"].append(
            {
                "name": title,
                "position": position,
                "publisher": pub,
                "cover": cover,
                "platform": platform,
                "weeklysales": weekly_sales,
                "overallsales": overall_sales,
                "stock": stock,
                "price": price,
                "iso_week": iso_week,
            }
        )
    data = None
    soup = None
    return table_dict, written_week


# Functions for the Amazon command
# It simply scrapes the Amazon Website
# async def get_amazon_soup(link: str, region: str, retry: bool = False):
#    soup = await get_other_chromedriver_soup_(link, retry=retry)
#    return soup


# async def get_amazon_chart(soup: BeautifulSoup, region: str):
#    items = soup.find_all("div", attrs={"id": "gridItemRoot"})
#    amazon_dict = {}
#    amazon_array = []
#    for item in items:
#        position = item.find("span").text.replace("#", "")
#        spans = item.find_all("span")
#        for span in spans:
#            name = span.find("div")
#            if name:
#                name = name.text
#                break
#        try:
#            pub = (
#                item.find("span", attrs={"class": "a-size-small a-color-base"})
#                .find("div")
#                .text
#            )
#        except AttributeError:
#            pub = ""
#        icon_row = item.find("div", attrs={"class": "a-icon-row"})
#        try:
#            score = icon_row.find("span", attrs={"class": "a-icon-alt"}).text
#
#            score = re.findall(r"\d+", score)
#            score = f"{score[0]}.{score[1]}"
#        except AttributeError:
#            score = ""
#        try:
#            reviews = (
#                icon_row.find("a").find("span", attrs={"class": "a-size-small"}).text
#            )
#            reviews = reviews.replace("\xa0", "")
#
#        except AttributeError:
#            reviews = ""
#
#        cover = item.find("img")["src"]
#
#        amazon_array.append(
#            {
#                "position": position,
#                "name": name,
#                "pub": pub,
#                "score": score,
#                "reviews": reviews,
#                "cover": cover,
#            }
#        )
#    amazon_dict[region] = amazon_array
#    soup = None
#
#    return amazon_dict


# Functions for the ESRB command
# It simply scrapes the ESRB Website
def create_esrb_dict(soup: BeautifulSoup):
    game_array = []
    i = 0
    for game in soup:
        if i == 5:
            break
        game_data = {}
        game_data["link"] = game.select_one(".heading h2 a")["href"]
        game_data["title"] = game.select_one(".heading h2 a").text
        game_data["platforms"] = game.select_one(
            ".heading .platforms"
        ).text  # .replace("\n", ",")

        rating_info = game.select(".content table tr")[1]
        game_data["rating"] = rating_info.select("td img")[0]["alt"]
        game_array.append(game_data)
        i += 1
    return game_array


def get_esrb_data(soup):
    game_data = {}
    game_data["title"] = soup.select_one(".col h1").text
    game_data["pub"] = soup.select_one(".col .subtitle").text
    game_data["platforms"] = soup.select_one(".platforms .platforms-txt").text
    game_data["content_descriptors"] = soup.select_one(".info-txt .description").text
    game_data["summary"] = soup.select_one(".summary-txt").text.replace("\t", "")
    return game_data


# A quick function to get a timestamp
def get_iso_week(year, week):
    first_day = dt.fromisocalendar(year, week, 1)
    month_number = first_day.strftime("%m")
    first_day = first_day.strftime("%B %d %Y")
    last_day = dt.fromisocalendar(year, week, 7).strftime("%B %d %Y")
    return f"{first_day} – {last_day}", month_number


def read_aliases_json(id: str):
    with open("aliases.json", "r+") as file:
        file_data = json.load(file)
        if id in file_data:
            return True, file_data[id]
        else:
            return False, None


def load_custom_sets():
    with open("aliases.json", "r+") as file:
        file_data = json.load(file)
        logger.debug(file_data)
        return file_data


# A function to export the various commands in a json or csv file
def export_data(data: dict, file_format: str, command: str):
    column_row = ""
    timestamp = datetime.datetime.now(timezone.utc)  # .isoformat()
    hash_id = hash(str(timestamp))
    iso_week = timestamp.isocalendar()[1]
    timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    game_info = False
    if file_format == "csv":
        keys = list(data.keys())
        first_key = keys[0]
        data_list = list(data[first_key])
        if type(data_list[0]) == str:
            for attribute in data[first_key]:
                if type(data[first_key][attribute]) == dict:
                    columns = ";".join(list(data[first_key][attribute].keys()))
                    column_row += columns + ";"
                else:
                    column_row += f"{attribute};"
            column_row = column_row[:-1]
            # column_row = ";".join(data_list)
            game_info = True
        else:
            column_row = ";".join(data_list[0].keys())

        # column_row = ";".join(list(data[list(data.keys())[0]][0].keys()))
        column_row += f";Timestamp;Timestamp ISO Week;Hash ID"
        rows.append(column_row)
        row = ""
        for key in data:
            if game_info:
                for attribute in data[key]:
                    value = data[key][attribute]
                    if type(value) == dict:

                        for entry in value:
                            if type(value[entry]) == list:
                                for sub_entry in value[entry]:
                                    row += f"{sub_entry},"
                                row = row[:-1]
                                row = row + ";"
                            else:
                                row += f"{value[entry]};"
                    elif type(value) == list:
                        for entry in value:
                            row += f"{entry},"
                        row = row[:-1]
                        row = row + ";"
                        # row += f'"{value}";'
                    else:
                        # print(value)
                        row += f"{value};"
                row = row[:-1]
                row = ";".join([row, str(timestamp), str(iso_week), str(hash_id)])
                rows.append(row)
            else:
                for entry in data[key]:
                    row = ";".join(map(str, list(entry.values())))
                    row = ";".join([row, str(timestamp), str(iso_week), str(hash_id)])
                    rows.append(row)
        file_name = "".join([str(timestamp), "_", command, ".csv"])
        with open(file_name, "w") as file:
            for row in rows:
                file.write("".join(row) + "\n")
    elif file_format == "json":
        for key in data:
            if type(data[key]) == list:
                for entry in data[key]:
                    entry["timestamp"] = str(timestamp)
                    entry["tsisoweek"] = iso_week
                    entry["hashid"] = hash_id
            else:
                data[key]["timestamp"] = str(timestamp)
                data[key]["tsisoweek"] = iso_week
                data[key]["hashid"] = hash_id
        file_name = "".join([str(timestamp), "_", command, ".json"])
        with open(file_name, "w") as file:
            file.write(json.dumps(data, indent=4, ensure_ascii=False))
    return file_name


# This saves the created aliases to the lias file
def save_to_aliases_json(id: str, alias: str):
    with open("aliases.json", "r+") as file:
        file_data = json.load(file)
        if id in file_data:
            if len(file_data[id]) < 5 and next(iter(alias)) not in file_data[id].keys():
                file_data[id].update(alias)
                file.seek(0)
                json.dump(file_data, file, indent=4)
                return (
                    True,
                    f"Alias {next(iter(alias))} with values {alias[next(iter(alias))]} added.",
                )
            elif len(file_data[id]) <= 5 and next(iter(alias)) in file_data[id].keys():
                file_data[id].update(alias)
                file.seek(0)
                json.dump(file_data, file, indent=4)
                return (
                    True,
                    f"Updated alias {next(iter(alias))} with values {alias[next(iter(alias))]}.",
                )
            else:
                return False, "Allocated number of Aliases reached"
        else:
            file_data[id] = alias
            file.seek(0)
            json.dump(file_data, file, indent=4)
            return True, "User and alias added"


# The
async def save_free_to_play_to_file(link_type):
    return_v = await get_best_selling_games(False, "en-us", link_type=link_type)
    with open("f2p.json", "r+") as file:
        file_data = json.load(file)
        for key in return_v:
            for entry in return_v[key]:
                if entry["id"] not in file_data["concepts"]:
                    file_data["concepts"].append(entry["id"])
        file.seek(0)
        json.dump(file_data, file, indent=4)


# The import is for an attempt at building a database with the store information
async def get_data_for_bestsellers_import(
    sem: asyncio.Semaphore, region: str, link_type: str, end_page: int = 8
):
    run = True
    error_counter = 0
    while run:
        try:
            game_array = []
            import_dict = {}
            x = 1
            for page in range(1, end_page):
                soup = await get_soup(
                    sem=sem,
                    region=region,
                    link_type=link_type + str(page),
                    next_data=True,
                )
                next_data = await get_next_data_json(soup)
                next_concepts = next_data["props"]["apolloState"][
                    f"CategoryGrid:28c9c2b2-cecc-415c-9a08-482a605cb104:{region}:{(page-1)*24}:24"
                ]["concepts"]
                for entry in next_concepts:
                    game = next_data["props"]["apolloState"][entry["id"]]
                    cover_key = game["media"][len(game["media"]) - 1]["id"]
                    cover_link = next_data["props"]["apolloState"][cover_key]["url"]
                    name = game["name"]
                    concept = game["id"]
                    try:
                        product = game["products"][0]["id"].split(":")[1]
                    except:
                        product = None

                    game_array.append(
                        {
                            "name": name,
                            "rank": x,
                            "cover": cover_link,
                            "region": region,
                            "id": concept,
                            "first_product": product,
                        }
                    )
                    x += 1
            import_dict[region.split("-")[1].upper()] = game_array
            run = False

        except Exception as e:
            logger.warning(e)
            logger.warning(traceback.format_exc())
            error_counter += 1
            if error_counter == 3:
                run = False
                import_dict[region.split("-")[1].upper()] = "Error"
            await asyncio.sleep(15)
    return import_dict


# The import is for an attempt at building a database with the store information
async def get_data_for_preorders_import(
    sem: asyncio.Semaphore, region: str, link_type: str, end_page: int = 9
):
    run = True
    error_counter = 0
    while run:
        try:
            game_array = []
            import_dict = {}
            soup = await get_soup(sem, region, link_type, False)
            if soup == None:
                return
            li = soup.find(
                attrs={"class": "psw-l-space-x-1 psw-l-line-center psw-list-style-none"}
            )
            pages = li.findChildren("button")
            popcount = pages[len(pages) - 1]["value"]

            x = 1
            for page in range(1, int(popcount) + 1):
                soup = await get_soup(sem, region, link_type + str(page), True)
                next_data = await get_next_data_json(soup)
                next_concepts = next_data["props"]["apolloState"][
                    f"CategoryGrid:3bf499d7-7acf-4931-97dd-2667494ee2c9:{region}:{(page-1)*24}:24"
                ]["products"]

                for product in next_concepts:
                    game = next_data["props"]["apolloState"][product["id"]]
                    cover_key = game["media"][len(game["media"]) - 1]["id"]
                    cover_link = next_data["props"]["apolloState"][cover_key]["url"]
                    name = game["name"]
                    product = game["id"]
                    game_array.append(
                        {
                            "name": name,
                            "rank": x,
                            "cover": cover_link,
                            "region": region,
                            "id": product,
                        }
                    )
                    x += 1

            import_dict[region.split("-")[1].upper()] = game_array
            run = False
        except Exception as e:
            logger.warning(e)
            error_counter += 1
            if error_counter == 3:
                run = False
                import_dict[region.split("-")[1].upper()] = "Error"
            await asyncio.sleep(3)
    li = None
    soup = None
    return import_dict


# There are few game pages on the store that are in a different muster or have different data in the json files
# This function attempts to gather data from these pages
async def gather_alien_game_data(
    sem: asyncio.Semaphore, id: str, link_type: str, region: str
):
    try:
        running = True
        no_data = 0
        soup = await get_soup(
            sem=sem, region=region, link_type=link_type, next_data=False
        )

        region_split = region.split("-")
        box_game = soup.find("div", attrs={"class": "box game-hero__title-content"})
        if not box_game:
            body = soup.body
            data_product_info = body.get("data-product-info")
            if not data_product_info:
                data_product_info = body.get("data-game-info")
                if not data_product_info:
                    return

            json_data = json.loads(data_product_info)
            concept = json_data["conceptId"]
            product = json_data["productId"]
            release_date = json_data["releaseDate"]
            top_category = json_data["productType"]
            if top_category == "FULL_GAME":
                top_category = "GAME"

            if "image" not in json_data:
                image_script = soup.find("span", attrs={"id": "buynow"}).find("script")
                image_json_data = json.loads(image_script.text)
                media = image_json_data["cache"][f"Product:{product}"]["media"]
                cover = [x["url"] for x in media if x["role"] == "MASTER"][0]
            else:
                cover = json_data["image"]
            publisher = json_data["publisher"]
            name = json_data["name"]
            invariant_name = None
            screens = None
            platforms = json_data["platforms"]
            if len(platforms) == 0:
                platforms = soup.find(attrs={"name": "platforms"})["content"]
                if "," in platforms:
                    platforms = platforms.split(",")
                else:
                    platforms = [platforms]
            age_rating = (
                soup.find(attrs={"name": "contentRating"})["content"]
                if soup.find(attrs={"name": "contentRating"})
                else None
            )
            genres = soup.find(attrs={"name": "genres"})["content"]
            url = f"https://store.playstation.com/{region}/product/{product}"
            edition_ordering = None
            edition_type = None
            rating = "?"
            rating_count = "?"
            try:
                price = soup.find("span", attrs={"class": "psw-t-title-m"}).text
            except Exception as e:
                price = None

            star_rating = {
                "rating": rating,
                "ratingCount": rating_count,
                "ratingDistribution": ["?%", "?%", "?%", "?%", "?%"],
            }

            age_content = None

            # box game-hero__title-content
            # env:fff7b280-f9a4-11ee-b1a4-f92160df5b7f
            # env:675f6de0-f9dd-11ee-a98e-338b4d6d6dfa
            # env:c6d38ed0-e3a0-11ee-b12b-a50425e2163a
        else:

            script = box_game.find_all("script")[1]
            json_data = json.loads(script.text)
            # .find("script")

            if "conceptId" in json_data["args"]:
                concept = json_data["args"]["conceptId"]
                cache = json_data["cache"]
                product = cache[f"Concept:{id}"]["defaultProduct"]["__ref"].split(":")[
                    1
                ]
                release_date = cache[f"Concept:{id}"]["releaseDate"]["value"]
                script = soup.find("span", attrs={"id": "buynow"}).find("script")
                json_data = json.loads(script.text)
                product_reference = json_data["cache"][f"Product:{product}"]
                top_category = product_reference["topCategory"]
                media = product_reference["media"]
                cover = [x["url"] for x in media if x["role"] == "MASTER"][0]
                screens = await get_screenshots(media=media)
                publisher = soup.find(attrs={"name": "publisher"})["content"]
                platforms = soup.find(attrs={"name": "platforms"})["content"]
                platforms = [platforms]
            else:
                product = json_data["args"]["productId"]
                cache = json_data["cache"]

                for key in cache:
                    if key.startswith("Concept"):
                        concept = cache[key]["id"]
                        break
                try:
                    release_date_script = soup.find(
                        "div", attrs={"class": "gameInformation"}
                    ).find("script")
                    r_d = json.loads(release_date_script.text)
                    for key in r_d["cache"]:
                        if key.startswith("Product:"):
                            release_date = r_d["cache"][key]["releaseDate"]
                            break
                    top_category = r_d["cache"][key]["type"]
                    publisher = r_d["cache"][key]["publisherName"]
                    platforms = []
                    # platform-badge
                    platform_badges = soup.find(
                        "div", attrs={"class": "platform-badge"}
                    ).find_all("span")
                    for entry in platform_badges:
                        platforms.append(entry.text)

                except:
                    top_category = soup.find(attrs={"name": "productType"})["content"]
                    release_date = soup.find(attrs={"name": "releaseDate"})["content"]
                    publisher = soup.find(attrs={"name": "publisher"})["content"]
                    platforms = soup.find(attrs={"name": "platforms"})["content"]
                    platforms = [platforms]
                screens = None
            # json_text = json.loads(json_text.find("script").text)
            game_dict = {}
            # concept = json_data["args"]["conceptId"]
            try:
                cover = soup.find(attrs={"property": "og:image"})["content"]
            except:
                cover = soup.find(attrs={"name": "image"})["content"]
            cache_product = cache[f"Product:{product}"]
            invariant_name = cache_product["invariantName"]
            name = cache_product["name"]
            cta_id = cache_product["webctas"][0]["__ref"]
            cta = cache[f"{cta_id}"]
            price = cta["price"]["basePrice"]
            try:
                footer = soup.find("div", attrs={"class": "game-hero__footer"}).find(
                    "script"
                )
                footer_data = json.loads(footer.text)
                for key in footer_data["cache"]:
                    if key.startswith("Product:") or key.startswith("Concept:"):
                        age_rating = footer_data["cache"][key]["contentRating"][
                            "description"
                        ]
                        descriptors = footer_data["cache"][key]["contentRating"][
                            "descriptors"
                        ]
                        desc_arr = []
                        for scriptor in descriptors:
                            desc_arr.append(scriptor["description"])
                        break
                age_content = ",".join(desc_arr)
            except:
                age_rating = soup.find(attrs={"name": "contentRating"})["content"]
                age_content = None

            try:
                genres = soup.find(attrs={"name": "genres"})["content"]
            except:
                genres = None
            url = f"https://store.playstation.com/{region}/product/{product}"
            edition_ordering = None
            edition_type = None
            rating = "?"
            rating_count = "?"

            star_rating = {
                "rating": rating,
                "ratingCount": rating_count,
                "ratingDistribution": ["?%", "?%", "?%", "?%", "?%"],
            }

        game_dict = {
            "concept": concept,
            "name": name,
            "product": product,
            "starRating": star_rating,
            "url": url,
            "cover": cover,
            "price": price,
            "discounted_price": None,
            "date": release_date,
            "pub": publisher,
            "platforms": platforms,
            "edition_ordering": edition_ordering,
            "edition_type": edition_type,
            "screens": screens,
            "top_category": top_category,
            "invariant_name": invariant_name,
            "genres": genres,
            "age_rating": age_rating,
            "age_content": age_content,
            "region": region.split("-")[1].upper(),
        }

        soup = None

        return game_dict

    except Exception as e:
        logger.error(e)
        logger.error(id)
        logger.error(link_type)
        logger.error(region)
        logger.error(traceback.format_exc())
        return


async def waste_disposal(items: list):
    for item in items:
        del item
    gc.collect()


# Deletes the create export files
def delete_file(file: str):
    os.remove(file)


# Small function to open json files
def load_json_file(name: str):
    with open(f"{name}.json", "r+") as file:
        file_data = json.load(file)
    return file_data


if __name__ == "__main__":
    exit()
