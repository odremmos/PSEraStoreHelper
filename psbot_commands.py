import asyncio
import copy
import datetime as dt
import logging
import re
import traceback
import typing
from collections import Counter
from datetime import datetime, timezone

import babel.numbers
import discord
from discord import app_commands
from discord.ext import commands, tasks
from howlongtobeatpy import HowLongToBeat, HowLongToBeatEntry

from async_soup_and_data import (  # AmazonRetryThrottle,; AmazonThrottle,; display_top,; get_amazon_chart,; get_amazon_soup,; find_current_chart_from_igea,
    async_process_data,
    create_esrb_dict,
    delete_file,
    export_data,
    gather_game_data,
    get_best_selling_games,
    get_bestselling_preorders,
    get_current_sell_chart,
    get_esrb_data,
    get_famitsu_sale_chart,
    get_games_collection,
    get_iso_week,
    get_soup,
    get_trending_games,
    is_game_in_bestselling,
    load_custom_sets,
    load_json_file,
    process_products,
    save_to_aliases_json,
    setup_procure_images,
    validate_game,
    validate_stores,
    waste_disposal,
)

logger = logging.getLogger("discord" + f".{__name__}")

# Global variables or variables that act with the purpose of a global variable
storeicon = "https://i.imgur.com/aZHNia4.png"
store_dict = {
    "JP": {"name": "Japan", "sub": "ja-jp", "key": "JP", "flag": "🇯🇵"},
    "KR": {"name": "Korea", "sub": "ko-kr", "key": "KR", "flag": "🇰🇷"},
    "US": {"name": "United States", "sub": "en-us", "key": "US", "flag": "🇺🇸"},
    "GB": {"name": "United Kingdom", "sub": "en-gb", "key": "GB", "flag": "🇬🇧"},
    "FR": {"name": "France", "sub": "fr-fr", "key": "FR", "flag": "🇫🇷"},
    "DE": {"name": "Germany", "sub": "de-de", "key": "DE", "flag": "🇩🇪"},
    "HK": {"name": "Hong Kong", "sub": "en-hk", "key": "HK", "flag": "🇭🇰"},
    "AU": {"name": "Australia", "sub": "en-au", "key": "AU", "flag": "🇦🇺"},
    "TW": {"name": "Taiwan", "sub": "en-tw", "key": "TW", "flag": "🇹🇼"},
    "AR": {"name": "Argentina", "sub": "es-ar", "key": "AR", "flag": "🇦🇷"},
    "AT": {"name": "Austria", "sub": "de-at", "key": "AT", "flag": "🇦🇹"},
    "BH": {"name": "Bahrain", "sub": "en-bh", "key": "BH", "flag": "🇧🇭"},
    "BE": {"name": "Belgium", "sub": "fr-be", "key": "BE", "flag": "🇧🇪"},
    "BO": {"name": "Bolivia", "sub": "es-bo", "key": "BO", "flag": "🇧🇴"},
    "BR": {"name": "Brasil", "sub": "pt-br", "key": "BR", "flag": "🇧🇷"},
    "BG": {"name": "Bulgaria", "sub": "en-bg", "key": "BG", "flag": "🇧🇬"},
    "CA": {"name": "Canada", "sub": "en-ca", "key": "CA", "flag": "🇨🇦"},
    "CL": {"name": "Chile", "sub": "es-cl", "key": "CL", "flag": "🇨🇱"},
    "CO": {"name": "Colombia", "sub": "es-co", "key": "CO", "flag": "🇨🇴"},
    "CR": {"name": "Costa Rica", "sub": "es-cr", "key": "CR", "flag": "🇨🇷"},
    "HR": {"name": "Croatia", "sub": "en-hr", "key": "HR", "flag": "🇭🇷"},
    "CY": {"name": "Cyprus", "sub": "en-cy", "key": "CY", "flag": "🇨🇾"},
    "CZ": {"name": "Czech Republic", "sub": "en-cz", "key": "CZ", "flag": "🇨🇿"},
    "DK": {"name": "Denmark", "sub": "en-dk", "key": "DK", "flag": "🇩🇰"},
    "EC": {"name": "Ecuador", "sub": "es-ec", "key": "EC", "flag": "🇪🇨"},
    "SV": {"name": "El Salvador", "sub": "es-sv", "key": "SV", "flag": "🇸🇻"},
    "FI": {"name": "Finland", "sub": "en-fi", "key": "FI", "flag": "🇫🇮"},
    "GR": {"name": "Greece", "sub": "en-gr", "key": "GR", "flag": "🇬🇷"},
    "GT": {"name": "Guatemala", "sub": "es-gt", "key": "GT", "flag": "🇬🇹"},
    "HN": {"name": "Honduras", "sub": "es-hn", "key": "HN", "flag": "🇭🇳"},
    "HU": {"name": "Hungary", "sub": "en-hu", "key": "HU", "flag": "🇭🇺"},
    "IS": {"name": "Iceland", "sub": "en-is", "key": "IS", "flag": "🇮🇸"},
    "IN": {"name": "India", "sub": "en-in", "key": "IN", "flag": "🇮🇳"},
    "ID": {"name": "Indonesia", "sub": "en-id", "key": "ID", "flag": "🇮🇩"},
    "IE": {"name": "Ireland", "sub": "en-ie", "key": "IE", "flag": "🇮🇪"},
    "IL": {"name": "Israel", "sub": "en-il", "key": "IL", "flag": "🇮🇱"},
    "IT": {"name": "Italy", "sub": "it-it", "key": "IT", "flag": "🇮🇹"},
    "KW": {"name": "Kuwait", "sub": "en-kw", "key": "KW", "flag": "🇰🇼"},
    "LB": {"name": "Lebanon", "sub": "en-lb", "key": "LB", "flag": "🇱🇧"},
    "LU": {"name": "Luxembourg", "sub": "de-lu", "key": "LU", "flag": "🇱🇺"},
    "MY": {"name": "Malaysia", "sub": "en-my", "key": "MY", "flag": "🇲🇾"},
    "MT": {"name": "Malta", "sub": "en-mt", "key": "MT", "flag": "🇲🇹"},
    "MX": {"name": "Mexico", "sub": "es-mx", "key": "MX", "flag": "🇲🇽"},
    "NL": {"name": "Nederland", "sub": "nl-nl", "key": "NL", "flag": "🇳🇱"},
    "NZ": {"name": "New Zealand", "sub": "en-nz", "key": "NZ", "flag": "🇳🇿"},
    "NI": {"name": "Nicaragua", "sub": "es-ni", "key": "NI", "flag": "🇳🇮"},
    "NO": {"name": "Norway", "sub": "en-no", "key": "NO", "flag": "🇳🇴"},
    "OM": {"name": "Oman", "sub": "en-om", "key": "OM", "flag": "🇴🇲"},
    "PA": {"name": "Panama", "sub": "es-pa", "key": "PA", "flag": "🇵🇦"},
    "PY": {"name": "Paraguay", "sub": "es-py", "key": "PY", "flag": "🇵🇾"},
    "PE": {"name": "Peru", "sub": "es-pe", "key": "PE", "flag": "🇵🇪"},
    "PL": {"name": "Poland", "sub": "en-pl", "key": "PL", "flag": "🇵🇱"},
    "PT": {"name": "Portugal", "sub": "pt-pt", "key": "PT", "flag": "🇵🇹"},
    "QA": {"name": "Qatar", "sub": "en-qa", "key": "QA", "flag": "🇶🇦"},
    "RO": {"name": "Romania", "sub": "en-ro", "key": "RO", "flag": "🇷🇴"},
    "SA": {"name": "Saudi Arabia", "sub": "en-sa", "key": "SA", "flag": "🇸🇦"},
    "SG": {"name": "Singapore", "sub": "en-sg", "key": "SG", "flag": "🇸🇬"},
    "SI": {"name": "Slovenia", "sub": "en-si", "key": "SI", "flag": "🇸🇮"},
    "SK": {"name": "Slovakia", "sub": "en-sk", "key": "SK", "flag": "🇸🇰"},
    "ZA": {"name": "South Africa", "sub": "en-za", "key": "ZA", "flag": "🇿🇦"},
    "ES": {"name": "Spain", "sub": "es-es", "key": "ES", "flag": "🇪🇸"},
    "SE": {"name": "Sweden", "sub": "en-se", "key": "SE", "flag": "🇸🇪"},
    "CH": {"name": "Switzerland", "sub": "de-ch", "key": "CH", "flag": "🇨🇭"},
    "TH": {"name": "Thailand", "sub": "en-th", "key": "TH", "flag": "🇹🇭"},
    "TR": {"name": "Turkey", "sub": "en-tr", "key": "TR", "flag": "🇹🇷"},
    "UA": {"name": "Ukraine", "sub": "uk-ua", "key": "UA", "flag": "🇺🇦"},
    "AE": {
        "name": "United Arab Emirates/ Middle East",
        "sub": "en-ae",
        "key": "AE",
        "flag": "🇦🇪",
    },
    "UY": {"name": "Uruguay", "sub": "es-uy", "key": "UY", "flag": "🇺🇾"},
}

store_sets = {
    "plato": ["US", "JP", "GB", "FR", "ES", "PT", "DE", "BR", "KR", "IN"],
    "ww": list(store_dict.keys()),
    "asia": ["SG", "ID", "JP", "KR", "IN", "TW", "TH", "MY", "HK"],
    "eu": [
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "FI",
        "FR",
        "DE",
        "HU",
        "IS",
        "IE",
        "IT",
        "LU",
        "MT",
        "NO",
        "PL",
        "PT",
        "RO",
        "SI",
        "SK",
        "ES",
        "SE",
        "CH",
        "NL",
        "GB",
        "UA",
    ],
    "am": [
        "AR",
        "BO",
        "BR",
        "CA",
        "CL",
        "CO",
        "CR",
        "EC",
        "SV",
        "HN",
        "MX",
        "NI",
        "PA",
        "PE",
        "US",
        "UY",
    ],
    "ameo": ["NZ", "AU", "BH", "IL", "KW", "LB", "OM", "QA", "ZA", "TR", "AE", "AR"],
}
custom_sets = {}

