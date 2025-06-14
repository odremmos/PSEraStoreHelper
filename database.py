import asyncio
import datetime
import logging
import traceback
from configparser import ConfigParser
from datetime import timezone

import numpy
import psycopg2

from async_soup_and_data import gather_game_data, validate_game

logger = logging.getLogger("discord" + f".{__name__}")

###########################################################################################################################
###########################################################################################################################
########                                                                            #######################################
######## This File is an attempt at building an interface for a POSTGRESQL database #######################################
########                                                                            #######################################
###########################################################################################################################
###########################################################################################################################


def load_config(filename="database.ini", section="postgresql"):
    parser = ConfigParser()
    parser.read(filename)

    config = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            config[param[0]] = param[1]
    else:
        raise Exception(
            "Section {0} not found in the {1} file".format(section, filename)
        )

    return config


def connect(config: dict):
    """Connect to the PostgreSQL database server"""
    try:
        # connecting to the PostgreSQL server
        with psycopg2.connect(**config) as conn:
            logger.debug("Connected to the PostgreSQL server.")
            return conn
    except (psycopg2.DatabaseError, Exception) as error:
        logger.error(error)


def convert_timestamps(config):
    table = "ratings"
    sql = f"SELECT * FROM {table}"
    with psycopg2.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    if "Z" not in row[7]:
                        ts = f"{row[7].replace(' ','T')}Z"
                        logger.debug(ts)
                        conv_sql = (
                            f"UPDATE {table} SET timestamp = '{ts}' WHERE id = {row[0]}"
                        )
                        cur.execute(conv_sql)
                conn.commit()


def compare_timestamps(db_timestamp: str, import_timestamp: str):
    date_format = "%Y-%m-%dT%H:%M:%SZ"
    date1 = datetime.datetime.strptime(db_timestamp, date_format)
    date2 = datetime.datetime.strptime(import_timestamp, date_format)
    time_diff = abs(date2 - date1)
    logger.debug(time_diff.total_seconds() / 3600)
    if time_diff.total_seconds() / 3600 >= 18:
        return True
    else:
        return False


async def check_for_concepts(config: dict, concepts: str):
    concept_list = []
    sql = f"SELECT number FROM (VALUES {concepts}) AS numbers(number)WHERE number NOT IN (SELECT concept FROM concepts)"
    with psycopg2.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    concept_list.append(row[0])
    return concept_list


