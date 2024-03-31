import argparse

from dynamodocs.launcher import Runner
from dynamodocs.mylogger import logger


def main():
    argparser = argparse.ArgumentParser(
        description="Automatic documentation generator")

    argparser.add_argument("-c", "--clear", action="store_true",
                           help="Clear the output directory before generating the documentation from scratch")

    args = argparser.parse_args()

    runner = Runner(clear=args.clear)

    runner.run()

    logger.info("Documentation task completed.")


if __name__ == "__main__":
    main()