# Link types are stored here to reduce redundancy in the code
link_types = {
    "preorder": "/category/3bf499d7-7acf-4931-97dd-2667494ee2c9/",
    "f2p": "/category/4dfd67ab-4ed7-40b0-a937-a549aece13d0/",
    "product": "/product/",
    "concept": "/concept/",
    "topten": "/pages/latest",
    "120": "/pages/browse/",
    "search": "/search/",
    "base": "https://store.playstation.com",
    "sell": "https://www.sell.fr/",
    "igea": "https://igea.net/",
    "esrb_search": "https://www.esrb.org/search/?searchKeyword=",
    "fam_this": "https://www.famitsu.com/ranking/game-sales/",
    "fam_last": "https://www.famitsu.com/ranking/game-sales/last_week/",
    "fam_before": "https://www.famitsu.com/ranking/game-sales/before_last/",
}
# 1430
time = dt.time(hour=17, minute=13, tzinfo=timezone.utc)


# A lot of the following functions simply create and fill the various Discord Embeds


# This functions spreads the data in the fields of the constructed Discord embed
async def spread_results_in_fields(
    embed: discord.Embed,
    results: dict,
    store_list: list,
    category_type: str = "toplist",
):
    i = 0
    field_index = 0
    message = ""
    sku_dict = {}
    lenofresults = len(results)
    third_inline = True
    avg_sku = 0  #
    none_hit_counter = 0
    spread = [[], []]
    spread[0] = []
    spread[1] = []

    if category_type == "preorder":
        sku_counter = [
            len(results[key]) for key in results if results[key][0]["rank"] != "-"
        ]
        if len(sku_counter) != 0:
            avg_sku = sum(sku_counter) / len(sku_counter)
        else:
            avg_sku = 1
        # Orange,White,Red
        sku_letters_rev = ["\U0001f7e0", "\U000026aa", "\U0001f534"]
    position_occurences = Counter(
        [
            entry["rank"]
            for key in results
            for entry in results[key]
            if entry["rank"] in [1, 2, 3]
        ]
    )

    for store in store_list:
        multi_sku = False
        result = results[store.lower()]
        country = result[0]["region"]
        len_of_result = len(result)
        if len_of_result > 1 or category_type == "preorder":
            sku_amount = len_of_result
            multi_sku = True
            j = 0
            for sku in result:
                if sku_amount > avg_sku:
                    result[j]["letter"] = sku_letters_rev[0]
                    sku["letter"] = sku_letters_rev[0]
                    sku_letters_rev.pop(0)
                    j += 1
                if "name" in sku:
                    if sku["letter"] not in sku_dict:
                        sku_dict.update({sku["letter"]: sku["name"]})
            logger.debug(result)
            message += f":flag_{country}: "
            message += "".join(
                (
                    f' {str(entry["rank"]).zfill(2)} {entry["letter"]}'
                    if entry["rank"] != "-"
                    else f" None"
                )
                for entry in sorted(result, key=lambda result: result["rank"])
            )
        else:
            if type(result[0]["rank"]) == str:
                none_hit_counter += 1
            else:
                message += "".join([":flag_", country, ": "])
                message += "".join([str(result[0]["rank"]).zfill(2), "  "])
        if type(result[0]["rank"]) == int:
            i += 1
        if (
            i == 4 or store == store_list[len(store_list) - 1] and message != ""
        ) and not multi_sku:
            i = 0
            message += "\n"
            spread[field_index].append(message)
            message = ""
            if lenofresults >= 12:
                field_index += 1
        elif multi_sku:
            message += "\n"
            spread[field_index].append(message)
            message = ""
            if lenofresults >= 12:
                field_index += 1
        if field_index == 2:
            field_index = 0
    embed_dict = embed.to_dict()
    embed_dict.update({"fields": []})
    position_message = ""
    for j in range(1, 4):
        occu = position_occurences[j]
        if occu > 0:
            position_message += f"{str(occu).zfill(2)} #{j} Positions\n"

    if len(spread[0]) > 0:
        embed_dict["fields"].append({"inline": True, "name": "\u200b", "value": ""})
        field_message = "".join(spread[0])
        embed_dict["fields"][0]["value"] = "".join(["**", field_message, "**"])
    if lenofresults >= 12 and len(spread[1]) > 0:
        embed_dict["fields"].append({"inline": True, "name": "\u200b", "value": ""})
        field_message = "".join(spread[1])
        embed_dict["fields"][1]["value"] = "".join(["**", field_message, "**"])
    if position_message != "":
        embed_dict["fields"].append({"inline": True, "name": "\u200b", "value": ""})
        embed_dict["fields"][len(embed_dict["fields"]) - 1]["value"] = position_message

    if multi_sku == True or category_type == "preorder":
        description = "\n".join(
            [f"{letter}: {name}" for letter, name in sku_dict.items()]
        )
        embed_dict["description"] = description
    else:
        if none_hit_counter > 0:
            description = f"Either not available or outside scope in {none_hit_counter}"
            # description += f"\n\n{ranking_description}"
            embed_dict["description"] = description
    return discord.Embed.from_dict(embed_dict)


async def validate_input(game: str, stores: str, id: str = "", single: bool = False):
    valid_stores, store_list = validate_stores(
        stores, store_dict, store_sets, custom_sets, single, id
    )
    valid_game, is_concept = validate_game(game)
    message = ""
    invalid = False
    if not valid_game:
        invalid = True
        message = "False Input: Game\nIf you used direct input be sure to remove any additional characters from the id.\nAlternatively the chosen SKU doesnt have an active store page."
    if not valid_stores:
        invalid = True
        message += "\nFalse Input: Stores\nAccepted formats: Autocomplete choices,2 Letter country code single or comma seperated or valid aliases."

    if invalid == True:
        return False, message, is_concept

    return True, store_list, is_concept


async def validate_custom_alias_data(
    alias: str, stores: str, store_dict: str, store_sets: list
):
    if len(alias) <= 4:
        valid_stores, store_list = validate_stores(stores, store_dict, store_sets)
        message = ""
        if not valid_stores:
            message += "\nFalse Input: Stores"
            return False, False, message
        else:
            return valid_stores, store_list, "Valid"
    else:
        return False, False, "Please choose an alias that has 4 or less characters."


def generate_embeds(
    title: str,
    message: str,
    is_multi: bool = False,
    imgur_url: str = "",
    country: str = "",
    url_type: str = "",
):
    try:
        if url_type == "topten":
            component = "pages/browse"
            col = 0xEC3440
        elif url_type == "preorders":
            component = "category/3bf499d7-7acf-4931-97dd-2667494ee2c9/1"
            col = 0x228B22
        elif url_type == "trending":
            component = "pages/latest"
            col = 0x783D19

        embed = discord.Embed(
            title=title,
            color=col,
            description=message,
            timestamp=datetime.now(),
        )
        embed.set_footer(
            text=title,
            icon_url=storeicon,
        )
        if not is_multi:

            store_url = f"https://store.playstation.com/{store_dict[country.upper()]['sub']}/{component}"
            embed_dict = embed.to_dict()
            embed_dict["url"] = store_url
            embed = discord.Embed.from_dict(embed_dict)
            if imgur_url:
                embed.set_image(url=imgur_url)
            embed.set_thumbnail(
                url="".join(["https://flagcdn.com/w40/", country.lower(), ".png"])
            )
        return embed
    except Exception as error:
        logger.error(traceback.format_exc())
        logger.error(error)


async def process_top_lists(
    results: dict,
    title: str,
    store_list: str,
    imageonly: bool = False,
    url_type: str = "",
    grid_type: str = "",
):
    """Takes the results of the top ten and preorders queries and processes as well as adds them to the embed(s)

    Parameters
    ----------
    results : Array of Dicts
        The results of the preceding functions
    title : str
        The title of the embed
    store_list : Array of strings
        The list of stores the results are from

    Returns
    -------
    discord.embeds
        The embeds that will be sent to the discord server.
    len_of_results
        An int of the amount of stores, used to determine if a thread will be created
    """
    embeds = []
    message = ""
    is_multi = False
    len_of_results = len(results)
    list_of_keys = list(results.keys())
    first_key = list_of_keys[0]
    if len_of_results != 1:
        is_multi = True
    i = 0

    for key in store_list:
        country = key.lower()
        if not imageonly:
            prepared_message = ""
            if len_of_results != 1:
                prepared_message += "".join([":flag_", country, ": ", "\n"])
            for result in results[key.lower()]:
                if re.search("\b\d{6,9}\b", result["id"]):
                    link = f"https://store.playstation.com/{store_dict[result['region'].upper()]['sub']}/concept/{result['id']}"
                else:
                    link = f"https://store.playstation.com/{store_dict[result['region'].upper()]['sub']}/product/{result['id']}"
                prepared_message += "".join(
                    [
                        "**[",
                        str(result["rank"]).zfill(2),
                        f"]({link}):** ",
                        result["name"],
                        "\n",
                    ]
                )
        i += 1
        if len_of_results == 1 or imageonly:
            cover_array = [
                "".join([game["cover"], "?thumb=true"]) for game in results[key.lower()]
            ]
            image_string = ";".join(cover_array)
            imgur_url = await setup_procure_images(
                image_string,
                grid_type=grid_type,
            )

            if not imgur_url:
                logger.info("No image received")
            embeds.append(
                generate_embeds(
                    title,
                    prepared_message,
                    is_multi=False,
                    imgur_url=imgur_url,
                    country=country,
                    url_type=url_type,
                )
            )
        elif not imageonly:
            if (
                len(message) + len(prepared_message) > 4080
                or key == store_list[len_of_results - 1]
            ):
                embeds.append(generate_embeds(title, message, is_multi))
                message = prepared_message
                i = 0
            else:
                message += prepared_message

    return embeds, len_of_results