class insert:
    def __init__(self):
        self.concept_rating_inserts = 0
        self.concept_inserts = 0
        self.product_price_inserts = 0
        self.product_inserts = 0
        self.bestseller_inserts = 0
        self.bestseller_entry_inserts = 0
        self.preorder_inserts = 0
        self.preorder_entry_inserts = 0
        self.concepts_processed = []
        self.products_processed = []
        self.concepts_processed_by_store = {}
        self.products_processed_by_store = {}
        self.product_inserted_into_game_store = 0
        self.concept_inserted_into_game_store = 0
        self.insert_concept_error = 0
        self.insert_product_error = 0
        self.insert_bestseller_error = 0
        self.insert_preorders_error = 0
        self.return_code = 0

    async def print_log(self, return_row: tuple, item: str, insert_type: str):
        bitwise_value = return_row[0]
        logger.debug(f"Printing log for {item}")
        logger.debug(bitwise_value)
        # inserts new product
        if bitwise_value & 1024 == 1024:
            logger.debug(f"{item} does not exist. Inserting")
            if insert_type == "concept":
                self.concept_inserts += 1
                self.concept_inserted_into_game_store += 1
            else:
                self.product_inserts += 1
                self.product_inserted_into_game_store += 1
        # bit wise 1 = Update
        if bitwise_value & 1 == 1:
            logger.debug("Update")
        # 2 assigned price
        if bitwise_value & 2 == 2:
            logger.debug("Assigned price")
        # inserted and assigned price
        if bitwise_value & 4 == 4:
            logger.debug("Inserted and assigned price")
        # assigns name
        if bitwise_value & 8 == 8:
            logger.debug("Assigned name")
        # inserts and assigns name
        if bitwise_value & 16 == 16:
            logger.debug("Inserts and assign name")
        # assigns release_date
        if bitwise_value & 32 == 32:
            logger.debug("Assigned release date")
        # inserts and assign release date
        if bitwise_value & 64 == 64:
            logger.debug("Inserts and assign release date")
        # assigns genre
        if bitwise_value & 128 == 128:
            logger.debug("Assigned genre")
        # inserts and assignes genre
        if bitwise_value & 256 == 256:
            logger.debug("Inserts and assignes genre")
        # inserts existing product
        if bitwise_value & 512 == 512:
            logger.debug(f"Insert {item} into game_store")
            if insert_type == "concept":
                self.concept_inserted_into_game_store += 1
            else:
                self.product_inserted_into_game_store += 1

    async def insert_rating(
        self,
        cur: psycopg2.extensions.cursor,
        item_type: str,
        id: str,
        game: dict,
        timestamp: str,
        dry_run: bool = True,
        first: bool = True,
    ):
        insert_rating = False
        if item_type == "concepts":
            entry_type = "concept_id"
            logger.debug("Inserting Concept Rating")
        else:
            entry_type = "product_id"
            logger.debug("Inserting Product Rating")
        if not first:
            cur.execute(
                f"SELECT timestamp FROM ratings Where {entry_type} = {id} ORDER BY timestamp DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row:
                r_timestamp = row[0]
                if compare_timestamps(
                    db_timestamp=r_timestamp,
                    import_timestamp=timestamp,
                ):
                    insert_rating = True
        if first or insert_rating:
            logger.debug(f"Inserting Rating for {id}")
            self.concept_rating_inserts += 1
            cur.execute(
                "".join(
                    [
                        "INSERT INTO ratings(rating,one_stars,two_stars,three_stars,four_stars,five_stars,total,timestamp,",
                        entry_type,
                        ") VALUES( %s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    ]
                ),
                (
                    (game["starRating"]["rating"]),
                    game["starRating"]["ratingDistribution"][4],
                    game["starRating"]["ratingDistribution"][3],
                    game["starRating"]["ratingDistribution"][2],
                    game["starRating"]["ratingDistribution"][1],
                    game["starRating"]["ratingDistribution"][0],
                    (game["starRating"]["ratingCount"]),
                    timestamp,
                    id,
                ),
            )
            cur.execute(
                f"UPDATE {item_type} SET last_synced = '{timestamp}' Where id = {id}"
            )

    async def insert_missing_data(
        self,
        cur,
        entry_type: str,
        id: str,
        game: dict,
        dry_run: bool = True,
        first: bool = True,
    ):
        columns = []
        set = []
        if entry_type == "concept":
            entry_type = "concept_id"
            logger.info("Checking if concept data is missing")
            sql = f"SELECT invariant_name FROM concepts WHERE id = {id}"
            cur.execute(sql)
            row = cur.fetchone()
            if row:
                if not row[0] and game["invariant_name"]:
                    if "'" in game["invariant_name"]:
                        name = game["invariant_name"].replace("'", "''")
                    else:
                        name = game["invariant_name"]
                    value = "".join(["'", name, "'"])
                    assignment = "".join(["invariant_name", " = ", value])
                    set.append(assignment)
                if len(set) > 0:
                    logger.debug(f"Columns that were missing values: {len(set)}")
                    value = "".join(
                        [
                            "'",
                            datetime.datetime.now(timezone.utc).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            "'",
                        ]
                    )
                    assignment = "".join(["last_synced", " = ", value])
                    set.append(assignment)
                    statement = ", ".join(set)
                    sql = f"UPDATE concepts  SET {statement}  WHERE id = {id}"
                    logger.debug(sql)
                    if not dry_run:
                        cur.execute(sql)
        elif entry_type == "product":
            entry_type = "product_id"
            logger.debug("Checking if product data is missing")
            sql = f"SELECT genres,age_rating,age_content,edition_type,edition_ordering,name FROM products  WHERE id = {id}"
            cur.execute(sql)
            row = cur.fetchone()
            if row:

                if not row[0] and game["genres"]:
                    value = "".join(["'", game["genres"], "'"])
                    assignment = "".join(["genres", " = ", value])
                    set.append(assignment)
                if not row[1] and game["age_rating"]:
                    value = "".join(["'", game["age_rating"], "'"])
                    assignment = "".join(["age_rating", " = ", value])
                    set.append(assignment)
                if not row[2] and game["age_content"]:
                    value = "".join(["'", game["age_content"], "'"])
                    assignment = "".join(["age_content", " = ", value])
                    set.append(assignment)
                if not row[3] and game["edition_type"]:
                    value = "".join(["'", game["edition_type"], "'"])
                    assignment = "".join(["edition_type", " = ", value])
                    set.append(assignment)
                if not row[4] and game["edition_ordering"]:
                    value = str(game["edition_ordering"])
                    assignment = "".join(["edition_ordering", " = ", value])
                    set.append(assignment)
                if not row[5] and game["name"]:
                    if "'" in game["name"]:
                        name = game["name"].replace("'", "''")
                    else:
                        name = game["name"]
                    value = "".join(["'", name, "'"])
                    assignment = "".join(["name", " = ", value])
                    set.append(assignment)
                if len(set) > 0:
                    logger.debug(f"Columns that were missing values: {len(set)}")
                    value = "".join(
                        [
                            "'",
                            datetime.datetime.now(timezone.utc).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            "'",
                        ]
                    )
                    assignment = "".join(["last_synced", " = ", value])
                    set.append(assignment)
                    statement = ", ".join(set)
                    sql = f"UPDATE products SET {statement}  WHERE id = {id}"
                    price_sql = f"select pr.amount from products p join product_price pp on p.id = pp.product_id JOIN prices pr on pp.price_id = pr.id where region is null and p.id = {id};"
                    cur.execute(price_sql)
                    cur.fetchone()
                    if row:
                        if row[0] == game["price"]:
                            logger.info("price match")
                            if not dry_run:
                                cur.execute(sql)

    async def insert_concept_data(
        self,
        config: dict,
        game: dict,
        timestamp: str,
        dry_run: bool,
        force: bool = False,
        custom_list: bool = False,
    ):
        try:
            concept_id = None
            first = None
            with psycopg2.connect(**config) as conn:
                with conn.cursor() as cur:
                    if type(game["concept"]) == str:
                        game["concept"] = int(game["concept"])
                    cur.execute(
                        "INSERT INTO concepts_vw(concept,images,cover,import_region,import_date,age_content,age_rating,release_date,name,invariant_name,publisher) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (
                            game["concept"],
                            ",".join(game["screens"]) if game["screens"] else None,
                            game["cover"],
                            game["region"],
                            datetime.datetime.now(timezone.utc).strftime(
                                "%Y-%m-%dT%H:%M:%SZ"
                            ),
                            game["age_content"],
                            game["age_rating"],
                            game["date"],
                            game["name"],
                            game["invariant_name"],
                            game["pub"],
                        ),
                    )
                    cur.execute(
                        f"SELECT id FROM concepts Where concept = {game['concept']}"
                    )
                    row = cur.fetchone()
                    if row:
                        concept_id = row[0]
                        # first = True
                    cur.execute(
                        f"SELECT return_value,id FROM log_operation WHERE timestamp = '{game['date']}' AND item_id = '{game['concept']}'"
                    )
                    row = cur.fetchone()
                    if row:
                        await self.print_log(
                            row, game["concept"], insert_type="concept"
                        )
                        cur.execute(f"DELETE FROM log_operation where id = {row[1]}")
                    if concept_id:
                        no_day_match = False
                        # If the rating has a ? it comes with alien data and should not be inserted
                        if game["starRating"]["rating"] != "?":
                            if not first:
                                cur.execute(
                                    f"SELECT timestamp FROM ratings Where concept_id = {concept_id} ORDER BY timestamp DESC LIMIT 1"
                                )
                                row = cur.fetchone()
                                if row:
                                    r_timestamp = row[0]
                                    if (
                                        compare_timestamps(
                                            db_timestamp=r_timestamp,
                                            import_timestamp=timestamp,
                                        )
                                        or force
                                    ):
                                        logger.debug(
                                            f"{game['concept']} Rating does not exist from within 20 last hours"
                                        )
                                        no_day_match = True
                                    else:
                                        logger.debug(
                                            f"{game['concept']} Rating does exist from within 20 last hours"
                                        )
                            if first or no_day_match:
                                await self.insert_rating(
                                    cur=cur,
                                    item_type="concepts",
                                    id=concept_id,
                                    game=game,
                                    timestamp=timestamp,
                                    dry_run=dry_run,
                                )
                            else:
                                logger.debug(f"Rating not inserted")
                    if not dry_run:
                        conn.commit()
                    else:
                        conn.rollback()

                if not custom_list:
                    await self.insert_product_data(
                        config=config,
                        game=game,
                        timestamp=timestamp,
                        dry_run=dry_run,
                        force=force,
                    )

        except (Exception, psycopg2.DatabaseError) as error:
            conn.rollback()
            logger.error(error)
            logger.error(game["concept"])
            logger.error(game["product"])
            logger.error(traceback.format_exc())
            self.insert_concept_error += 1
            self.return_code = 1

    async def insert_product_data(
        self,
        config: dict,
        game: dict,
        timestamp: str,
        dry_run: bool,
        force: bool = False,
    ):
        conn = None
        logger.debug("Entering insert_product_data")
        product_id = None
        try:
            with psycopg2.connect(**config) as conn:
                with conn.cursor() as cur:
                    if game["product"] != "TBA":
                        if game["top_category"] == "ADD_ON":
                            dlc = True
                        else:
                            dlc = False
                        cur.execute(
                            "INSERT INTO products_vw(product, concept, category, region, edition_type, edition_ordering,  name, invariant_name, release_date, genres, price,cover) VALUES( %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (
                                game["product"],
                                game["concept"],
                                game["top_category"],
                                game["region"],
                                game["edition_type"],
                                game["edition_ordering"],
                                game["name"],
                                game["invariant_name"],
                                game["date"],
                                game["genres"],
                                game["price"],
                                game["cover"],
                            ),
                        )
                        cur.execute(
                            f"SELECT id FROM products Where product = '{game['product']}'"
                        )

                        row = cur.fetchone()
                        if row:
                            product_id = row[0]
                        cur.execute(
                            f"SELECT return_value,id FROM log_operation WHERE timestamp = '{game['date']}' AND item_id = '{game['product']}'"
                        )
                        row = cur.fetchone()
                        if row:
                            await self.print_log(
                                row, game["product"], insert_type="product"
                            )
                            cur.execute(
                                f"DELETE FROM log_operation where id = {row[1]}"
                            )
                            # 1 = PS4, 2 = PS5
                            platforms = {"PS4": 1, "PS5": 2}
                            for platform in game["platforms"]:
                                if not dry_run:
                                    cur.execute(
                                        "INSERT INTO product_platform(product_id,platform_id) VALUES (%s,%s)",
                                        (product_id, platforms[platform]),
                                    )

                        if dlc:
                            if product_id:
                                await self.insert_rating(
                                    cur=cur,
                                    item_type="products",
                                    id=product_id,
                                    game=game,
                                    timestamp=timestamp,
                                    dry_run=dry_run,
                                )
                        if not dry_run:
                            conn.commit()
                        else:
                            conn.rollback()

        except (Exception, psycopg2.DatabaseError) as error:
            if conn:
                conn.rollback()
            logger.error(error)
            logger.error(game)
            logger.error(traceback.format_exc())
            self.insert_product_error += 1
            self.return_code = 1

    async def insert_bestsellers(
        self,
        config: dict,
        games_list: list,
        timestamp: str,
        region: str,
        dry_run: bool,
    ):
        try:
            logger.debug("Entering insert_bestsellers")
            save_data = False
            hash_id = hash(timestamp)
            with psycopg2.connect(**config) as conn:
                with conn.cursor() as cur:
                    store = region
                    cur.execute(f"SELECT id FROM store Where key = '{store}'")
                    row = cur.fetchone()
                    store_id = row[0]

                    cur.execute(
                        f"SELECT timestamp FROM bestseller Where store_id = {store_id} ORDER BY timestamp DESC"
                    )
                    row = cur.fetchone()
                    if not row:
                        save_data = True
                        logger.debug(f"Bestseller list does not exist. Inserting")
                    else:
                        r_timestamp = row[0]
                        if compare_timestamps(
                            db_timestamp=r_timestamp, import_timestamp=timestamp
                        ):
                            logger.debug(
                                f"Current Bestseller list does not exist. Inserting"
                            )
                            save_data = True
                        else:
                            logger.debug(f"Current Bestseller list does exist. ")
                    if save_data:
                        self.bestseller_inserts += 1
                        for game in games_list:
                            self.bestseller_entry_inserts += 1
                            if not dry_run:
                                cur.execute(
                                    "INSERT INTO bestseller(store_id,position,hash_id,timestamp,concept) VALUES( %s,%s,%s,%s,%s) RETURNING id",
                                    (
                                        store_id,
                                        game["rank"],
                                        hash_id,
                                        timestamp,
                                        game["id"],
                                    ),
                                )
                            row = cur.fetchone()
                            if row:
                                bestseller_id = row[0]
                                cur.execute(
                                    f"SELECT id FROM concepts Where concept = {game['id']}"
                                )
                                row = cur.fetchone()
                                if row:
                                    concept_id = row[0]
                                    if not dry_run:
                                        cur.execute(
                                            "INSERT INTO concept_bestseller(concept_id,bestseller_id) VALUES (%s,%s)",
                                            (concept_id, bestseller_id),
                                        )

                        conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            logger.error(region)
            logger.error(game)
            logger.error(traceback.format_exc())
            self.insert_bestseller_error += 1
            self.return_code = 1

    async def insert_preorders(
        self,
        config: dict,
        games_list: list,
        timestamp: str,
        region: str,
        dry_run: bool,
    ):
        logger.debug("Entering insert_preorders")
        hash_id = hash(timestamp)
        try:
            save_data = False
            with psycopg2.connect(**config) as conn:
                with conn.cursor() as cur:
                    store = region.upper()
                    cur.execute(f"SELECT id FROM store Where key = '{store}'")
                    row = cur.fetchone()
                    store_id = row[0]

                    cur.execute(
                        f"SELECT timestamp FROM preorders Where store_id = {store_id} ORDER BY timestamp DESC"
                    )
                    row = cur.fetchone()
                    if not row:
                        save_data = True
                        logger.debug(f"Preorder list does not exist. Inserting")
                    else:
                        r_timestamp = row[0]
                        if compare_timestamps(
                            db_timestamp=r_timestamp, import_timestamp=timestamp
                        ):
                            logger.debug(
                                f"Current Preorder list does not exist. Inserting"
                            )
                            save_data = True
                        else:
                            logger.debug(f"Preorder list does exist. ")
                    if save_data:
                        self.preorder_inserts += 1
                        for game in games_list:
                            self.preorder_entry_inserts += 1
                            if not dry_run:
                                cur.execute(
                                    "INSERT INTO preorders(store_id,position,hash_id,timestamp,product) VALUES( %s,%s,%s,%s,%s) RETURNING id",
                                    (
                                        store_id,
                                        game["rank"],
                                        hash_id,
                                        timestamp,
                                        game["id"],
                                    ),
                                )
                        if not dry_run:
                            conn.commit()
                        else:
                            conn.rollback()

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("error:", error)
            logger.error(traceback.format_exc())
            self.insert_preorders_error += 1

    async def prepare_concepts(
        self,
        store_dict: dict,
        import_list: dict,
        data_store: str,
        dry_run: bool,
        primary_stores: list,
    ):
        try:
            logger.debug("Entering prepare_concepts")
            config = load_config()
            ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            games_to_process = {}
            games_to_process = {
                game["id"]: store
                for store in import_list
                for game in import_list[store]
                if game["id"] not in games_to_process
            }
            sem = asyncio.Semaphore(3)
            tasks = []
            insert_tasks = []
            results = []

            games_to_finally_process = {
                id: store
                for id, store in games_to_process.items()
                if id not in self.concepts_processed
            }
            for id in games_to_finally_process:
                self.concepts_processed.append(id)
            self.concepts_processed_by_store[data_store] = len(games_to_finally_process)
            for id in games_to_finally_process:
                task = asyncio.create_task(
                    gather_game_data(
                        sem=sem,
                        id=id,
                        region=store_dict[games_to_process[id]]["sub"],
                        link_type="/concept/",
                    )
                )
                tasks.append(task)
            completed_tasks = await asyncio.gather(*tasks)
            logger.debug("Collected Concepts")
            for future in completed_tasks:
                results.append(future)
            logger.debug(f"Amount of Concepts: {len(results)}")

            for game in results:
                if game:
                    await self.insert_concept_data(
                        config=config,
                        game=game,
                        timestamp=ts,
                        dry_run=dry_run,
                    )

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            logger.error(traceback.format_exc())

    async def search_for_products(self, config: dict, products: str):
        not_in_table = []
        sql = f"SELECT prod FROM (VALUES {products}) AS prods(prod) WHERE prod NOT IN (SELECT product FROM products)"
        with psycopg2.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                if rows:
                    for row in rows:
                        not_in_table.append(row[0])

        return not_in_table

    async def prepare_products(
        self,
        store_dict: dict,
        import_list: dict,
        data_store: str,
        dry_run: bool,
        primary_stores: list,
    ):
        try:
            config = load_config()
            ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            games_to_process = {}
            games_to_process = {
                game["id"]: store
                for store in import_list
                for game in import_list[store]
                if game["id"] not in games_to_process
            }
            # products_to_check = [
            #    f"('{product}')" for store in import_list for game in import_list[store]
            # ]
            products_to_check = [f"('{product}')" for product in games_to_process]
            products_to_check = ",".join(products_to_check)
            # products_to_check = [
            #   game for store in import_list for game in import_list[store]
            # ]
            new_products = await self.search_for_products(
                config=config, products=products_to_check
            )
            games_to_process = {
                key: data
                for key, data in games_to_process.items()
                if key in new_products
            }
            logger.debug(f"Amount of Products: {len(games_to_process)}")

            if len(games_to_process) > 0:
                sem = asyncio.Semaphore(3)
                tasks = []
                results = []
                concept_tasks = []
                concept_results = []
                for game in games_to_process:
                    task = asyncio.create_task(
                        gather_game_data(
                            sem=sem,
                            id=game,
                            link_type="/product/",
                            region=store_dict[games_to_process[game]]["sub"],
                        )
                    )
                    tasks.append(task)
                completed_tasks = await asyncio.gather(*tasks)
                for future in completed_tasks:
                    if future:
                        results.append(future)
                logger.info(results)
                unsorted_concepts = [
                    f"({game['concept']})" for game in results if game["concept"]
                ]
                concepts = numpy.unique(unsorted_concepts)
                concepts = ",".join(concepts)
                logger.info(concepts)
                concepts_to_insert = await check_for_concepts(
                    config=config, concepts=concepts
                )
                concepts_to_insert_dict = {}
                concepts_to_insert_dict = {
                    concept: game["region"]
                    for concept in concepts_to_insert
                    for game in results
                    if concept == game["concept"]
                }

                logger.debug(f"Amount of Concepts to insert: {len(concepts_to_insert)}")
                for concept in concepts_to_insert_dict:
                    gather_task = asyncio.create_task(
                        gather_game_data(
                            sem=sem,
                            id=str(concept),
                            region=concepts_to_insert_dict[concept],
                            link_type="/concept/",
                        )
                    )
                    concept_tasks.append(gather_task)
                completed_tasks = await asyncio.gather(*concept_tasks)
                for future in completed_tasks:
                    concept_results.append(future)

                for game in concept_results:
                    await self.insert_concept_data(
                        config=config,
                        game=game,
                        timestamp=ts,
                        dry_run=dry_run,
                    )

                for game in results:
                    await self.insert_product_data(
                        config=config,
                        game=game,
                        timestamp=ts,
                        dry_run=dry_run,
                    )
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            logger.error(game)
            logger.error(traceback.format_exc())

    async def result_log(self):
        logger.info(f"Inserted Concepts: {self.concept_inserts}")
        logger.info(f"Inserted Ratings: {self.concept_rating_inserts}")
        logger.info(f"Inserted Products: {self.product_inserts}")
        logger.info(f"Inserted Prices: {self.product_price_inserts}")
        logger.info(f"GS Product Inserts: {self.product_inserted_into_game_store }")
        logger.info(f"GS Concept Inserts: {self.concept_inserted_into_game_store }")
        logger.info(f"Insert Product Errors: {self.insert_product_error}")
        logger.info(f"Insert Concept Errors: {self.insert_concept_error}")
        logger.info(f"Insert Bestseller Errors: {self.insert_bestseller_error}")
        logger.info(f"Insert Preorders Errors: {self.insert_preorders_error}")
        logger.info(f"Return Code: {self.return_code}")


