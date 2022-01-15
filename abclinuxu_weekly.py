#!/usr/bin/env python3
"""Get articles/news from AbcLinuxu.cz for past week from now and mail them.

1. Get all articles/news from Abclinuxu.cz for past week from now
2. parse HTML and transform it into markdown
3. mailout

Patches, comments, improvements - always welcome.
Trolls - keep it for your self :p

2010/Feb/20 @ Zdenek Styblik (original Perl version)
zdenek [dot] styblik [snail] gmail [dot] com

License:
You want my car's license plate again, or what?

Yo Adrian, I did it!
"""
import argparse
import logging
import re
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from typing import List

import requests
from html2text import HTML2Text

BASEURL = "https://www.abclinuxu.cz"
COUNT = 50
HTTP_TIMEOUT = 30  # seconds
# Limit offset from the start to 3 pages, resp. (3 - 1) * COUNT
OFFSET_LIMIT = 100
RE_DATE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+ [0-9]+:[0-9]+")
RE_INT = re.compile(r"[0-9]+")
RE_LEADING_SPACES = re.compile(r"^\s+")
RE_TRAILING_SPACES = re.compile(r"\s+$")
SMTP_TIMEOUT = 30  # seconds
URL_TEMPLATE = (
    "https://www.abclinuxu.cz/History?type={to_fetch}&from={offset}"
    "&count={count}&orderBy=create&orderDir=desc"
)


@dataclass
class FetchType:
    """Class holds data related to what's being fetched.

    This way is a bit better than dictionary.
    """

    collect_start: str
    fetch_type: str
    to_fetch: str

    def extract_date(self, text_line: str) -> str:
        """Try to extract date from given HTML line.

        Wrapper which hides difference in implementation between article and
        news. This isn't exactly the best approach, but it will do.
        """
        if self.to_fetch == "articles":
            return self.extract_article_date(text_line)

        if self.to_fetch == "news":
            return self.extract_news_date(text_line)

        # Handle just in case new type is added.
        raise NotImplementedError(
            "to_fetch '{:s}' is not supported".format(self.to_fetch)
        )

    @staticmethod
    def extract_article_date(text_line: str) -> str:
        """Find time in HTML line in Articles section.

        Returns an empty string if something goes wrong.
        """
        text_line = RE_LEADING_SPACES.sub("", text_line)
        text_line = RE_TRAILING_SPACES.sub("", text_line)
        chunks = text_line.split(" ")
        if chunks and RE_INT.search(chunks[0]):
            return chunks[0]

        return ""

    @staticmethod
    def extract_news_date(text_line: str) -> str:
        """Find time in HTML line in News section.

        Returns an empty string if something goes wrong.
        """
        if "|" not in text_line:
            return ""

        cpos = text_line.index("|")
        date_part = text_line[cpos + 2:]  # fmt:skip
        if " " not in date_part:
            return ""

        cpos = date_part.index(" ")
        date_found = date_part[0:cpos]
        if date_found and RE_INT.search(date_found):
            return date_found

        return ""


FETCH_TYPES = {
    "clanky": FetchType(
        collect_start="článků", fetch_type="clanky", to_fetch="articles"
    ),
    "zpravicky": FetchType(
        collect_start="zpráviček", fetch_type="zpravicky", to_fetch="news"
    ),
}


def convert_date(extracted_date: str) -> float:
    """Convert date in dd.mm.YYYY format to U*nix timestamp."""
    date_chunks = extracted_date.split(".")
    time_struct = time.strptime(
        "{:d}/{:d}/{:d} 12:00:00".format(
            int(date_chunks[2]),
            int(date_chunks[1]),
            int(date_chunks[0]),
        ),
        "%Y/%m/%d %H:%M:%S",
    )
    return time.mktime(time_struct)


