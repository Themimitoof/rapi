import logging
import os
from pathlib import Path
from typing import List

import yaml
from pydantic import ValidationError

from rapi.model.site import Site

log = logging.getLogger(__name__)


class Config:
    _conf_path: Path
    _conf: str

    destination_folder: Path
    """Destination path where all feeds will be exported."""

    websites: List[Site] = []
    """List of all websites configuration."""

    @classmethod
    def from_config(cls, path: str | Path) -> "Config":
        """
        Generate a ``Config`` instance by reading the specified configuration file.
        """

        if not os.path.exists(path):
            raise ValueError(f"The configuration '{path}' file doesn't exists.")

        conf = cls()
        with open(path, "r") as f:
            raw_conf = conf._conf = yaml.load(f.buffer, yaml.BaseLoader)
            conf._conf_path = Path(path)

            if "destination" not in raw_conf:
                log.info(
                    "No destination set in the configuration file, using default "
                    "value: 'feeds'."
                )
                conf.destination_folder = Path(os.getcwd(), "feeds")

            conf.destination_folder = Path.resolve(Path(raw_conf["destination"]))

            if not os.path.exists(conf.destination_folder):
                log.info("%r not exists, creating the folder.")
                os.mkdir(conf.destination_folder)

            if "websites" not in raw_conf:
                raise ValueError("No website configuration found.")

            for website_conf in raw_conf["websites"]:
                try:
                    log.debug("Configuring %r...", website_conf)
                    conf.websites.append(Site(**website_conf))
                except ValidationError:
                    log.exception(
                        "Unable to validate the configuration for website %r",
                        website_conf,
                    )

        return conf