async def check_for_orig_country(config: dict, id: str):
    sql = f"SELECT s.COMPONENT FROM store s JOIN concepts co ON s.key = co.import_region WHERE co.concept = {id};"
    with psycopg2.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            if row:
                region = row[0]
                return region
            else:
                return


async def sync_out_of_date(dry_run: bool, force: bool):
    config = load_config()
    """sql = select co.concept from concepts co
            JOIN (SELECT concept_id, MAX(timestamp) AS newest_timestamp
            FROM ratings    GROUP BY concept_id) ra  on co.id = ra.concept_id
            WHERE EXTRACT(DAY FROM ((NOW()at time zone 'utc') - TO_TIMESTAMP(newest_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))::INTERVAL) >= 1
            order by newest_timestamp;"""
    sql = """SELECT c.concept FROM concepts c WHERE c.images IS NULL OR c.release_date IS NULL OR c.invariant_name IS NULL
            UNION
            select co.concept from concepts co
            JOIN (SELECT concept_id, MAX(timestamp) AS newest_timestamp
            FROM ratings    GROUP BY concept_id) ra  on co.id = ra.concept_id
            WHERE EXTRACT(HOUR FROM ((NOW()at time zone 'utc') - TO_TIMESTAMP(newest_timestamp, 'YYYY-MM-DD"T"HH24:MI:SS"Z"'))::INTERVAL) >= 20"""
    concept_arr = {}
    insert_tasks = []
    tasks = []
    results = []
    sem = asyncio.Semaphore(3)
    ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    insert_handler = insert()
    concept_arr = await collect_db_items(config=config, query=sql, one_column=True)
    results = await gather_item_data(
        config=config,
        sem=sem,
        item_type="/concept/",
        items=concept_arr,
        lookup_region=True,
    )
    logger.info(f"Amount of Games: {len(results)}")
    _ = await inserts_tasks(
        config=config,
        items=results,
        handler=insert_handler,
        ts=ts,
        item_type="/concept/",
        dry_run=dry_run,
        force=force,
    )
    _ = await inserts_tasks(
        config=config,
        items=results,
        handler=insert_handler,
        ts=ts,
        item_type="/product/",
        dry_run=dry_run,
        force=force,
    )

    await insert_handler.result_log()


