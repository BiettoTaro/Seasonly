import asyncio

import httpx

from app.db.session import async_session, engine
from app.recipes.client import MealDBClient
from app.recipes.importer import (
    complete_import_run,
    create_import_run,
    fail_import_run,
    import_snapshot,
    normalize_snapshot,
)


async def async_main() -> None:
    async with async_session() as run_session:
        run = await create_import_run(run_session)

    try:
        async with httpx.AsyncClient() as http_client:
            client = MealDBClient(http_client=http_client)
            categories = await client.fetch_categories()
            ingredients = await client.fetch_ingredients()
            recipes = await client.fetch_all_recipes()
        snapshot = normalize_snapshot(
            categories=categories,
            ingredients=ingredients,
            recipes=recipes,
        )

        async with async_session() as import_session, import_session.begin():
            await import_snapshot(import_session, snapshot)

        async with async_session() as run_session:
            await complete_import_run(run_session, run.id, snapshot)
        message = "Imported {} recipes, {} ingredients, and {} categories".format(
            len(snapshot["recipes"]),
            len(snapshot["ingredients"]),
            len(snapshot["categories"]),
        )
        print(message)
    except Exception as error:
        async with async_session() as run_session:
            await fail_import_run(run_session, run.id, error)
        raise
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
