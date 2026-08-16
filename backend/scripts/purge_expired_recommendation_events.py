import argparse
import asyncio

from app.db.session import async_session, engine
from app.recommendations.events import purge_expired_recommendation_events

DEFAULT_INTERVAL_SECONDS = 86_400


class PurgeRecommendationEventsArguments(argparse.Namespace):
    loop: bool = False
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS


async def purge_once() -> int:
    async with async_session() as session:
        return await purge_expired_recommendation_events(session)


async def run_forever(interval_seconds: int) -> None:
    while True:
        deleted_count = await purge_once()
        print(f"Purged {deleted_count} expired recommendation events")
        await asyncio.sleep(interval_seconds)


async def async_main(*, loop: bool, interval_seconds: int) -> None:
    try:
        if loop:
            await run_forever(interval_seconds)
        else:
            deleted_count = await purge_once()
            print(f"Purged {deleted_count} expired recommendation events")
    finally:
        await engine.dispose()


def parse_args() -> PurgeRecommendationEventsArguments:
    parser = argparse.ArgumentParser(
        description="Delete identifiable recommendation events after their retention period."
    )
    _ = parser.add_argument(
        "--loop",
        action="store_true",
        help="Repeat the purge until the process is stopped.",
    )
    _ = parser.add_argument(
        "--interval-seconds",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Seconds between purge runs when --loop is enabled.",
    )
    args = PurgeRecommendationEventsArguments()
    _ = parser.parse_args(namespace=args)
    if args.interval_seconds < 60:
        parser.error("--interval-seconds must be at least 60")
    return args


def main() -> None:
    args = parse_args()
    asyncio.run(
        async_main(
            loop=args.loop,
            interval_seconds=args.interval_seconds,
        )
    )


if __name__ == "__main__":
    main()