async def collect_db_items(config: dict, query: str, one_column: bool = False):
    items = []
    with psycopg2.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            if rows:
                for row in rows:
                    if one_column:
                        items.append({row[0]: ""})
                    else:
                        items.append({row[0]: row[1]})
    return items


async def gather_item_data(
    config: dict,
    sem: asyncio.Semaphore,
    item_type: str,
    items: list,
    redirect_region: str = "",
    force_region: bool = False,
    lookup_region: bool = False,
):
    tasks = []
    results = []
    for item in items:
        for id, region in item.items():
            if region == "" and lookup_region:
                region = await check_for_orig_country(config=config, id=id)
                if region:
                    pass
                else:
                    region = "en-us"
            task = asyncio.create_task(
                gather_game_data(
                    sem=sem,
                    id=str(id),
                    region=region if not force_region else redirect_region,
                    link_type=item_type,
                )
            )
            tasks.append(task)
    completed_tasks = await asyncio.gather(*tasks)
    for future in completed_tasks:
        results.append(future)
    return results


async def inserts_tasks(
    config: dict,
    items: list,
    handler: insert,
    ts: str,
    item_type: str,
    dry_run: bool,
    force: bool = False,
    custom_list: bool = False,
):
    tasks = []
    if item_type == "/concept/":
        func = handler.insert_concept_data
    elif item_type == "/product/":
        func = handler.insert_product_data
    for game in items:
        if game:
            if item_type == "/concept/":
                task = asyncio.create_task(
                    func(
                        config=config,
                        game=game,
                        timestamp=ts,
                        dry_run=dry_run,
                        force=force,
                        custom_list=custom_list,
                    )
                )
            elif item_type == "/product/":
                task = asyncio.create_task(
                    func(
                        config=config,
                        game=game,
                        timestamp=ts,
                        dry_run=dry_run,
                        force=force,
                    )
                )
            tasks.append(task)
    completed_tasks = await asyncio.gather(*tasks)
    return completed_tasks


