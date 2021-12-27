#!/usr/bin/env python3
"""Custom version of html2markdown with possibility to set baserurl.

2021/Dec/27 @ Zdenek Styblik
zdenek [dot] styblik [snail] gmail [dot] com
"""
import argparse
import sys

from html2text import HTML2Text


def parse_args() -> argparse.Namespace:
    """Return parsed CLI args."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reference-links",
        dest="inline_links",
        action="store_false",
        default=True,
        help="Use reference style links instead of inline links",
    )
    parser.add_argument(
        "--decode-errors",
        dest="decode_errors",
        default="strict",
        help=(
            "What to do in case of decode errors.'ignore', 'strict' and 'replace' are "
            "acceptable values"
        ),
    )
    parser.add_argument(
        "--base-url",
        dest="baseurl",
        default="",
        help=(
            "Base URL of relative links"
        ),
    )
    parser.add_argument("filename", nargs="?")
    parser.add_argument("encoding", nargs="?", default="utf-8")
    return parser.parse_args()


def main() -> None:
    """Run HTML2Text and turn HTML into markdown."""
    args = parse_args()
    #
    if args.filename and args.filename != "-":
        with open(args.filename, "rb") as fhandle:
            data = fhandle.read()
    else:
        data = sys.stdin.buffer.read()

    try:
        html = data.decode(args.encoding, args.decode_errors)
    except UnicodeDecodeError as err:
        print("Warning: Use the --decode-errors=ignore flag.")
        raise err

    processor = HTML2Text(baseurl=args.baseurl)
    processor.inline_links = args.inline_links
    sys.stdout.write(processor.handle(html))


if __name__ == "__main__":
    main()
