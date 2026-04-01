from datetime import datetime, timedelta, UTC
import logging
import cli
from logger_config import setup_logging


logger = logging.getLogger(__name__)
def main():

    setup_logging()

    parser = cli.build_parser()
    args = parser.parse_args()
    result = args.handler(args)
    if result is None:
        print("Operation is failed")
        logger.info("Operation is failed %s", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))
        return
    
    logger.info("Operation is success %s", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))
    print(result)



if __name__ == "__main__":
    main()