async def synchronize_list_data(dry_run: bool):
    config = load_config()
    p_sql = """SELECT pr.product,st.component FROM products pr
            JOIN game_store gs ON pr.id = gs.product_id
            JOIN store st ON st.id = gs.store_id
            LEFT JOIN product_or_concept_name po ON gs.id = po.gs_id
            WHERE po.gs_id IS NULL
            UNION ALL
            SELECT DISTINCT pre.product,st.component
            FROM preorders pre
            JOIN products p ON pre.product = p.product
            JOIN store st ON p.region = st.key
            WHERE pre.product NOT IN (SELECT DISTINCT p.product FROM names n
            JOIN product_or_concept_name pocn ON n.id = pocn.name_id
            JOIN game_store gs ON pocn.gs_id = gs.id
            JOIN products p ON gs.product_id = p.id)
            UNION ALL
            SELECT DISTINCT ON (pre.product) pre.product,st.component FROM preorders pre
            JOIN products p ON pre.product = p.product
            LEFT JOIN game_store gs ON p.id = gs.product_id
            JOIN store st ON st.id = pre.store_id WHERE gs.id IS NULL;"""
    product_arr = []

    sem = asyncio.Semaphore(3)
    ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    insert_handler = insert()
    product_arr = await collect_db_items(config=config, query=p_sql)
    results = await gather_item_data(
        config=config, sem=sem, item_type="/product/", items=product_arr
    )

    logger.info(f"Amount of Products: {len(results)}")
    await inserts_tasks(
        config=config,
        items=results,
        handler=insert_handler,
        ts=ts,
        item_type="/product/",
        dry_run=dry_run,
    )
    c_sql = """SELECT
            c.concept,
            st.component
            FROM
            concepts c
            JOIN game_store gs ON c.id = gs.concept_id
            JOIN store st ON gs.store_id = st.id
            LEFT JOIN game_publisher gpu ON gs.id = gpu.gs_id
            LEFT JOIN publisher pu ON gpu.publisher_id = pu.id
            WHERE pu.name IS NULL
            ORDER BY c.concept LIMIT 100;"""
    concept_arr = await collect_db_items(config=config, query=c_sql)
    results = await gather_item_data(
        config=config, sem=sem, item_type="/concept/", items=concept_arr
    )
    logger.info(f"Amount of Concept: {len(results)}")
    await inserts_tasks(
        config=config,
        items=results,
        handler=insert_handler,
        ts=ts,
        item_type="/concept/",
        dry_run=dry_run,
    )
    await insert_handler.result_log()


