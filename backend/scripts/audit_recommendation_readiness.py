import asyncio
import json

from app.db.session import async_session, engine
from app.recommendations.readiness import build_recommendation_readiness_report


async def async_main() -> None:
    try:
        async with async_session() as session:
            report = await build_recommendation_readiness_report(session)
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
