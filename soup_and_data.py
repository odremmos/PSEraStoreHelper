import concurrent
import json
import logging
import os
import re
import shutil

import cachetools
import cchardet
import requests
from bs4 import BeautifulSoup, SoupStrainer
from PIL import Image

from psbot_commands import link_types

logger = logging.getLogger("discord" + __name__)
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
# Global

session = requests.session()


# Soup Functions ###


# Searches the provided webpage parse for the element with the ID __NEXT_DATA__. This is the script/JSON that holds most store information
##It then gets loaded as JSON and returned to the calling isntance
def get_next_data_json(soup):
    [result] = [res for res in soup.find(attrs={"id": "__NEXT_DATA__"})]
    json_data = json.loads(result)
    return json_data


# Gets the parse of the Store page that is targeted and returns to the calling instance, if the conncetion fails it returns false
def get_soup(region, type_, next_data=True):
    # the url is build, the region is the country that gets passed, type is the last part of the store page.
    # Depending on what information or storepage is wanted  a different aspect oft the store is accessed
    # psbot_commands.link_types holds the possible values
    url = "https://store.playstation.com/" + region + type_
    # logger.info(url)
    # session is global and the method is supposed to use the global variable
    global session
    # if the session was closed open a new one
    if session == None:
        session = requests.session()
    req = session.get(url)

    if req.status_code == 200:
        # If the connection was successful parse the page with lxml. Lxml is a faster parser than the default provided by BeautifulSoup
        if next_data:
            strainer = SoupStrainer("script", attrs={"id": "__NEXT_DATA__"})
            soup = BeautifulSoup(req.text, "lxml", parse_only=strainer)
        else:
            soup = BeautifulSoup(req.text, "lxml")
    else:
        logger.info(req.status_code)
        return False
    return soup


# Nearly the smae as above. The difference is that it targets the search page for the autocomplete
# Since this information is not too time sensitive it gets cached
@cachetools.cached(
    cache=cachetools.TTLCache(maxsize=50 * 1024 * 1024, ttl=3 * 24 * 60 * 60)
)
def get_search_soup(region, search_term):
    # logger.debug("Method: get_search_soup")

    try:
        url = f"https://store.playstation.com/{region}/search/{search_term}"
        # logger.info(f"SearchUrl: {url}")
        global session
        if session is None:
            session = requests.session()

        with session.get(url) as req:
            # logger.debug(req.status_code)

            if req.status_code == 200:
                strainer = SoupStrainer("script", attrs={"id": "__NEXT_DATA__"})
                soup = BeautifulSoup(req.text, "lxml", parse_only=strainer)
                # ogger.debug("Connection Successful")
                return soup
            else:
                # logger.error(f"Request failed with status code: {req.status_code}")
                return None

    except requests.RequestException as error:
        # logger.error(f"Request Exception: {error}")
        return None


### Validation ###
# Validates the given Game. If by autocmplete or as string itself or as concept number it will be passed if not it returns False.
def validate_game(game):
    # Product Ids in the PS store are 6 Alphanumerical characters dash 9 alphanumericals low score 2 characters(usually zeros) dash and finall 16 alphanumericals
    # There are two return booleans because the first confirms its valid and the second decides if its a concept id
    if re.search("[A-Z0-9]{6}-[A-Z0-9]{9}_[0-9]{2}-[A-Z0-9]{16}$", game):
        return True, False
    # concept ids are 8 alphanumerical characters
    # If true it is both valid and a concept id
    elif re.search("^[0-9]*$", game):
        return True, True
    else:
        return False, False


# Quick check if a game exists on a store. Data is a json which carries information which page it is.
# If the game doesnt exist, it will be an error page.
def store_has_game(data):
    if data["page"] == "/[locale]/error":
        return False
    return True


# validates if the given key exists in the storedict Dict. If not the method returns false and the command wont execute
def validate_storekey(key, storedict):
    if key.upper() in storedict:
        return True
    else:
        return False


def validate_stores(stores: str, storedict, store_sets, single=False):
    if not single and stores.lower() in store_sets.keys():
        return True, store_sets[stores.lower()]
    elif not single and "," in stores:
        storelist = stores.split(",")
        return_storelist = []
        for store in storelist:
            if not validate_storekey(store, storedict):
                return False, None
            else:
                return_storelist.append(store.upper())
        return True, return_storelist
    else:
        if not validate_storekey(stores, storedict):
            return False, None
        else:
            return True, [stores.upper()]


### Data Functions ###