async def custom_list_import(dry_run: bool, custom_games: dict, force: bool = False):
    try:
        game = None
        logger.info("Begin Custom Import")
        regions = ["en-us", "ja-jp", "en-gb"]
        config = load_config()
        ts = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        sem = asyncio.Semaphore(3)
        tasks = []
        payload = []
        results = []
        specific_products = []
        insert_handler = insert()
        for region in regions:
            gather_region = region
            if region == "en-gb":
                if len(custom_games) > 10:
                    del custom_games[234026]
                    del custom_games[232844]
                    del custom_games[230138]
                    del custom_games[221826]
            for id in custom_games:
                _, is_concept = validate_game(game=str(id))
                if is_concept:
                    link_type = "/concept/"
                else:
                    link_type = "/product/"
                    if id.startswith("J") and region != "ja-jp":
                        continue
                    elif id.startswith("U") and region != "en-us":
                        continue
                    elif id.startswith("E") and region != "en-gb":
                        continue
                    specific_products.append(id)
                task = asyncio.create_task(
                    gather_game_data(
                        sem=sem,
                        id=str(id),
                        region=region,
                        link_type=link_type,
                    )
                )
                tasks.append(task)
            completed_tasks = await asyncio.gather(*tasks)
        for future in completed_tasks:
            results.append(future)
        logger.info(f"Amount of Concepts Regions Added: {len(results)}")
        concepts_to_process = {}
        concepts_to_process = {
            game["concept"]: game
            for game in results
            if game
            if game["concept"] not in concepts_to_process
        }
        payload = list(concepts_to_process.values())
        await inserts_tasks(
            config=config,
            items=payload,
            handler=insert_handler,
            ts=ts,
            item_type="/concept/",
            dry_run=dry_run,
            force=force,
            custom_list=True,
        )

        logger.info(f"Completed Concepts entering Products")
        products_to_process = {}
        products_to_process = {
            game["product"]: game
            for game in results
            if game
            if game["product"] not in products_to_process
        }
        payload = list(products_to_process.values())
        await inserts_tasks(
            config=config,
            items=payload,
            handler=insert_handler,
            ts=ts,
            item_type="/product/",
            dry_run=dry_run,
            force=force,
        )
        await insert_handler.result_log()

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        logger.error(game)
        logger.error(traceback.format_exc())
