from __future__ import annotations

import argparse
import asyncio
import logging

from .config import load_config
from .daemon import VtsDaemon


def main() -> None:
    parser = argparse.ArgumentParser(description="VTS daemon")
    parser.add_argument("--config", help="path to vtsd.json", default=None)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    cfg = load_config(args.config)
    daemon = VtsDaemon(cfg)
    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