def gather_game_data(id, link_type, region="en-us"):
    sgamedict = {}
    announced = False
    is_concept = False
    different_store = False

    if link_type == "/concept/":
        is_concept = True
    if region != "en-us":
        different_store = True
    # Gives store region, product type store link and the product id to the scraper
    if different_store:
        main_soup = get_soup("en-us", link_type + id)
        next = get_next_data_json(main_soup)
        sp = BeautifulSoup(
            next["props"]["pageProps"]["batarangs"]["background-image"]["text"], "lxml"
        )
        media = json.loads(sp.find("script").text)
        for key in media["cache"].keys():
            if key.startswith("Concept"):
                id = key.split(":")[1]
                break
        # id = media['cache'][list(media['cache'])[0]]['id']
        soup = get_soup(region, link_types["concept"] + id)
        is_concept = True
    else:
        soup = get_soup(region, link_type + id)
    next = get_next_data_json(soup)
    if not store_has_game(next):
        return False
    sp = BeautifulSoup(
        next["props"]["pageProps"]["batarangs"]["background-image"]["text"], "lxml"
    )
    media = json.loads(sp.find("script").text)
    sp = BeautifulSoup(next["props"]["pageProps"]["batarangs"]["cta"]["text"], "lxml")
    cta = json.loads(sp.find("script").text)
    sp = BeautifulSoup(
        next["props"]["pageProps"]["batarangs"]["game-title"]["text"], "lxml"
    )
    game_info = json.loads(sp.find("script").text)
    sp = BeautifulSoup(
        next["props"]["pageProps"]["batarangs"]["star-rating"]["text"], "lxml"
    )
    star = json.loads(sp.find("script").text)
    if is_concept:
        product = media["cache"]["Concept:" + id]["defaultProduct"]  # ['__ref']
        if product != None:
            product = product["__ref"]
            product = product.split(":")[1]
            concept = id
        else:
            announced = True
            concept = id

    else:
        product = id
        concept = media["cache"][list(media["cache"])[0]]["id"]
    if not announced:
        star = star["cache"]["Product:" + product]["starRating"]
        rtings_distribution = [
            entry["percentage"] for entry in star["ratingsDistribution"]
        ]
        starRating = {
            "rating": star["averageRating"],
            "ratingCount": star["totalRatingsCount"],
            "ratingDistribution": rtings_distribution,
        }
        active_cta_id = ":".join(
            ["GameCTA", cta["cache"]["Product:" + product]["activeCtaId"]]
        )
        name = cta["cache"]["Product:" + product]["name"]
        url = "https://store.playstation.com/" + region + "/product/" + product
        cover = (
            media["cache"]["Product:" + product]["media"][
                len(media["cache"]["Product:" + product]["media"]) - 1
            ]["url"]
            + "?thumb=true"
        )
        price = cta["cache"][active_cta_id]["price"]["basePrice"]
        platforms = game_info["cache"]["Product:" + product]["platforms"]
        if is_concept == False:
            release_date = game_info["cache"]["Product:" + product]["releaseDate"]
            if release_date == None:
                release_date = game_info["cache"]["Concept:" + concept]["releaseDate"][
                    "value"
                ]
        else:
            release_date = game_info["cache"]["Concept:" + concept]["releaseDate"][
                "value"
            ]
            if release_date == None:
                release_date = game_info["cache"]["Product:" + product]["releaseDate"]
    else:
        product = "TBA"
        name = media["cache"]["Concept:" + concept]["name"]
        starRating = {
            "rating": "0",
            "ratingCount": "0",
            "ratingDistribution": ["0%", "0%", "0%", "0%", "0%"],
        }
        url = "https://store.playstation.com/" + region + "/concept/" + concept
        price = "TBA"
        cover = (
            media["cache"]["Concept:" + concept]["media"][
                len(media["cache"]["Concept:" + concept]["media"]) - 1
            ]["url"]
            + "?thumb=true"
        )
        release_date = "TBA"
        platforms = "TBA"
    if is_concept == False:
        publisher = game_info["cache"]["Product:" + product]["publisherName"]
    else:
        publisher = game_info["cache"]["Concept:" + concept]["publisherName"]

    sgamedict = {
        "concept": concept,
        "name": name,
        "product": product,
        "starRating": starRating,
        "url": url,
        "cover": cover,
        "price": price,
        "date": release_date,
        "pub": publisher,
        "platforms": platforms,
    }
    return sgamedict


def get_main_product(soup):
    soup = soup.find("button", attrs={"data-qa": "inline-toast#hiddenCta"})
    product = json.loads(soup["data-telemetry-meta"])["productId"]
    return product