class HandlerView(discord.ui.View):
    current_page: int = 1
    page_count: int = 0
    game: dict = {}
    store: str = ""

    def __init__(
        self,
        payload,
        store,
        original_user: discord.user,
        type: str,
        trending_images: list = [],
    ):
        super().__init__(timeout=180)
        self.original_user = original_user
        self.type = type
        if type == "screens":
            self.game = payload
            self.screenshots = self.game["screens"]
            self.page_count = (
                int(len(self.game["screens"]) / 4)
                if (len(self.game["screens"]) / 4).is_integer()
                else int(len(self.game["screens"]) / 4) + 1
            )
            self.store = store
        elif type == "trending":
            self.payload = payload
            self.store = store
            self.images = trending_images
            self.page_count = len(self.payload)

    async def on_timeout(self):
        self.disable_all_items()

    async def send(self, interaction: discord.Interaction, silent):
        # if silent:
        #    self.message = await self.original_user.send(view=self)
        # else:
        self.message = await interaction.followup.send(view=self, ephemeral=silent)
        await self.update_message()

    async def update_message(self):
        self.update_buttons()
        if self.type == "screens":
            await self.message.edit(embeds=self.create_embeds(), view=self)
        elif self.type == "trending":
            await self.message.edit(embeds=self.create_embeds(), view=self)

    def disable_all_items(self):
        self.remove_item(self.first_page_button)
        self.remove_item(self.last_page_button)
        self.remove_item(self.next_button)
        self.remove_item(self.prev_button)

    def create_embeds(self):
        cur_page = self.current_page
        embeds = []
        if self.type == "screens":
            current_point = cur_page * 4 - 4
            title = f"{self.game['name']} :flag_{self.store.lower()}:"
            for i in range(4):
                if current_point == len(self.screenshots):
                    break
                embed = discord.Embed(title=title, url=self.game["url"], color=0x8A9A5B)
                embed.set_image(url=self.screenshots[current_point])
                embed.set_footer(
                    text=f"{self.game['name']} Screenshots {self.current_page} / {self.page_count}",
                    icon_url=self.game["cover"],
                )
                embeds.append(embed)
                current_point += 1
        elif self.type == "trending":
            key = self.store[cur_page - 1]
            message = ""
            country = key.lower()
            for result in self.payload[key.lower()]:
                message += "".join(
                    [
                        "**",
                        str(result["rank"]).zfill(2),
                        ":** ",
                        result["name"],
                        "\n",
                    ]
                )
            embeds.append(
                generate_embeds(
                    title="Trending",
                    message=message,
                    is_multi=False,
                    imgur_url=self.images[key.lower()],
                    country=country,
                    url_type="topten",
                )
            )
        return embeds

    def update_buttons(self):
        if self.current_page == 1:
            self.first_page_button.disabled = True
            self.prev_button.disabled = True
            self.first_page_button.style = discord.ButtonStyle.gray
            self.prev_button.style = discord.ButtonStyle.gray
        else:
            self.first_page_button.disabled = False
            self.prev_button.disabled = False
            self.first_page_button.style = discord.ButtonStyle.green
            self.prev_button.style = discord.ButtonStyle.primary

        if self.current_page == self.page_count:
            self.next_button.disabled = True
            self.last_page_button.disabled = True
            self.last_page_button.style = discord.ButtonStyle.gray
            self.next_button.style = discord.ButtonStyle.gray
        else:
            self.next_button.disabled = False
            self.last_page_button.disabled = False
            self.last_page_button.style = discord.ButtonStyle.green
            self.next_button.style = discord.ButtonStyle.primary

    @discord.ui.button(label="|<", style=discord.ButtonStyle.green)
    async def first_page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if interaction.user == self.original_user:
            await interaction.response.defer()
            self.current_page = 1
            await self.update_message()

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user == self.original_user:
            await interaction.response.defer()
            self.current_page -= 1
            await self.update_message()

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user == self.original_user:
            await interaction.response.defer()
            self.current_page += 1
            await self.update_message()

    @discord.ui.button(label=">|", style=discord.ButtonStyle.green)
    async def last_page_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user == self.original_user:
            await interaction.response.defer()
            self.current_page = self.page_count
            await self.update_message()

    def on_error(
        self, interaction: discord.Interaction[discord.Client], error: Exception, item
    ):
        logger.error(error)
        # return super().on_error(interaction, error, item)


async def prepare_embed_for_top_selling(
    results: dict,
    store_list: list,
    top120: bool,
    found: dict,
    exclude_f2p: bool = False,
):
    if top120:
        top = "Top 120"
    else:
        top = "Top 10"
    if exclude_f2p:
        description = "These are the positions with F2P Games removed\n"
    else:
        description = ""

    for result in results:
        if len(results[result][0]) == 12:
            col = 0x228B22
        else:
            col = 0xEC3440
        break

    embed = discord.Embed(color=col, timestamp=datetime.now(), description=description)

    embed = await spread_results_in_fields(
        embed,
        results,
        store_list,
    )

    embed.set_author(
        name=found["name"],
        url=f"https://store.playstation.com/en-us/concept/{found['concept']}",
    )
    embed.set_thumbnail(url=f'{found["cover"]}?w=50')
    embed.set_footer(
        text=f"Positions in {top}",
        icon_url=storeicon,
    )
    return embed


async def get_topselling_results(
    top120: bool, store_list: list, found: dict, exclude_f2p: bool
):
    if top120:
        link_type = link_types["120"]
    else:
        link_type = link_types["topten"]
    function = is_game_in_bestselling
    results = await async_process_data(
        store_dict,
        function,
        store_list,
        found,
        link_type,
        top120=top120,
        exclude_f2p=exclude_f2p,
    )
    return results


"""async def store_bestseller_in_db(region_list: str, games_dict: dict):
    config = load_config()
    ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = {}
    for region in region_list:
        res = await get_data_for_bestsellers_import(
            sem=sem, region=region, link_type="/pages/browse/"
        )get_data_for_preorders_import
        results.update(res)
    await prepare_concepts(store_dict=store_dict, import_list=results)
    await insert_bestsellers(config=config, games_list=games_dict, timestamp=ts)"""


class PSCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.no_data_key_error_message = "The data couldnt be collected. \nThis could happen for following reasons:\n1. There was a slight hiccup in which case it will work after a retry\n2. PSN is down. Wait for it to come up again."
        self.no_data_type_error_message = "The data couldnt be collected.\nPossible Issues:\n1. There was an error in fetching the information. It will work in in a retry.\n2. Faulty Code. Contact Lacrimosis."
        self.generic_message = ":exclamation: Ran into an error"
        self.amazon_regions = ["in", "fr", "com", "de", "es", "us", "jp", "gb"]
        self.set_dict = {
            "plato": "Plato Selection",
            "ameo": "Africa, Middle East, Oceania",
            "ww": "World Wide",
            "eu": "Europe",
            "asia": "Asia",
            "am": "America",
        }
        self.aliases = ["plato", "ww", "asia", "eu", "am", "ameo"]

    async def base_log(self, ctx: discord.Interaction):
        logger.info(f"Command: {ctx.command.name}")
        if "private" in str(ctx.channel.type):
            logger.info(f"Location Type: {ctx.channel.type}")
        else:
            logger.info(f"Guild: {ctx.guild.name}")
            logger.info(f"Location: {ctx.channel.name}")
            logger.info(f"Location Type: {ctx.channel.type}")
        if "options" in ctx.data:
            logger.info(f"Options:")
            for option in ctx.data["options"]:
                message = f'{option["name"]}:{option["value"]}'
                logger.info(message)

    async def error_handler(self, ctx: discord.Interaction, error: Exception):
        logger.error(ctx.data["name"])
        if "options" in ctx.data:
            for option in ctx.data["options"]:
                message = f'{option["name"]}:{option["value"]}'
                logger.error(message)
        logger.error(error)
        logger.error(traceback.format_exc())
        if "KeyError" in str(error.args):
            error_message = self.no_data_key_error_message
        elif "TypeError" in str(error.args):
            error_message = self.no_data_type_error_message
        elif "AmazonRetryThrottle" in str(error.args):
            error_message = "Retry has failed. Please try again in a few minutes."
        elif "PSNBlock" in str(error.args):
            error_message = "Bot has beeen blocked from PSN. Retry in 10 minutes."
        else:
            error_message = self.generic_message
        return error_message

    async def message_handler(
        self, ctx: discord.Interaction, message_type: str, content: str = ""
    ):
        # ToDo Conert to Dict
        if message_type == "init":
            await ctx.response.send_message(
                "<a:loading:1227296138990714890> Collecting Data. This may take a while.",
                ephemeral=True,
            )
        elif message_type == "edit_no_data":
            await ctx.edit_original_response(
                content="The data couldnt be collected. \n Either it was a slight hiccup and will work again on a retry or PSN is down."
            )
        elif message_type == "edit_game_released":
            await ctx.edit_original_response(
                content="Game has been already released. <:waiting1:963149578083893258>"
            )
        elif message_type == "edit_game_no_preorder":
            await ctx.edit_original_response(
                content="Game has no preorder yet. <:waiting1:963149578083893258>"
            )
        elif message_type == "processing":
            if content == "":
                content = "Data collected. Processing"
            await ctx.edit_original_response(
                content=f"<a:processing:1227360323217002588> {content}"
            )
        elif message_type == "preparing":
            if content == "":
                content = "Data processed. Preparing"
            await ctx.edit_original_response(
                content=f"<a:tick:1227295639122083920> {content}"
            )
        elif message_type == "game_not_in_store":
            await ctx.delete_original_response()
            await ctx.followup.send(
                "Game doesnt exist in requested store <:waiting1:963149578083893258>",
                ephemeral=True,
            )
        elif message_type == "send_invalid_store":
            await ctx.response.send_message("False Input: Store(s)", ephemeral=True)
        elif message_type == "send":
            await ctx.delete_original_response()
            await ctx.followup.send(content=content, ephemeral=True)
        else:
            await ctx.edit_original_response(content=message_type)

    async def get_amazon_link(self, region: str):
        if region not in self.amazon_regions:
            return "", False
        else:
            link = f"https://www.amazon.{region}/gp/bestsellers/videogames/ref=zg_bs_nav_videogames_0"
            return link, True

    async def gameinfo_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """The subroutine for game auto completion

        Parameters
        ----------
        interaction : discord.Interaction
            _description_
        current : str
            Currentletters that have been typed

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            A list of names representing product Ids
        """
        # Regex collection of unicode ranges. The ranges are for japanese characters
        reg = "n/[\u3000-\u303f]|[\u3040-\u309f]|[\u30a0-\u30ff]|[\uff00-\uffef]|[\u4e00-\u9faf]|[\u2605-\u2606]|[\u2190-\u2195]|\u203b/g"
        data = []
        store = None
        prefix_search = False
        try:
            # current is the input users type into the parameter
            # If the regex matches it means the input is made out of japanese characters
            if re.search(reg, current):
                # The store which the autocomplete searches in is set to the japanese one.
                store = store_dict["JP"]["sub"]
                prefix_search = True
                prefix = "JP"
            # If there is a comma in the current input.
            # This serves as way to set a different store to search in
            if "," in current:
                split_current = current.split(",")
                # The store gets stored
                search_store = split_current[0]
                # The latter half of the split is the actual search string
                current = split_current[1]
                # The store is sent to validation
                valid, store_list = validate_stores(
                    search_store, store_dict, single=True
                )
                if valid:
                    # the store if valid is set to the string in front of the comma
                    store = store_dict[store_list[0]]["sub"]
                    prefix = store_list[0]
                    # prefix_search is needed so that the gameinfo function knows it needs to switch stores
                    prefix_search = True
            # the searchin parameter functions an alternative to the comma seperated input
            # in interaction.namespace are all parameters and their current values stored.
            # a parameter only exists in it if it has any value
            # if "searchin" in interaction.namespace:
            #    search_store = interaction.namespace["searchin"]
            # if the store it searchin has been selected with autocomplete the value in the parameter will be
            # Country (country tld) In order for the TLD to be used it has to be extracted.
            # Starting from the third last character to the last will be saved as new search store
            #    if search_store.endswith(")"):
            #        search_store = search_store[-3:]
            #    store = interaction.namespace["searchin"].upper()
            #    logger.info(store)
            #    if store in store_dict:
            #       store = store_dict[store]["sub"]
            # It is possible to directly use a games id to get data
            # the validation checks if its a game id
            if current != "":
                is_game_id, _ = validate_game(current)
                # if the current input is empty or an id there is no need to start the
                # request to collect search results to display as suggestions for the autocomplete
                if not is_game_id:
                    if not store:
                        store = store_dict["US"]["sub"]
                    searchterm = current
                    # Once the data has been validated the actual suggestiosn can be fetched.
                    # The store that will be searched in and the search string are given to get_games_collection
                    games = await get_games_collection(store, searchterm)
                    # del soup
                    logger.debug("Returning from get_games_collection")
                    if games:
                        for game_choice in iter(games):
                            game = games[game_choice]

                            # if the search was in a different store the information whcih store has been picked must be send
                            # to game info as well. Games are unique IDs peer country.
                            # Thus the clarification
                            if prefix_search:
                                game = f"{prefix},{game}"
                            # The display values (game_choice) and the underlying value (game)
                            # are safed in the list which gets sent to the suggestion list
                            data.append(
                                app_commands.Choice(name=game_choice, value=game)
                            )
                        return data
        except Exception as error:
            logger.error(traceback.format_exc())
            logger.debug(error)

    # @app_commands.autocomplete()

    async def store_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """This function returns the

        Parameters
        ----------
        interaction : discord.Interaction
            The current interaction
        current : str
            The current input in the connected parameter

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            List of suggestions
        """
        data = []
        valuegroup = []
        try:
            # This function supports the input of multiple stores in a chain. Example: fr,de,us
            # If there is a comma the input will be collected in two ways.
            if "," in current:
                comma = True
                # The whole input is saved in searchgroup. White space is removed.
                searchgroup = current.replace(" ", "")
                # The very last entered string is the searchterm
                split_search = current.split(",")
                searchterm = split_search[int(len(split_search) - 1)].lower().strip()

                display = []
                valuegroup = []
                searchgroup = searchgroup.split(",")
                searchgroup.pop(len(searchgroup) - 1)
                for c in searchgroup:
                    for country_key, country_dict in store_dict.items():
                        if c.upper() in country_key or (
                            country_dict["name"].lower().startswith(c.lower())
                            and len(c) > 3
                        ):
                            display.append(
                                f"{country_dict['name']} ({country_dict['key']})"
                            )
                            valuegroup.append(country_dict["key"])
            else:
                # No comma means the searchterm is simply the current input
                comma = False
                searchterm = current
            # This function supports the display of all stores that have been typed into the coma seprated string
            # That makes the function somewhat more complex than otherwise necessary.

            if searchterm != "":
                matching_keys = [
                    key
                    for key in store_dict.keys()
                    if store_dict[key]["name"].lower().startswith(searchterm.lower())
                    or store_dict[key]["key"].startswith(searchterm.upper())
                ]
                if not comma:
                    aliases = [
                        key
                        for key in self.aliases
                        if key.lower().startswith(searchterm.lower())
                    ]
                    matching_keys = aliases + matching_keys
            else:
                keys = [key for key in store_dict.keys()][:19]
                matching_keys = self.aliases + keys

            for x in matching_keys:
                if comma:
                    suggestion_display = copy.deepcopy(display)

                    suggestion_display.append(
                        f"{store_dict[x]['name']} ({store_dict[x]['key']})"
                    )
                    suggestion_value = copy.deepcopy(valuegroup)
                    suggestion_value.append(store_dict[x]["key"])
                    data.append(
                        app_commands.Choice(
                            name=", ".join(suggestion_display),
                            value=",".join(suggestion_value),
                        )
                    )
                else:
                    if x in store_sets:
                        data.append(
                            app_commands.Choice(
                                name=f"{self.set_dict[x]}",
                                value=x,
                            )
                        )
                    else:
                        data.append(
                            app_commands.Choice(
                                name=f"{store_dict[x]['name']} ({store_dict[x]['key']})",
                                value=store_dict[x]["key"],
                            )
                        )
                        if len(data) == 25:
                            break
        except Exception as error:
            logger.error(traceback.format_exc())
            logger.error(error)

        return data

    async def storeinfo_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """This function returns the

        Parameters
        ----------
        interaction : discord.Interaction
            The current interaction
        current : str
            The current input in the connected parameter

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            List of suggestions
        """
        data = []
        try:
            searchterm = current
            # This function supports the display of all stores that have been typed into the coma seprated string
            # That makes the function somewhat more complex than otherwise necessary.
            if searchterm != "":
                matching_keys = [
                    key
                    for key in store_dict.keys()
                    if store_dict[key]["name"].lower().startswith(searchterm.lower())
                    or store_dict[key]["key"].startswith(searchterm.upper())
                ]
            else:
                keys = [key for key in store_dict.keys()][:19]
                matching_keys = keys

            for x in matching_keys:
                data.append(
                    app_commands.Choice(
                        name=f"{store_dict[x]['name']} ({store_dict[x]['key']})",
                        value=store_dict[x]["key"],
                    )
                )
                if len(data) == 25:
                    break
        except Exception as error:
            logger.error(traceback.format_exc())
            logger.error(error)

        return data

    async def bool_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """This function returns the

        Parameters
        ----------
        interaction : discord.Interaction
            The current interaction
        current : str
            The current input in the connected parameter

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            List of suggestions
        """
        try:
            if current != "":
                current == ""
            data = []
            data.append(app_commands.Choice(name="Yes", value="True"))
            data.append(app_commands.Choice(name="No", value="False"))
        except Exception as error:
            logger.error(error)
            logger.error(traceback.format_exc())

        return data

    async def export_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """This function returns the

        Parameters
        ----------
        interaction : discord.Interaction
            The current interaction
        current : str
            The current input in the connected parameter

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            List of suggestions
        """
        data = []
        formats = ["csv", "json"]
        try:
            for format in formats:
                data.append(app_commands.Choice(name=format, value=format))
        except Exception as error:
            logger.error(error)

        return data

    @app_commands.command(name="topten")
    @app_commands.autocomplete(
        stores=store_autocompletion,
        export=export_autocompletion,
    )
    async def topten(
        self,
        interaction: discord.Interaction,
        stores: str,
        imageonly: bool = False,
        silent: bool = False,
        export: str = None,
    ):
        """The 10 Bestselling Games

        Parameters
        ----------
        stores : str
            The stores in which to look up the games
        imageonly: bool
            Returns lists only as images. Multiple Countries supported
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(interaction)
        store_list = []
        futures = []
        title = "Bestselling Games"
        valid, store_list = validate_stores(
            stores, store_dict, store_sets, custom_sets, id=str(interaction.user.id)
        )
        if not valid:
            await self.message_handler(
                ctx=interaction, message_type="send_invalid_store"
            )
        else:
            await self.message_handler(ctx=interaction, message_type="init")
            function = get_best_selling_games
            results = await async_process_data(
                store_dict, function, store_list, link_type=link_types["topten"]
            )
            await self.message_handler(ctx=interaction, message_type="processing")
            embeds, len_of_results = await process_top_lists(
                results,
                title,
                store_list,
                imageonly,
                url_type="topten",
                grid_type="topten",
            )

            if len_of_results > 4 or imageonly and len_of_results > 4:
                if str(interaction.channel.type) not in ["thread", "private"]:
                    thread = await interaction.channel.create_thread(
                        name="Top 10",
                        type=discord.ChannelType.public_thread,
                    )
                    for embed in embeds:
                        await thread.send(embed=embed)
                    await interaction.delete_original_response()
                    await interaction.followup.send(
                        content="<:katpeek:740197912524619796> Here you go"
                    )
                else:
                    await interaction.delete_original_response()
                    await interaction.followup.send(embeds=embeds, ephemeral=True)
            else:
                await interaction.delete_original_response()
                await interaction.followup.send(
                    embeds=embeds,
                    ephemeral=silent,
                )
            if export:
                file = export_data(
                    data=results, file_format=export, command=interaction.command.name
                )
                await interaction.followup.send(file=discord.file.File(file))
                delete_file(file)

    @topten.error
    async def topten_error(self, interaction: discord.Interaction, error: Exception):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(
        name="preorders", description="Shows Top 12 Preorder Of Given Stores"
    )
    @app_commands.autocomplete(
        stores=store_autocompletion, export=export_autocompletion
    )
    async def preorders(
        self,
        interaction: discord.Interaction,
        stores: str,
        imageonly: bool = False,
        silent: bool = False,
        export: str = None,
    ):
        """Twelve bestselling prorders"

        Parameters
        ----------
        stores : str
            The stores in which to look up the games
        imageonly: bool
            Returns lists only as images. Multiple Countries supported
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(interaction)

        store_list = []
        title = "Bestselling Preorders"
        embeds = []

        valid_stores, store_list = validate_stores(
            stores, store_dict, store_sets, custom_sets, id=str(interaction.user.id)
        )
        if not valid_stores:
            await self.message_handler(
                ctx=interaction, message_type="send_invalid_store"
            )
        else:
            await self.message_handler(ctx=interaction, message_type="init")
            function = get_bestselling_preorders
            results = await async_process_data(
                store_dict, function, store_list, link_type=link_types["topten"]
            )
            logger.debug("After async_process_data")
            await self.message_handler(ctx=interaction, message_type="processing")
            embeds, len_of_results = await process_top_lists(
                results,
                title,
                store_list,
                imageonly,
                url_type="preorders",
                grid_type="preorders",
            )

            if len_of_results > 5 or imageonly and len_of_results > 4:
                if str(interaction.channel.type) not in ["thread", "private"]:
                    thread = await interaction.channel.create_thread(
                        name="Top 10",
                        type=discord.ChannelType.public_thread,
                    )
                    for embed in embeds:
                        await thread.send(embed=embed)
                    await interaction.delete_original_response()
                    await interaction.followup.send(
                        content="<:katpeek:740197912524619796> Here you go"
                    )
                else:
                    await interaction.delete_original_response()
                    await interaction.followup.send(embeds=embeds, ephemeral=True)
            else:
                await interaction.delete_original_response()
                await interaction.followup.send(embeds=embeds, ephemeral=silent)

            if export:
                file = export_data(
                    data=results, file_format=export, command=interaction.command.name
                )
                await interaction.followup.send(file=discord.file.File(file))
                delete_file(file)
            waste = []
            waste.extend((results, embeds))
            await waste_disposal(waste)

    @preorders.error
    async def preorders_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="gameinfo")
    @app_commands.autocomplete(
        game=gameinfo_autocompletion,
        redirect=store_autocompletion,
        export=export_autocompletion,
    )
    async def gameinfo(
        self,
        interaction: discord.Interaction,
        game: str,
        redirect: str = None,
        silent: bool = False,
        export: str = None,
    ):
        """Information about a Game

        Parameters
        ----------
        game : str
            Your Game. Different Store Example: de,Uncharted
        redirect : str, optional
            Get the game in another Store
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(interaction)

        for option in interaction.data["options"]:
            message = f'topten Error - {option["name"]}:{option["value"]}'
            logger.debug(message)
        store, target_region = ("US", False) if redirect == None else ("US", redirect)
        if target_region:
            _, target_region = validate_stores(target_region, store_dict, single=True)
            print_region = target_region[0]
            target_region = store_dict[target_region[0]]["sub"]
        if "," in game:
            split = game.split(",")
            game = split[1]
            store = split[0]
        valid, store, is_concept = await validate_input(game, store, True)
        if not valid:
            await interaction.response.send_message(store, ephemeral=True)
        else:
            if game.startswith("JP"):
                store = "JP"
            else:
                store = store[0]
            if is_concept:
                link_type = link_types["concept"]
            else:
                link_type = link_types["product"]
            await interaction.response.send_message(
                "<a:loading:1227296138990714890> Collecting Data.", ephemeral=True
            )
            found = await gather_game_data(
                None,
                id=game,
                link_type=link_type,
                region=store_dict[store.upper()]["sub"],
                target_region=target_region,
                is_gameinfo=True,
            )

            if target_region:
                store = print_region
            if found == None:
                await self.message_handler(
                    ctx=interaction, message_type="game_not_in_store"
                )
            elif type(found) == str:
                await self.message_handler(
                    ctx=interaction,
                    message_type="send",
                    content="The game might exist but it doesnt support search by concept.",
                )
            else:
                await self.message_handler(ctx=interaction, message_type="processing")
                if found["product"] != "TBA":
                    d = datetime.fromisoformat(str(found["date"])[:-1]).astimezone(
                        timezone.utc
                    )
                    release_date = d.strftime("%Y-%m-%d")
                else:
                    release_date = found["date"]
                if list == type(found["platforms"]):
                    if len(found["platforms"]) == 1:
                        platforms = found["platforms"][0]
                    else:
                        platforms = ", ".join(found["platforms"])
                else:
                    platforms = found["platforms"]

                title = f"{found['name']} :flag_{store.lower()}:"
                try:

                    price = found["price"]
                    col = 0xE6E6FA
                    if found["discounted_price"] and re.sub(
                        r"[^\d,\.]", "", found["discounted_price"]
                    ):
                        non_string_dp = babel.numbers.parse_decimal(
                            re.sub(r"[^\d,\.]", "", found["discounted_price"]),
                            locale=store_dict[store.upper()]["sub"].replace("-", "_"),
                        )
                        non_string_p = babel.numbers.parse_decimal(
                            re.sub(r"[^\d,\.]", "", found["price"]),
                            locale=store_dict[store.upper()]["sub"].replace("-", "_"),
                        )
                        if non_string_dp < non_string_p:
                            price = (
                                f"**{found['discounted_price']}**\n~~{found['price']}~~"
                            )
                            col = 0xF8D364

                except Exception as e:
                    if type(e) == list:
                        for i in e:
                            print(i)
                    else:
                        print(e)
                    print("error")
                embed = discord.Embed(title=title, url=found["url"], color=col)
                embed.set_thumbnail(url=found["cover"])
                embed.add_field(
                    name="Score", value=found["starRating"]["rating"], inline=True
                )

                embed.add_field(name="Price", value=price, inline=True)
                embed.add_field(name="Publisher", value=found["pub"], inline=True)
                embed.add_field(
                    name="Ratings",
                    value=found["starRating"]["ratingCount"],
                    inline=True,
                )
                embed.add_field(name="Platforms", value=platforms, inline=True)
                embed.add_field(name="Release", value=release_date, inline=True)
                embed.add_field(
                    name="Rating Distribution",
                    value="".join(
                        [
                            ("★" * (5 - x))
                            + ("☆" * x)
                            + ": **"
                            + found["starRating"]["ratingDistribution"][x]
                            + "**\n"
                            for x in range(5)
                        ]
                    ),
                    inline=True,
                )
                if found["genres"]:
                    embed.add_field(
                        name="Genres",
                        value=found["genres"].replace(",", "\n"),
                        inline=True,
                    )
                if found["age_rating"]:
                    embed.add_field(
                        name=found["age_rating"],
                        value=(
                            found["age_content"].replace(",", "\n")
                            if found["age_content"]
                            else ""
                        ),
                        inline=True,
                    )
                embed.set_footer(
                    text="".join(
                        [
                            "Concept: ",
                            str(found["concept"]),
                            " Product: ",
                            found["product"],
                        ]
                    ),
                    icon_url=storeicon,
                )
                await interaction.delete_original_response()
                await interaction.followup.send(embed=embed, ephemeral=silent)
                waste = []
                waste.extend((embed, found, game))
                await waste_disposal(waste)

            if export:
                results = {}
                results[store] = found
                file = export_data(
                    data=results, file_format=export, command=interaction.command.name
                )
                await interaction.followup.send(file=discord.file.File(file))
                delete_file(file)

    @gameinfo.error
    async def gameinfo_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="screens")
    @app_commands.autocomplete(game=gameinfo_autocompletion)
    async def screens(
        self, interaction: discord.Interaction, game: str, silent: bool = False
    ):
        """Screenshots for your game.

        Parameters
        ----------
        game : str
            Your Game. Different Store Example: de,Uncharted
        silent : bool, optional
            Result will only visible for you
        """
        await self.base_log(interaction)
        user = interaction.user
        if "," in game:
            split = game.split(",")
            game = split[1]
            store = split[0]
        else:
            store = "US"
        valid, store, is_concept = await validate_input(game, store, True)
        if not valid:
            await interaction.response.send_message(store, ephemeral=True)
        else:
            await interaction.response.send_message(
                "Collecting Data. This may take a while.", ephemeral=True
            )
            if game.startswith("JP"):
                store = "JP"
            else:
                store = store[0]

            if is_concept:
                link_type = link_types["concept"]
            else:
                link_type = link_types["product"]
            found = await gather_game_data(
                None,
                id=game,
                link_type=link_type,
                region=store_dict[store.upper()]["sub"],
            )
            if found == None:
                await self.message_handler(ctx=interaction, message_type="edit_no_data")
            elif found["screens"] == None:
                await self.message_handler(
                    ctx=interaction,
                    content="No screenshots found.",
                    message_type="send",
                )
            else:
                view = HandlerView(found, store, type="screens", original_user=user)
                await view.send(interaction=interaction, silent=silent)

    @app_commands.command(name="searchtopten")
    @app_commands.autocomplete(
        game=gameinfo_autocompletion,
        stores=store_autocompletion,
        export=export_autocompletion,
        excludef2p=bool_autocompletion,
    )
    async def searchtopten(
        self,
        interaction: discord.Interaction,
        game: str,
        stores: str,
        silent: bool = False,
        export: str = None,
        excludef2p: str = "False",
    ):
        """Search a Game in The Top 10

        Parameters
        ----------
        game : str
            The Game
        stores : str
            See: /ls or /la
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        excludef2p : bool, optional
            F2P games are removed from the counts
        """
        await self.base_log(interaction)

        store_list = []
        results = []
        valid, _, is_concept = await validate_input(
            game, stores, id=str(interaction.user.id)
        )
        if not valid:
            await interaction.response.send_message(_, ephemeral=True)
        else:
            await self.message_handler(ctx=interaction, message_type="init")
            store_list = _
            if is_concept:
                link_type = link_types["concept"]
            else:
                link_type = link_types["product"]
            found = await gather_game_data(
                None,
                id=game,
                link_type=link_type,
                region=store_dict["US"]["sub"],
            )
            if found == None:
                await self.message_handler(ctx=interaction, message_type="edit_no_data")
            else:
                if excludef2p == "True":
                    excludef2p = True
                else:
                    excludef2p = False
                results = await get_topselling_results(
                    False, store_list=store_list, found=found, exclude_f2p=excludef2p
                )
                if None in results:
                    await self.message_handler(
                        ctx=interaction, message_type="edit_no_data"
                    )
                else:
                    await self.message_handler(
                        ctx=interaction, message_type="processing"
                    )
                    embed = await prepare_embed_for_top_selling(
                        results=results,
                        store_list=store_list,
                        top120=False,
                        found=found,
                        exclude_f2p=excludef2p,
                    )
                    await interaction.delete_original_response()
                    await interaction.followup.send(embed=embed, ephemeral=silent)

                    if export:
                        file = export_data(
                            data=results,
                            file_format=export,
                            command=interaction.command.name,
                        )
                        await interaction.followup.send(file=discord.file.File(file))
                        delete_file(file)
                    waste = []
                    waste.extend((results, embed, found, game))
                    await waste_disposal(waste)

    @searchtopten.error
    async def searchtopten_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="searchtop120")
    @app_commands.autocomplete(
        game=gameinfo_autocompletion,
        stores=store_autocompletion,
        export=export_autocompletion,
        excludef2p=bool_autocompletion,
    )
    async def searchtop120(
        self,
        interaction: discord.Interaction,
        game: str,
        stores: str,
        silent: bool = False,
        export: str = None,
        excludef2p: str = "False",
    ):
        """Search a Game in The Top 120

        Parameters
        ----------
        game : str
            The Game
        stores : str
            See: /ls or /la
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        excludef2p : bool, optional
            F2P games are removed from the counts
        """
        await self.base_log(interaction)

        store_list = []
        results = []

        valid, store_list, is_concept = await validate_input(
            game, stores, id=str(interaction.user.id)
        )
        if not valid:
            await interaction.response.send_message(store_list, ephemeral=True)
        else:
            await self.message_handler(ctx=interaction, message_type="init")
            if is_concept:
                link_type = link_types["concept"]
            else:
                link_type = link_types["product"]
            found = await gather_game_data(
                None,
                id=game,
                link_type=link_type,
                region=store_dict["US"]["sub"],
            )
            if found == None:
                await self.message_handler(ctx=interaction, message_type="edit_no_data")
            else:
                if excludef2p == "True":
                    excludef2p = True
                else:
                    excludef2p = False
                results = await get_topselling_results(
                    top120=True,
                    store_list=store_list,
                    found=found,
                    exclude_f2p=excludef2p,
                )
                if None in results:
                    await self.message_handler(
                        ctx=interaction, message_type="edit_no_data"
                    )
                else:
                    await self.message_handler(
                        ctx=interaction, message_type="processing"
                    )
                    embed = await prepare_embed_for_top_selling(
                        results=results,
                        store_list=store_list,
                        top120=True,
                        found=found,
                        exclude_f2p=excludef2p,
                    )
                    await interaction.delete_original_response()
                    await interaction.followup.send(embed=embed, ephemeral=silent)

        if export:
            file = export_data(
                data=results, file_format=export, command=interaction.command.name
            )
            await interaction.followup.send(file=discord.file.File(file))
            delete_file(file)
        waste = []
        waste.extend((results, embed, found, game))
        await waste_disposal(waste)

    @searchtop120.error
    async def searchtop120_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="searchpreorder")
    @app_commands.autocomplete(
        game=gameinfo_autocompletion,
        stores=store_autocompletion,
        export=export_autocompletion,
    )  # ,store=store
    async def searchpreorder(
        self,
        interaction: discord.Interaction,
        game: str,
        stores: str,
        silent: bool = False,
        export: str = None,
    ):
        """Search a Game in the Preorder Bestsellers

        Parameters
        ----------
        game : str
            The Game
        stores : str
            See: /ls or /la
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        excludef2p : bool, optional
            F2P games are removed from the counts
        """
        await self.base_log(ctx=interaction)
        # tracemalloc.start()
        store_list = []
        results = {}
        region = "en-us"
        if "," in game:
            split = game.split(",")
            game = split[1]
            region = store_dict[split[0].upper()]["sub"]
        valid, _, is_concept = await validate_input(
            game, stores, id=str(interaction.user.id)
        )
        if not valid:
            await interaction.response.send_message(_, ephemeral=True)
            return
        else:
            store_list = _
            await self.message_handler(ctx=interaction, message_type="init")
            if is_concept:
                link_type = link_types["concept"]
            else:
                link_type = link_types["product"]

            found = await gather_game_data(
                None, region=region, id=game, link_type=link_type
            )
            if found == None:
                await self.message_handler(ctx=interaction, message_type="edit_no_data")
            elif found["product"] == "TBA":
                await self.message_handler(
                    ctx=interaction, message_type="edit_game_no_preorder"
                )
            else:
                d = datetime.fromisoformat(str(found["date"])[:-1]).astimezone(
                    timezone.utc
                )
                ts = datetime.now(timezone.utc)

                if d < ts:
                    await self.message_handler(
                        ctx=interaction, message_type="edit_game_released"
                    )

                else:
                    await self.message_handler(
                        ctx=interaction,
                        message_type="processing",
                        content="Initial Data collected. Comparing with selected stores. Processing",
                    )
                    function = process_products
                    results = await async_process_data(
                        store_dict,
                        function,
                        store_list,
                        game=found,
                        link_type=link_types["concept"],
                        limit_rate=4,
                    )
                    embed = discord.Embed(
                        color=0x228B22,
                        timestamp=datetime.now(),
                    )
                    await self.message_handler(
                        ctx=interaction, message_type="preparing"
                    )
                    embed = await spread_results_in_fields(
                        embed, results, store_list, category_type="preorder"
                    )

                    embed.set_author(
                        name=found["name"],
                        url=f"https://store.playstation.com/en-us/concept/{found['concept']}",
                    )
                    embed.set_thumbnail(url=f"{found['cover']}?w=50")
                    embed.set_footer(
                        text="Preorder Positions",
                        icon_url=storeicon,
                    )
                    await interaction.delete_original_response()
                    await interaction.followup.send(embed=embed, ephemeral=silent)
                    # snapshot = tracemalloc.take_snapshot()
                    # await display_top(snapshot)
        if export:
            file = export_data(
                data=results, file_format=export, command=interaction.command.name
            )
            await interaction.followup.send(file=discord.file.File(file))
            delete_file(file)

    @searchpreorder.error
    async def searchpreorder_error(
        self, interaction: discord.Interaction, error: Exception
    ):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="ls")
    async def liststores(self, interaction: discord.Interaction):
        """Lists All Available Stores"""
        await self.base_log(ctx=interaction)
        message = ""
        temp_message = ""
        i = 0
        for x in store_dict:
            i = i + 1
            temp_message += (
                ":flag_"
                + store_dict[x]["key"].lower()
                + ": ("
                + store_dict[x]["key"]
                + ") "
            )
            if i % 4 == 0:
                message += temp_message + "\n"
                temp_message = ""
        embed = discord.Embed(
            title="Available Stores",
            color=0x0063C9,
            url="https://www.playstation.com/country-selector/index.html",
            description=message,
        )
        embed.set_thumbnail(url=storeicon)
        embed.set_footer(
            text="Available Stores",
            icon_url=storeicon,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @liststores.error
    async def liststores_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(
        name="la",
    )
    async def listalias(self, interaction: discord.Interaction):
        """Lists all Available Aliases

        If you have customized aliases they will show as well
        """
        await self.base_log(interaction)
        message = ""
        embed = discord.Embed(
            title="Available Aliases",
            color=0x0063C9,
        )
        for x in store_sets:
            message = ""
            for country in store_sets[x]:
                message += ":flag_" + str(country.lower()) + ":"
            embed.add_field(name=x, value=message, inline=True)
        user_id = str(interaction.user.id)
        if user_id in custom_sets:
            for x in custom_sets[user_id]:
                message = ""
                for country in custom_sets[user_id][x]:
                    message += ":flag_" + str(country.lower()) + ":"
                embed.add_field(name=x, value=message, inline=True)

        embed.set_thumbnail(url=storeicon)
        embed.set_footer(
            text="Available Aliases",
            icon_url=storeicon,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="storeinfo")
    @app_commands.autocomplete(store=storeinfo_autocompletion)  # ,store=store
    async def storeinfo(self, interaction: discord.Interaction, store: str):
        """Basic Store Information

        Parameters
        ----------
        store : str
            Store of your choice. See: /ls
        """
        store = store.upper()
        valid, store = validate_stores(store, store_dict, single=True)
        if not valid:
            await interaction.response.send_message(
                content="Invalid Input. Only supports single country", ephemeral=True
            )

        else:
            store = store[0]
            embed = discord.Embed(
                title=":flag_" + store.lower() + ":",
                color=0x0063C9,
                url="".join(
                    [
                        "https://store.playstation.com/",
                        store_dict[store]["sub"],
                        link_types["topten"],
                    ]
                ),
                timestamp=datetime.now(),
                description="Click on the flag to visit the store!\n",
            )
            embed.add_field(name="Name", value=store_dict[store]["name"], inline=True)
            embed.add_field(name="Key", value=store_dict[store]["key"], inline=True)
            embed.add_field(
                name="Component", value=store_dict[store]["sub"], inline=True
            )
            embed.set_footer(
                text="Store Information",
                icon_url=storeicon,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="addalias")
    @app_commands.autocomplete(stores=store_autocompletion)  # ,store=store
    async def addalias(self, interaction: discord.Interaction, alias: str, stores: str):
        """Adds an Customized Alias. Maximum is 5.

        Parameters
        ----------
        alias : str
            Name. Maximum of 4 characters.
        stores : str
            The Stores. Maximum of 10 characters.
        """
        await self.base_log(interaction)
        valid_stores, store_list, return_message = await validate_custom_alias_data(
            alias, stores, store_dict, store_sets
        )
        if not valid_stores:
            await interaction.response.send_message(
                content=return_message, ephemeral=True
            )
        elif len(store_list) > 10:
            await interaction.response.send_message(
                content=return_message, ephemeral=True
            )
        else:
            new_alias = {alias: store_list}
            logger.debug(new_alias)
            is_success, r_message = save_to_aliases_json(
                str(interaction.user.id), new_alias
            )
            if is_success:
                custom_sets.update(load_custom_sets())

                logger.debug(custom_sets[str(interaction.user.id)])
            await interaction.response.send_message(content=r_message, ephemeral=True)

    @addalias.error
    async def addalias_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    async def help_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """This function returns the

        Parameters
        ----------
        interaction : discord.Interaction
            The current interaction
        current : str
            The current input in the connected parameter

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            List of suggestions
        """
        try:
            data = []
            for command in self.__cog_app_commands__:
                if command.name != "help":
                    if command.name.startswith(current.lower()) or current == "":
                        data.append(
                            app_commands.Choice(name=command.name, value=command.name)
                        )
        except Exception as error:
            logger.error(error)
            logger.error(traceback.format_exc())

        return data

    @app_commands.command(name="help")
    @app_commands.autocomplete(command=help_autocompletion)
    async def help(self, interaction: discord.Interaction, command: str = ""):
        """Help"""
        await self.base_log(interaction)

        message = ""
        commands_json = load_json_file(name="commands")
        if command == "":
            for command_ in self.__cog_app_commands__:
                if command_.name != "help":
                    message += f"***/{command_.name}*** {commands_json['commands'][command_.name]['description']}\n"
            message += "\n\nUse /help [command: <command>] to get help for a specific command.\n\nParameter [silent] makes the bot response Ephemeral, only the requestor can see it.\n\nParameter [export] returns a CSV or JSON file with the data of the command."
            await interaction.response.send_message(content=message, ephemeral=True)
        else:
            commands_json = load_json_file(name="commands")

            embed = discord.Embed(
                color=0x366B2C,
                timestamp=datetime.now(),
                description=commands_json["commands"][command]["text"],
            )
            embed.set_author(name=command)
            embed.set_footer(
                text=command,
                icon_url=storeicon,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @addalias.error
    async def addalias_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="rating")
    @app_commands.autocomplete(
        game=gameinfo_autocompletion,
        second_game=gameinfo_autocompletion,
        third_game=gameinfo_autocompletion,
        fourth_game=gameinfo_autocompletion,
        fifth_game=gameinfo_autocompletion,
        sixth_game=gameinfo_autocompletion,
        export=export_autocompletion,
    )
    async def rating(
        self,
        interaction: discord.Interaction,
        game: str,
        second_game: str = None,
        third_game: str = None,
        fourth_game: str = None,
        fifth_game: str = None,
        sixth_game: str = None,
        silent: bool = False,
        export: str = None,
    ):
        """Ratings for Games

        Parameters
        ----------
        game : str
            First game or list of games (list in format: <ID>,<ID>,<ID>)
        second_game : str, optional
            Second game, optional, by default None
        third_game : str, optional
            Third game, optional, by default None
        fourth_game : str, optional
            Fourth game, optional, by default None
        fifth_game : str, optional
            Fifth game, optional, by default None
        sixth_game : str, optional
            Sixth game, optional, by default None
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(ctx=interaction)
        games = []
        found_collection = []
        init_sent = False
        if "," in game:
            games = game.split(",")
        else:
            for game in interaction.data["options"]:
                if game["name"] != "silent":
                    games.append(game["value"])
        await interaction.response.send_message(
            content="Validating Data.", ephemeral=True
        )
        for game in games:
            valid, store, is_concept = await validate_input(game, "US", True)
            store = store[0]
            if not valid:
                await interaction.edit_original_response(store)
            else:
                if not init_sent:
                    await interaction.edit_original_response(content="Validating Data.")
                    init_sent = True
                if is_concept:
                    link_type = link_types["concept"]
                else:
                    link_type = link_types["product"]

                found = await gather_game_data(
                    None,
                    id=game,
                    link_type=link_type,
                    region=store_dict[store.upper()]["sub"],
                    target_region=False,
                )
                found_collection.append(found)
        embed = discord.Embed(title="Ratings", color=0x0063C9)
        if len(found_collection) == 1:
            embed.set_thumbnail(url=f"{found_collection[0]['cover']}?w=50'")
        for found in found_collection:
            embed.add_field(
                name=f"{found['name']}",
                value=found["starRating"]["ratingCount"],
                inline=True,
            )
            embed.add_field(
                name="\u200b", value=found["starRating"]["rating"], inline=True
            )
            rating_string = str(found["starRating"]["rating"])
            if "." in rating_string:
                int_rating = int(rating_string.split(".")[0])
                decimal_value_rating = int(rating_string.split(".")[1])
                decimal_value_rating = (
                    decimal_value_rating * 10
                    if decimal_value_rating <= 9
                    else decimal_value_rating
                )
            else:
                int_rating = int(rating_string)
            stars = ""
            stars = ":full_moon:" * int_rating
            if int_rating != 5:
                if decimal_value_rating < 20:
                    stars += ":new_moon:" * (5 - int_rating)
                elif decimal_value_rating < 80 and decimal_value_rating >= 20:
                    stars += ":last_quarter_moon:" + ":new_moon:" * (5 - int_rating - 1)
                elif decimal_value_rating >= 80:
                    stars += ":full_moon:" + ":new_moon:" * (5 - (int_rating + 1))
            stars += f" [:shopping_cart:]({link_types['base']}/{store_dict[store]['sub']}{link_types['concept']}{found['concept']})"
            embed.add_field(
                name="\u200b",
                value=stars,
                inline=True,
            )
        await interaction.delete_original_response()
        await interaction.followup.send(embed=embed, ephemeral=silent)

        if export:
            results = {}
            results[store] = found_collection
            file = export_data(
                data=results, file_format=export, command=interaction.command.name
            )
            await interaction.followup.send(file=discord.file.File(file))
            delete_file(file)

    @rating.error
    async def rating_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="igea")
    @app_commands.autocomplete(export=export_autocompletion)
    async def igea(
        self, interaction: discord.Interaction, silent: bool = False, export: str = None
    ):
        """Gets current IGEA Chart

        Parameters
        ----------
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(interaction)
        week = None
        await self.message_handler(ctx=interaction, message_type="init")
        results, display_week = await find_current_chart_from_igea(
            link=link_types["igea"]
        )
        await self.message_handler(ctx=interaction, message_type="processing")
        chart_dict = results
        if week == None:
            footer = f"Top 10 ANZ Week {display_week}"
        else:
            pass
        imgur_url = None
        embeds = []
        for key in chart_dict:
            message = ""
            cover_array = [game["cover"] for game in chart_dict[key]]
            image_string = ";".join(cover_array)
            imgur_url = await setup_procure_images(
                image_string=image_string, grid_type="igea"
            )

            for entry in chart_dict[key]:
                message += f"**{entry['position'].zfill(2)}** __{entry['name']}__ [{entry['publisher']}]\n"
            embed = discord.Embed(
                title=f"Top 10 {key} Games",
                color=0x0063C9,
                timestamp=datetime.now(),
            )
            embed.add_field(name=store_dict[key]["name"], value=message, inline=False)
            if imgur_url:
                embed.set_image(url=imgur_url)
            embed.set_thumbnail(
                url="https://igea.net/wp-content/themes/IGEA2021/images/igea-logo.png"
            )
            embed.set_footer(
                text=footer,
                icon_url="https://igea.net/wp-content/uploads/2019/12/cropped-IGEA-LOGO-GREEN-SQUARE-32x32.png",
            )
            embeds.append(embed)

        await interaction.followup.send(embeds=embeds, ephemeral=silent)
        if export:
            file = export_data(
                data=results, file_format=export, command=interaction.command.name
            )
            await interaction.followup.send(file=discord.file.File(file))
            delete_file(file)

    @igea.error
    async def igea_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    @app_commands.command(name="sell")
    @app_commands.autocomplete(export=export_autocompletion)
    async def sell(
        self, interaction: discord.Interaction, silent: bool = False, export: str = None
    ):
        """Gets Current SELL Chart

        Parameters
        ----------
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(interaction)
        week = None

        await self.message_handler(ctx=interaction, message_type="init")
        results, display_week = await get_current_sell_chart(link=link_types["sell"])
        chart_dict = results
        display_week, _ = get_iso_week(
            int(datetime.now().strftime("%Y")), int(display_week)
        )
        await self.message_handler(ctx=interaction, message_type="processing")
        if week == None:
            footer = f"{display_week}"
        else:
            pass
        embed = discord.Embed(
            title="\u200b",
            color=0x0063C9,
            timestamp=datetime.now(),
        )

        for key in chart_dict:
            message = ""
            for entry in chart_dict[key]:
                message += f"**{entry['position'].zfill(2)}** __{entry['name']}__\n*{entry['platform']}*\n[{entry['publisher']}]\n"
            #
            embed.add_field(name="Games", value=message, inline=True)
        cover_array = [game["cover"] for game in chart_dict["fr"]]
        image_string = ";".join(cover_array)
        imgur_url = await setup_procure_images(
            image_string=image_string, grid_type="sell"
        )
        if imgur_url:
            embed.set_image(url=imgur_url)
        embed.set_author(
            icon_url="https://i.imgur.com/QsJIDQ1.png", name=f"TOP 5 France"
        )
        embed.set_footer(
            text=footer,
            icon_url="https://www.sell.fr/sites/default/files/favicon_4.png",
        )
        await interaction.delete_original_response()
        await interaction.followup.send(embed=embed, ephemeral=silent)

        if export:
            file = export_data(
                data=results, file_format=export, command=interaction.command.name
            )
            await interaction.followup.send(file=discord.file.File(file))
            delete_file(file)

    async def famitsu_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """The subroutine for rating board auto completion

        Parameters
        ----------
        interaction : discord.Interaction
            _description_
        current : str
            Currentletters that have been typed

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            A list of names representing product Ids
        """
        famitsu_weeks = {
            "fam_this": "Newest Week",
            "fam_last": "Last Week",
            "fam_before": "Week Before Last",
        }
        data = []
        famitsu_keys = []
        try:
            for key in link_types:
                if key.startswith("fam"):
                    famitsu_keys.append(key)
            for famitsu_key in famitsu_keys:

                data.append(
                    app_commands.Choice(
                        name=famitsu_weeks[famitsu_key], value=link_types[famitsu_key]
                    )
                )
            return data
        except Exception as error:
            logger.error(traceback.format_exc())
            logger.error(error)

    @app_commands.command(name="famitsu")
    @app_commands.autocomplete(
        week=famitsu_autocompletion, export=export_autocompletion
    )
    async def famitsu(
        self,
        interaction: discord.Interaction,
        week: str,
        silent: bool = False,
        export: str = None,
    ):
        """Gets Famitsu Charts

        Parameters
        ----------
        week: str, optional
            Which week you want the Chart for
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        excludef2p : bool, optional
            F2P games are removed from the counts
        """
        await self.base_log(interaction)
        week_ = None
        console_dict = {
            "PS4": "\U00002b1c",
            "PS5": "\U0001f7e6",
            "Switch": "\U0001f7e5",
            "Switch2": "\U0001f7e5",
        }
        await self.message_handler(ctx=interaction, message_type="init")
        results, display_week = await get_famitsu_sale_chart(link=week)
        await self.message_handler(ctx=interaction, message_type="processing")
        chart_dict = results
        if week_ == None:
            footer = f"{display_week}"
        else:
            pass

        for key in chart_dict:
            message = f'{console_dict["PS4"]} PS4\n{console_dict["PS5"]} PS5\n{console_dict["Switch"]} Switch\n{console_dict["Switch2"]} Switch2\n\n'
            for entry in chart_dict[key]:
                message += f"{console_dict[entry['platform']]} **{entry['position'].zfill(2)}** - {entry['weeklysales']}/{entry['overallsales']}\n"

        embed = discord.Embed(
            title="\u200b",
            color=0x0063C9,
            timestamp=datetime.now(),
            description=message,
        )
        cover_array = [game["cover"] for game in chart_dict["jp"]]
        image_string = ";".join(cover_array)
        imgur_url = await setup_procure_images(
            image_string=image_string, grid_type="famitsu"
        )
        if imgur_url:
            embed.set_image(url=imgur_url)
        embed.set_author(
            icon_url="https://www.famitsu.com/img/1812/favicons/apple-touch-icon.png",
            name=f"Famitsu Charts",
        )
        embed.set_footer(
            text=footer,
            icon_url="https://www.famitsu.com/img/1812/favicons/apple-touch-icon.png",
        )
        await interaction.delete_original_response()
        await interaction.followup.send(embed=embed, ephemeral=silent)

        if export:
            file = export_data(
                data=results, file_format=export, command=interaction.command.name
            )
            await interaction.followup.send(file=discord.file.File(file))
            delete_file(file)

    async def rating_boards_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """The subroutine for rating board auto completion

        Parameters
        ----------
        interaction : discord.Interaction
            _description_
        current : str
            Currentletters that have been typed

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            A list of names representing product Ids
        """
        data = []
        try:
            if current != "":
                soup = await get_soup(
                    False,
                    False,
                    link_type=f"{link_types['esrb_search']}{current}",
                    next_data=False,
                    cloudflare=True,
                )
                soup = soup.select_one("#results").select(".game")
                games = create_esrb_dict(soup)
                for game in games:
                    value = f"{game['link']}_{game['rating']}"
                    data.append(app_commands.Choice(name=game["title"], value=value))
                return data
        except Exception as error:
            logger.error(traceback.format_exc())
            logger.error(error)

    @app_commands.command(name="esrb")
    @app_commands.autocomplete(game=rating_boards_autocompletion)
    async def esrb(
        self, interaction: discord.Interaction, game: str, silent: bool = False
    ):
        """ESRB Entry of a Game

        Parameters
        ----------
        game : str
            The game you want the rating for
        silent : bool, optional
            Result will only visible for you
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(interaction)

        await self.message_handler(ctx=interaction, message_type="init")

        game = game.split("_")
        soup = await get_soup(False, False, game[0], False, True)
        found = get_esrb_data(soup)
        await self.message_handler(ctx=interaction, message_type="processing")
        embed = discord.Embed(
            title=f"{found['title']} ESRB Rating",
            color=0x0063C9,
            url=game[0],
            timestamp=datetime.now(),
        )

        embed.add_field(
            name=f"Publisher",
            value=found["pub"],
            inline=True,
        )
        embed.add_field(name="Platforms", value=found["platforms"], inline=True)
        embed.add_field(
            name="Content",
            value=found["content_descriptors"],
            inline=True,
        )
        embed.add_field(
            name="Rating",
            value=game[1],
            inline=True,
        )
        embed.add_field(
            name="Summary",
            value=found["summary"],
            inline=False,
        )
        embed.set_footer(
            text=found["title"],
            icon_url="https://i.imgur.com/DSSGyNs.png",
        )

        await interaction.followup.send(embed=embed, silent=silent)

    @esrb.error
    async def esrb_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    """
    @app_commands.command(name="snitch")
    async def snitch(
        self, interaction: discord.Interaction, user: str, silent: bool = False
    ):
        #PSN Account Information
        #
        #Parameters
        #----------
        #user : str
        #    User you want to snitch on

        await self.base_log(interaction)

        await interaction.response.send_message(
            "Collecting Data. This may take a while.", ephemeral=True
        )
        user_data, message = await get_user_data(user)
        if user_data:
            embed = discord.Embed(
                title=f"\u200b",
                color=0x0063C9,
                timestamp=datetime.now(),
            )
            if user_data["avatar"]:
                embed.set_thumbnail(url=user_data["avatar"])

            # embed.add_field(name="Name", value=user_data["name"], inline=True)
            if user_data["last_seen"]:
                if user_data["online_status"]:
                    last_seen = ":green_square: Online"
                else:
                    last_seen = ago(
                        datetime.strptime(
                            user_data["last_seen"], "%Y-%m-%dT%H:%M:%S.%fZ"
                        )
                    )
                embed.add_field(
                    name=f"Last Seen",
                    value=last_seen,
                    inline=True,
                )
            else:
                last_seen = "Unknown"
                embed.add_field(
                    name=f"Last Seen",
                    value=last_seen,
                    inline=True,
                )

            if user_data["last_played"]:
                embed.add_field(
                    name="Last Played", value=user_data["last_played"], inline=True
                )

            if user_data["trophy_level"]:
                embed.add_field(
                    name="Trophy Level",
                    value=user_data["trophy_level"],
                    inline=True,
                )
                embed.add_field(
                    name="Trophies",
                    value=user_data["trophies_sum"],
                    inline=True,
                )
                message = f'<:plat:1223407818850439298> {user_data["plat"]} <:gold:1223407695835435149> {user_data["gold"]} <:silver:1223407820628561930> {user_data["silver"]} <:bronze:1223407693629489365> {user_data["bronze"]}'
                embed.add_field(
                    name="Spread",
                    value=message,
                    inline=True,
                )
            if user_data["plus"]:
                embed.set_footer(
                    icon_url="https://i.imgur.com/loFmA1p.png", text="\u200b"
                )

            icon = "https://i.imgur.com/33BaItY.png"
            embed.set_author(icon_url=icon, name="Player Information")

            await interaction.delete_original_response()
            await interaction.followup.send(embed=embed, ephemeral=silent)
        else:
            await interaction.followup.send(content=message, ephemeral=True)

    @snitch.error
    async def snitch_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)
        """

    @app_commands.command(name="trending")
    @app_commands.autocomplete(
        stores=store_autocompletion, export=export_autocompletion
    )
    async def trending(
        self,
        interaction: discord.Interaction,
        stores: str,
        silent: bool = False,
        export: str = None,
    ):
        """Trending Games

        Parameters
        ----------
        stores : str
            The store or stores you want to see trending games from
        export : str, optional
            Export data in csv or json
        """
        await self.base_log(interaction)

        dm_user = interaction.user
        embeds = []
        valid, store_list = validate_stores(
            stores=stores,
            store_dict=store_dict,
            store_sets=store_sets,
            custom_sets=custom_sets,
            single=False,
        )
        if not valid:
            await interaction.response.send_message(store_list, ephemeral=True)
        elif len(store_list) > 5 and not file:
            await interaction.response.send_message(
                "More than 5 stores are not supported", ephemeral=True
            )
        else:
            await self.message_handler(ctx=interaction, message_type="init")
            function = get_trending_games
            results = await async_process_data(
                store_dict=store_dict,
                function=function,
                store_list=store_list,
                link_type=link_types["topten"],
                limit_rate=5,
            )
            if not results:
                pass
            else:
                await self.message_handler(ctx=interaction, message_type="processing")
                if len(results) > 1:
                    view = HandlerView(
                        payload=results,
                        store=store_list,
                        original_user=dm_user,
                        type="trending",
                        trending_images=imgur_urls,
                    )
                    imgur_urls = {}
                    for key in results:
                        cover_array = [
                            "".join([game["cover"], "?thumb=true"])
                            for game in results[key.lower()]
                        ]
                        image_string = ";".join(cover_array)
                        imgur_urls[key] = await setup_procure_images(
                            image_string=image_string, grid_type="trending"
                        )
                    await view.send(interaction=interaction, silent=silent)
                else:

                    embeds, _ = await process_top_lists(
                        results=results,
                        title="Trending",
                        store_list=store_list,
                        url_type="trending",
                        grid_type="trending",
                    )
                    await interaction.delete_original_response()
                    await interaction.followup.send(embeds=embeds)
                if export:
                    file = export_data(
                        data=results,
                        file_format=export,
                        command=interaction.command.name,
                    )
                    await interaction.followup.send(file=discord.file.File(file))
                    delete_file(file)
                waste = []
                waste.extend((results, embeds))
                await waste_disposal(waste)

    @trending.error
    async def trending_error(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)

    async def hltb_autocompletion(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        """This function returns the

        Parameters
        ----------
        interaction : discord.Interaction
            The current interaction
        current : str
            The current input in the connected parameter

        Returns
        -------
        typing.List[app_commands.Choice[str]]
            List of suggestions
        """
        data = []
        try:
            if current != "":
                results = await HowLongToBeat().async_search(current)
                for result in results:
                    data.append(
                        app_commands.Choice(name=result.game_name, value=result.game_id)
                    )
        except Exception as error:
            logger.error(traceback.format_exc())
            logger.error(error)

        return data

    @app_commands.command(name="howlongtobeat")
    @app_commands.autocomplete(game=hltb_autocompletion, export=export_autocompletion)
    async def howlongtobeat(
        self, interaction: discord.Interaction, game: int, export: str = None
    ):
        """Search HowLongToBeat

        Parameters
        ----------
        game : str
            The Game you want the length for
        """
        game_entry = HowLongToBeatEntry
        game_entry = await HowLongToBeat().async_search_from_id(game)
        embed = discord.Embed(
            title=f"How Long To Beat {game_entry.game_name}",
            url=game_entry.game_web_link,
            color=0x0063C9,
        )
        embed.set_thumbnail(url=game_entry.game_image_url)
        embed.add_field(name="Rating", value=f"{game_entry.review_score}%", inline=True)
        embed.add_field(
            name="Backlog", value=game_entry.json_content["count_backlog"], inline=True
        )
        embed.add_field(
            name="Playing", value=game_entry.json_content["count_playing"], inline=True
        )
        embed.add_field(
            name="Completed by",
            value=game_entry.json_content["count_comp"],
            inline=True,
        )
        embed.add_field(
            name="How Long To Beat",
            value=f"Main Story: **{round(game_entry.main_story)} Hours**\nMain + Extra: **{round(game_entry.main_extra)} Hours**\nCompletionist: **{round(game_entry.completionist)} Hours**",
            inline=True,
        )
        embed.set_footer(
            text=f"{game_entry.profile_dev} Released: {game_entry.release_world}",
        )
        await interaction.response.send_message(embed=embed)

    @howlongtobeat.error
    @famitsu.error
    async def base_error_handler(self, interaction: discord.Interaction, error):
        error_message = await self.error_handler(ctx=interaction, error=error)
        await interaction.followup.send(content=error_message, ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(PSCommands(bot))
    # await bot.add_cog(PSCommands(bot), guilds=[discord.Object(id=739723077109153833)])
    custom_sets.update(load_custom_sets())
    logger.info("Setup PS_Bot_Commands complete")
    print("Setup PS_Bot_Commands complete")


if __name__ == "__main__":
    exit()
