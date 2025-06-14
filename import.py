import asyncio
import datetime as dt
import logging
from datetime import timezone

from async_soup_and_data import (
    get_data_for_bestsellers_import,
    get_data_for_preorders_import,
    pretty_file,
)
from database import insert, load_config
from psbot_commands import link_types, store_dict

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


###### Importer for the datbase               #####
###### Irrevelant for the nomal bot functions #####


async def store_data_in_db(
    handler: insert,
    store_dict: dict,
    get_data_function: callable,
    preparation_function: callable,
    store_data_function: callable,
    link_type: str,
    dry_run: bool,
):
    primary_stores = ["JP", "KR", "US", "GB", "FR", "DE", "HK", "AU", "TW"]
    config = load_config()
    ts = dt.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sem = asyncio.Semaphore(4)
    tasks = []
    results = {}
    for store in store_dict:
        task = asyncio.create_task(
            get_data_function(
                sem=sem,
                region=store_dict[store]["sub"],
                link_type=link_type,
                end_page=8,
            )
        )
        tasks.append(task)
    completed_tasks = await asyncio.gather(*tasks)
    logger.info("Completed Gathering Ranking Data")
    for future in completed_tasks:
        if future:
            results.update(future)
    error_list = []
    payload = {}
    for store, data in results.items():
        if data != "Error":
            payload[store] = data
            await preparation_function(
                store_dict=store_dict,
                import_list=payload,
                data_store=store,
                dry_run=dry_run,
                primary_stores=primary_stores,
            )
            payload = {}
        else:
            print("error")
            error_list.append(store)
    # for store in error_list:
    #   del results[store]

    logger.info("Completed Preparation Function")
    tasks = []
    for store in store_dict:
        if store not in error_list:
            task = asyncio.create_task(
                store_data_function(
                    config=config,
                    games_list=results[store],
                    timestamp=ts,
                    region=store,
                    dry_run=dry_run,
                )
            )
        tasks.append(task)
    completed_tasks = await asyncio.gather(*tasks)
    logger.info("Completed Storing Data Function")


async def main():
    # store_dict = {
    #    "DK": {"name": "Denmark", "sub": "en-dk", "key": "DK", "flag": "🇩🇰"},
    #    "EC": {"name": "Ecuador", "sub": "es-ec", "key": "EC", "flag": "🇪🇨"},
    #    "SV": {"name": "El Salvador", "sub": "es-sv", "key": "SV", "flag": "🇸🇻"},
    #    "FI": {"name": "Finland", "sub": "en-fi", "key": "FI", "flag": "🇫🇮"},
    #    "GR": {"name": "Greece", "sub": "en-gr", "key": "GR", "flag": "🇬🇷"},
    #    "GT": {"name": "Guatemala", "sub": "es-gt", "key": "GT", "flag": "🇬🇹"},
    #    "HN": {"name": "Honduras", "sub": "es-hn", "key": "HN", "flag": "🇭🇳"},
    # }
    # store_dict = {
    #    "US": {"name": "United States", "sub": "en-us", "key": "US", "flag": "🇺🇸"},
    # }
    dry_run = False
    if dry_run:
        logger.info("Dry run. Data will not be saved")
    else:
        logger.info("Active run. Saving Data")
    insert_handler = insert()
    payload = {}
    i = 1
    for entry, data in store_dict.items():
        payload[entry] = data
        i += 1
        if i == 6 or entry == list(store_dict.keys())[-1]:
            i = 0
            cset = [entry for entry in payload]
            logger.info(f"Country Set: {cset}")
            await store_data_in_db(
                handler=insert_handler,
                store_dict=payload,
                get_data_function=get_data_for_bestsellers_import,
                preparation_function=insert_handler.prepare_concepts,
                store_data_function=insert_handler.insert_bestsellers,
                link_type=link_types["120"],
                dry_run=dry_run,
            )
            logger.info("Completed Bestseller Import")
            await store_data_in_db(
                handler=insert_handler,
                store_dict=payload,
                get_data_function=get_data_for_preorders_import,
                preparation_function=insert_handler.prepare_products,
                store_data_function=insert_handler.insert_preorders,
                link_type=link_types["preorder"],
                dry_run=dry_run,
            )
            logger.info("Completed Preorder Import")

            payload = {}
    for store in insert_handler.concepts_processed_by_store:
        logger.info(
            f"{insert_handler.concepts_processed_by_store[store]} concepts processed for {store}"
        )
    for store in insert_handler.products_processed_by_store:
        logger.info(
            f"{insert_handler.products_processed_by_store[store]} products processed for {store}"
        )
    logger.info(f"Inserted Concepts: {insert_handler.concept_inserts}")
    logger.info(f"Inserted Ratings: {insert_handler.concept_rating_inserts}")
    logger.info(f"Inserted Products: {insert_handler.product_inserts}")
    logger.info(f"Inserted Prices: {insert_handler.product_price_inserts}")
    logger.info(f"Inserted Bestseller Lists:   { insert_handler.bestseller_inserts}")
    logger.info(
        f"Inserted Bestseller Entries:   {  insert_handler.bestseller_entry_inserts }"
    )
    logger.info(f"Inserted Preorder Lists:   {  insert_handler.preorder_inserts }")
    logger.info(
        f"Inserted Preorder Entries:   {  insert_handler.preorder_entry_inserts }"
    )
    logger.info(
        f"GS Product Inserts: {insert_handler.product_inserted_into_game_store }"
    )
    logger.info(
        f"GS Concept Inserts: {insert_handler.concept_inserted_into_game_store }"
    )
    logger.info(f"Insert Product Errors: {insert_handler.insert_product_error}")
    logger.info(f"Insert Concept Errors: {insert_handler.insert_concept_error}")
    logger.info(f"Insert Bestseller Errors: {insert_handler.insert_bestseller_error}")
    logger.info(f"Insert Preorders Errors: {insert_handler.insert_preorders_error}")
    logger.info(f"Return Code: {insert_handler.return_code}")
    logger.info("IMPORT COMPLETE")


if __name__ == "__main__":
    asyncio.run(main())