def get_game_product_ids(concept, region):
    skulist = []
    soup = get_soup(region, "".join([link_types["concept"], concept]))
    next = get_next_data_json(soup)
    if not store_has_game(next):
        return False
    else:
        sp = BeautifulSoup(
            next["props"]["pageProps"]["batarangs"]["upsells"]["text"], "lxml"
        )
        if next["props"]["pageProps"]["batarangs"]["upsells"]["statusCode"] == 204:
            return 204
        else:
            upsells = json.loads(sp.find("script").text)
            products = upsells["cache"]["Concept:" + concept]["products"]
            for i in products:
                skulist.append(i["__ref"])

        return skulist


# Gets the first 5(or all if less) search resultes for the searchterm
# To be exact, this method, gets the json_data with the search results handed and looks up the data in the json
# @lru_cache()
def create_game_search_dict(region, json_data, searchterm):
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
                '$ROOT_QUERY.universalSearch({"countryCode":"',
                region[1].upper(),
                '","languageCode":"',
                region[0],
                '","nextCursor":"","pageOffset":0,"pageSize":24,"searchTerm":"',
                searchterm,
                '"})',
            ]
        )
        sgamedict = {}
        search_results = len(json_data["props"]["apolloState"][querykey]["results"])
        if search_results < 5:
            search_range = search_results
        else:
            search_range = 5
        sgamedict = {
            json_data["props"]["apolloState"][
                json_data["props"]["apolloState"][querykey]["results"][x]["id"]
            ]["name"]: json_data["props"]["apolloState"][querykey]["results"][x][
                "id"
            ].split(
                ":"
            )[
                1
            ]
            for x in range(search_range)
        }
    except Exception as error:
        logger.error(error)
    return sgamedict


def get_games_collection(store, searchterm):
    logger.debug("Before Search Soup")
    soup = get_search_soup(store, searchterm)
    logger.debug("Before Get Next Data")
    json_data = get_next_data_json(soup)
    logger.debug("Before create_game_search_dict")
    return create_game_search_dict(store, json_data, searchterm)


def getWesternName(id, type_):
    type_ = "concept"
    url = "https://store.playstation.com/en-us" + link_types[type_] + str(id)
    req = requests.get(url)
    soup = BeautifulSoup(req.text, features="html.parser")
    name = soup.find(attrs={"data-qa": "mfe-game-title#name"}).text
    return name


def get_best_selling_games(region):
    soup = get_soup(region, link_types["topten"])
    json_data = get_next_data_json(soup)
    toptenkey = "".join(
        ["CategoryStrand:fbb563aa-c602-476d-bb92-fe7f35080205:", region, ":0:10"]
    )
    gamearray = []
    x = 1

    for product in json_data["props"]["apolloState"][toptenkey]["concepts"]:
        game = json_data["props"]["apolloState"][product["id"]]
        cover_key = game["media"][len(game["media"]) - 1]["id"]
        cover_link = json_data["props"]["apolloState"][cover_key]["url"] + "?thumb=true"
        name = game["name"]
        concept = game["id"]
        gamearray.append(
            {
                "name": name,
                "rank": x,
                "cover": cover_link,
                "region": region.split("-")[1].lower(),
                "id": concept,
            }
        )
        x = x + 1
    return gamearray


def is_game_in_bestselling(region, id):
    tenbestsellers = get_best_selling_games(region)
    logger.info(type(tenbestsellers))
    for entry in tenbestsellers:
        logger.info(id)
        logger.info(entry["id"])
        if id == entry["id"]:
            return entry
    return {"id": id, "rank": "N/A", "region": region.split("-")[1]}


def get_bestselling_preorders(region, link_type):
    soup = get_soup(region, link_type)
    json_data = get_next_data_json(soup)
    preorderkey = "".join(
        ["CategoryStrand:3bf499d7-7acf-4931-97dd-2667494ee2c9:", region, ":0:12"]
    )
    # for key in json_data['props']['apolloState'].keys():
    #  if preorderkey in key:
    gamearray = []
    x = 1
    # message = ''.join([':flag_',region.split('-')[1].lower(),': ','\n'])
    for product in json_data["props"]["apolloState"][preorderkey]["products"]:
        game = json_data["props"]["apolloState"][product["id"]]
        cover_key = game["media"][len(game["media"]) - 1]["id"]
        cover_link = json_data["props"]["apolloState"][cover_key]["url"] + "?thumb=true"
        name = game["name"]
        country = region.split("-")[1].lower()
        gamearray.append(
            {"name": name, "rank": x, "cover": cover_link, "region": country}
        )
        x += 1
    return gamearray