def get_html(fetch_type: FetchType) -> str:
    """Get HTML blocks of interest from ABCLinuxu."""
    # Minus one week from now.
    date_stop = time.time() - 691200
    html_collected = ""
    heading_collected = False
    start_collect_needle = "<h1>Archiv {:s}</h1>".format(
        fetch_type.collect_start
    )
    offset = 0
    stop_processing = False
    while offset <= OFFSET_LIMIT:
        # Restart HTML collect per requested page.
        collect_html = False
        # Parser flow control. Date block cannot continue on a different page.
        in_date_block = False
        # Explanation:
        # page1 offset is 0, count 50
        # page2 offset is 50, count 50
        # page3 offset is 100, count 50
        url = URL_TEMPLATE.format(
            to_fetch=fetch_type.to_fetch,
            offset=str(offset),
            count=str(COUNT),
        )
        logging.debug("Req URL: '%s'", url)
        rsp = requests.get(url, timeout=HTTP_TIMEOUT)
        if rsp.status_code != 200:
            raise ValueError(
                "Expected HTTP Status Code 200, got {:d}".format(
                    rsp.status_code
                )
            )

        for html_line in rsp.text.split("\n"):
            html_line = html_line.strip()
            html_line = RE_LEADING_SPACES.sub("", html_line)
            html_line = RE_TRAILING_SPACES.sub("", html_line)
            if not collect_html and html_line == start_collect_needle:
                logging.debug("Beginning to collect HTML.")
                collect_html = True
                # Don't collect "Archiv XXX" multiple times when we have to
                # fetch data from multiple pages.
                if not heading_collected:
                    heading_collected = True
                else:
                    continue

            if collect_html and html_line == '<form action="/History">':
                logging.debug("Stop collecting HTML.")
                collect_html = False
                break

            if not collect_html:
                continue

            if html_line == '<p class="meta-vypis">':
                logging.debug("Start of the date block found.")
                in_date_block = True

            if in_date_block and html_line == "</p>":
                logging.debug("End of the date block found.")
                in_date_block = False
                if stop_processing:
                    offset = 10000
                    html_collected += "{}\n".format(html_line)
                    break

            if in_date_block and RE_DATE.search(html_line):
                extracted_date = fetch_type.extract_date(html_line)
                logging.debug("Raw extracted date: '%s'", extracted_date)
                if not extracted_date:
                    in_date_block = False

                if not extracted_date or not RE_INT.search(extracted_date):
                    continue

                item_date = convert_date(extracted_date)
                if item_date < date_stop:
                    logging.debug("Found stop date.")
                    # This is in order to include the whole block of author +
                    # date + comments which is couple more lines to read.
                    stop_processing = True

            html_collected += "{}\n".format(html_line)

        offset += COUNT

    return html_collected


def html_to_text(html: str, baseurl, inline_links) -> str:
    """Convert HTML to markdown(text)."""
    html_processor = HTML2Text(baseurl=baseurl)
    html_processor.inline_links = inline_links
    return html_processor.handle(html)


def main() -> None:
    """Fetch HTML, parse it, convert to markdown and mailout."""
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    fetch_type = FETCH_TYPES[args.fetch_type]
    html = get_html(fetch_type)
    html = html_to_text(html, args.baseurl, args.inline_links)
    logging.debug("HTML converted: %s", html)
    logging.debug("Mail from addr: '%s'", args.mail_from_addr)
    logging.debug("Mail to addrs: '%s'", args.mail_to_addrs)
    sendmail(
        fetch_type.fetch_type, html, args.mail_from_addr, args.mail_to_addrs
    )


def parse_args() -> argparse.Namespace:
    """Return parsed CLI args."""
    parser = argparse.ArgumentParser()
    parser.description = (
        "Get digest of ABCLinuxu's articles/news for the past week"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-a",
        "--articles",
        action="store_const",
        const="clanky",
        dest="fetch_type",
        help="Fetch and mail articles",
    )
    group.add_argument(
        "-n",
        "--news",
        action="store_const",
        const="zpravicky",
        dest="fetch_type",
        help="Fetch and mail news",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Enable debugging",
    )
    parser.add_argument(
        "--mail-from",
        dest="mail_from_addr",
        required=True,
        type=str,
        help="Mail from address",
    )
    parser.add_argument(
        "--mail-to",
        action="append",
        dest="mail_to_addrs",
        required=True,
        type=str,
        help="Mail to address(can be given multiple times)",
    )
    parser.add_argument(
        "--no-reference-links",
        dest="inline_links",
        action="store_true",
        default=False,
        help="Use inline links in markdown instead of references",
    )
    parser.add_argument(
        "--base-url",
        dest="baseurl",
        default=BASEURL,
        help="Base URL of relative links in markdown",
    )
    return parser.parse_args()


def sendmail(
    fetch_type: str,
    html: str,
    mail_from_addr: str,
    mail_to_addrs: List,
    host: str = "localhost",
    port: int = 0,
):
    """Mailout.

    Remote STMP with TLS:

        port = 465
        smtp_server = 'localhost'
        username = 'your_username'
        password = input('Type your password and press enter:')

        with smtplib.SMTP_SSL(
            smtp_server, port, timeout=SMTP_TIMEOUT
        ) as server:
            server.ehlo()
            server.login(username, password)
            for mail_to_addr in mail_to_addrs:
                msg = EmailMessage()
                [...]

    Why isn't it implemented? Because I don't need it and nobody else is using
    this script.
    """
    subject = "AbcLinuxu {:s} {:s}/{:s}".format(
        fetch_type,
        time.strftime("%W"),
        time.strftime("%Y"),
    )
    with smtplib.SMTP(host=host, port=port, timeout=SMTP_TIMEOUT) as server:
        server.ehlo()
        for mail_to_addr in mail_to_addrs:
            msg = EmailMessage()
            msg["From"] = mail_from_addr
            msg["To"] = mail_to_addr
            msg["Subject"] = subject
            # Date: Sun, 2 Jan 2022 23:45:02 +0000
            msg["Date"] = time.strftime("%a, %-d %b %Y %H:%M:%S %z")
            msg.set_payload(html.encode("utf-8"))
            msg["Content-Type"] = "text/plain; charset=utf-8"
            server.send_message(msg)


if __name__ == "__main__":
    main()
