import logging
import os
from pathlib import Path
import sys

from rapi.config import Config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def main():
    conf_path = Path(os.path.curdir, "feeds.yml")

    if len(sys.argv) > 1:
        conf_path = Path.resolve(Path(sys.argv[1]))

    log.info("Configuring Rapi with configuration file: %s", conf_path)
    conf = Config.from_config(conf_path)

    for website in conf.websites:
        try:
            website.retrieve_site_data()
            website.write_feeds(conf.destination_folder)
        except Exception:
            log.exception("Unable to generate feeds for %r.", website.url)


if __name__ == "__main__":
    main()