def is_bestselling_preorder(region, json_data, id, counter):
    found = False
    x = counter
    # result = {}
    id_check = id + ":" + region
    preorderkey = "".join(
        [
            "CategoryGrid:3bf499d7-7acf-4931-97dd-2667494ee2c9:",
            region,
            ":",
            str(counter),
            ":24",
        ]
    )
    # performance ^
    apollostate = json_data["props"]["apolloState"][preorderkey]["products"]
    for product in apollostate:
        if id_check == product["id"]:
            # result[id] = {'rank':x+1,'region':region.split('-')[1]}
            result = {"id": id_check, "rank": x + 1, "region": region.split("-")[1]}
            found = True
            break
        x += 1

    if found == True:
        return result, x
    else:
        return False, x


def search_for_game_in_preorders(sku, region):
    counter = 0
    returnvalue = None
    soup = get_soup(region, link_types["preorder"], False)
    li = soup.find(
        attrs={"class": "psw-l-space-x-1 psw-l-line-center psw-list-style-none"}
    )
    pages = li.findChildren("button")
    popcount = pages[len(pages) - 1]["value"]
    json_data = get_next_data_json(soup)
    returnvalue, counter = is_bestselling_preorder(region, json_data, sku, counter)

    # First page was already worked through, thus we can reduce popcount by one but have to add 1 to i(since /1 was already done)
    if not returnvalue:
        for i in range(int(popcount) - 1):
            i += 2
            soup = get_soup(region, link_types["preorder"] + str(i))
            json_data = get_next_data_json(soup)
            returnvalue, counter = is_bestselling_preorder(
                region, json_data, sku, counter
            )
            if returnvalue:
                break
    if not returnvalue:
        result = {"id": sku, "rank": "N/A", "region": region.split("-")[1]}
        return result
    return returnvalue


def process_products(concept, region):
    result = []
    SKU = get_game_product_ids(concept, region)
    if SKU == False:
        result.append({"id": False, "rank": "N/A", "region": region.split("-")[1]})
    else:
        for s in SKU:
            result.append(search_for_game_in_preorders(s, region))
    return result


def procure_images(game):
    global session
    if session == None:
        session = requests.session()
    url = game["cover"]
    file_path = "./images/" + str(game["rank"]).zfill(2) + "img.png"
    response = session.get(url, stream=True)
    with open(file_path, "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response


def create_banner_image():
    dir_path = "./images"
    files = [os.path.join(dir_path, file) for file in os.listdir(dir_path)]
    x = 0
    images = 0
    width = 0
    height = 0
    banner_image = None
    # os.path.join(dir_path, file_path)
    files.sort()
    if len(files) < 12:
        images = 10
        banner_image = Image.new("RGB", (102 * 5, 102 * 2))
    else:
        images = 12
        banner_image = Image.new("RGB", (102 * 6, 102 * 2))

    for file in files:
        # check if current file_path is a file
        if os.path.isfile(file):
            # add filename to list
            if file.endswith(".png"):
                current_image = Image.open(file)
                if images == 10:
                    if x == 5:
                        width = 0
                        height = 1
                elif images == 12:
                    if x == 6:
                        width = 0
                        height = 1
                banner_image.paste(
                    current_image,
                    (current_image.width * width, current_image.height * height),
                )
                width += 1
                x += 1
            os.remove(file)
    banner_image.save("./images/banner.png")


# Since Rankings have 10 or 12 games and thus images its best to use multiprocessing to speed things up.
# Method takes array of games and starts the image creation for them
def setup_procure_images(game_array):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for entry in game_array:
            future = executor.submit(procure_images, entry)
    create_banner_image()


# uploads the created ranking banner image to imgur
def upload_to_imgur():
    url = "https://api.imgur.com/3/image"
    # token is taken from the token file
    with open("token.json", "r") as cfg:
        data = json.load(cfg)
    token = "Client-ID " + data["imgur_token"]
    logger.info("upload_to_imgur")
    headers = {"Authorization": token}
    import base64

    # Read image file and encode as base64
    with open("./images/banner.png", "rb") as file:
        data = file.read()
    # delete the created image
    os.remove("./images/banner.png")
    base64_data = base64.b64encode(data)
    # Upload image to Imgur and get URL
    response = requests.post(url, headers=headers, data={"image": base64_data})
    url = response.json()["data"]["link"]
    return url
