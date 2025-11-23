#!/usr/bin/env python3
import sys
import argparse
import traceback

from coiny.core import check_accounts


def main():
    # Command line argument support
    parser = argparse.ArgumentParser(description="Crypto coin checker")
    parser.add_argument(
        "coinfile", type=argparse.FileType("r"), help="The coin JSON file"
    )
    args = parser.parse_args()

    filename = args.coinfile.name

    try:
        check_accounts(filename)
    except OSError as err:
        print(f"OS error: {err}")
    except ValueError as err:
        print(err)
    except Exception as err:
        print("Unexpected error:", sys.exc_info()[0], err)
        tb = traceback.format_exc()
        print(tb)


if __name__ == "__main__":
    main()
