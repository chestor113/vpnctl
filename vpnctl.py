import logging
import cli
from logger_config import setup_logging
from pathlib import Path


logger = logging.getLogger(__name__)


def print_result_data(data: dict):
    for key, value in data.items():
        print(f"{key}: {value}")


def main():
    setup_logging()

    parser = cli.build_parser()
    args = parser.parse_args()

    result = args.handler(args)

    if not result:
        print(f"ERROR: {result.error}")
        logger.error("Operation failed: %s", result.error)
        return

    if result.data:
        print_result_data(result.data)

    logger.info("Operation completed successfully")


if __name__ == "__main__":
    main()