import asyncio
import os
import signal

from .feishu import load_bot_from_env


async def _run() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bot = load_bot_from_env(project_root)
    stop_event = asyncio.Event()

    def _stop(*_args) -> None:
        stop_event.set()

    try:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _stop)
            except Exception:
                pass
    except Exception:
        pass

    await bot.start()
    await stop_event.wait()
    await bot.stop()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

