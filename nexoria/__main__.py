import logging

from .bot import NexoriaBot
from .settings import Settings


def main() -> None:
    settings = Settings.load()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    NexoriaBot(settings).run(settings.token, log_handler=None)


if __name__ == "__main__":
    main()
