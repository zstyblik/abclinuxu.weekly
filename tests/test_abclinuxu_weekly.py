"""Tests related to abclinuxu_weekly."""

import os
from datetime import datetime

import pytest
from freezegun import freeze_time

import abclinuxu_weekly  # noqa: I202,I100

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


@pytest.mark.parametrize("test_data", [("20.02.2010")])
def test_convert_date(test_data):
    """Test that convert_date() works as expected."""
    result = abclinuxu_weekly.convert_date(test_data)
    dtime = datetime.utcfromtimestamp(result)
    assert dtime.strftime("%d.%m.%Y") == test_data


@pytest.mark.parametrize(
    "fetch_type,html_line,expected",
    [
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="clanky",
                to_fetch="articles",
            ),
            "    7.1.2022 00:30 |",
            "7.1.2022",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="clanky",
                to_fetch="articles",
            ),
            # NOTE(zstyblik): well, this is interesting.
            "    7.1.2022 aasdfsa",
            "7.1.2022",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="clanky",
                to_fetch="articles",
            ),
            "abcefg",
            "",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="clanky",
                to_fetch="articles",
            ),
            "abc efg",
            "",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="zpravicky",
                to_fetch="news",
            ),
            '<a href="/lide/pytest">pytest</a> | 10.1.2022 08:00 |',
            "10.1.2022",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="zpravicky",
                to_fetch="news",
            ),
            '<a href="/lide/pytest">pytest</a> | 10.1.2022',
            "",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="zpravicky",
                to_fetch="news",
            ),
            "abcefg",
            "",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="zpravicky",
                to_fetch="news",
            ),
            "| abcefg",
            "",
        ),
        (
            abclinuxu_weekly.FetchType(
                collect_start="pytest",
                fetch_type="zpravicky",
                to_fetch="news",
            ),
            "| a bcefg",
            "",
        ),
    ],
)
def test_fetchtype_extract_date(fetch_type, html_line, expected):
    """Test FetchType.extract_date() works as expected."""
    result = fetch_type.extract_date(html_line)
    assert result == expected


def test_fetchtype_extract_date_exception():
    """Test FetchType.extract_date() raises NotImplementedError exception."""
    fetch_type = abclinuxu_weekly.FetchType(
        collect_start="pytest",
        fetch_type="pytest",
        to_fetch="pytest",
    )
    with pytest.raises(NotImplementedError):
        fetch_type.extract_date(" 7.1.2022 00:31 |")


def test_get_html_articles_single_fetch(requests_mock):
    """Test get_html() output for articles is as expected.

    Only single HTTP GET is performed since stop date is present on the page.
    """
    fetch_type = abclinuxu_weekly.FETCH_TYPES["clanky"]
    url = abclinuxu_weekly.URL_TEMPLATE.format(
        to_fetch=fetch_type.to_fetch,
        offset=str(0),
        count=str(abclinuxu_weekly.COUNT),
    )

    test_data_fname = os.path.join(
        SCRIPT_PATH, "files", "articles_sac_p1_rsp.txt"
    )
    with open(test_data_fname, "r", encoding="utf-8") as fhandle:
        test_data = fhandle.read()

    requests_mock.get(url, text=test_data, real_http=False)

    with freeze_time("2022-01-13"):
        result = abclinuxu_weekly.get_html(fetch_type)

    expected_data_fname = os.path.join(
        SCRIPT_PATH, "files", "articles_sac_p1_expected.txt"
    )
    with open(expected_data_fname, "r", encoding="utf-8") as fhandle:
        expected_data = fhandle.read()

    assert result == expected_data


def test_get_html_news_single_fetch(requests_mock):
    """Test get_html() output for news is as expected.

    Only single HTTP GET is performed since stop date is present on the page.
    """
    fetch_type = abclinuxu_weekly.FETCH_TYPES["zpravicky"]
    url = abclinuxu_weekly.URL_TEMPLATE.format(
        to_fetch=fetch_type.to_fetch,
        offset=str(0),
        count=str(abclinuxu_weekly.COUNT),
    )

    test_data_fname = os.path.join(SCRIPT_PATH, "files", "news_sac_p1_rsp.txt")
    with open(test_data_fname, "r", encoding="utf-8") as fhandle:
        test_data = fhandle.read()

    requests_mock.get(url, text=test_data, real_http=False)

    with freeze_time("2022-01-13"):
        result = abclinuxu_weekly.get_html(fetch_type)

    expected_data_fname = os.path.join(
        SCRIPT_PATH, "files", "news_sac_p1_expected.txt"
    )
    with open(expected_data_fname, "r", encoding="utf-8") as fhandle:
        expected_data = fhandle.read()

    assert result == expected_data


def test_get_html_news_multi_fetch(requests_mock):
    """Test that get_html() can fetch data from multiple pages.

    HTTP responses are crafted for this test case and stop date is at 3rd page.
    """
    fetch_type = abclinuxu_weekly.FETCH_TYPES["zpravicky"]
    for i in range(0, 3):
        fname = "news_continue_p{:d}_rsp.txt".format(i + 1)
        fpath = os.path.join(SCRIPT_PATH, "files", fname)
        with open(fpath, "r", encoding="utf-8") as fhandle:
            data = fhandle.read()

        url = abclinuxu_weekly.URL_TEMPLATE.format(
            to_fetch=fetch_type.to_fetch,
            offset=str(i * abclinuxu_weekly.COUNT),
            count=str(abclinuxu_weekly.COUNT),
        )
        requests_mock.get(url, text=data, real_http=False)

    with freeze_time("2022-01-13"):
        result = abclinuxu_weekly.get_html(fetch_type)

    expected_data_fname = os.path.join(
        SCRIPT_PATH, "files", "news_continue_p0_expected.txt"
    )
    with open(expected_data_fname, "r", encoding="utf-8") as fhandle:
        expected_data = fhandle.read()

    assert result == expected_data


def test_get_html_offset_limit(requests_mock):
    """Test that OFFSET_LIMIT is respected in get_html().

    If OFFSET_LIMIT isn't respected, we should see exception from requests-mock.
    """
    fetch_type = abclinuxu_weekly.FETCH_TYPES["zpravicky"]
    for i in range(0, 3):
        url = abclinuxu_weekly.URL_TEMPLATE.format(
            to_fetch=fetch_type.to_fetch,
            offset=str(i * abclinuxu_weekly.COUNT),
            count=str(abclinuxu_weekly.COUNT),
        )
        requests_mock.get(url, text="test", real_http=False)

    result = abclinuxu_weekly.get_html(fetch_type)

    assert result == ""


def test_html_to_text():
    """Test that html2text works.

    Note that this is just a dummy/smoke test.
    """
    input_text = '<p><a href="/foo">test link</a></p>'
    expected_text = (
        "[test link][1]\n"
        + "\n"
        + "   [1]: https://www.example.com/foo\n"
        + "\n"
    )
    baseurl = "https://www.example.com"
    inline_links = False
    result = abclinuxu_weekly.html_to_text(input_text, baseurl, inline_links)
    assert result == expected_text


def test_sendmail(smtpserver):
    """Test that sendmail() works as expected."""
    expected_email_subject = "AbcLinuxu zpravicky 05/2010"
    expected_email_from = "pytest@localhost"
    expected_email_to = "pytest1@localhost"
    expected_email_payload = "pytest\ntest"

    with freeze_time("2010-02-10"):
        abclinuxu_weekly.sendmail(
            "zpravicky",
            expected_email_payload,
            expected_email_from,
            [expected_email_to],
            host=smtpserver.addr[0],
            port=smtpserver.addr[1],
        )

    assert len(smtpserver.outbox) == 1

    email = smtpserver.outbox[0]
    assert email["Subject"] == expected_email_subject
    assert email["From"] == expected_email_from
    assert email["To"] == expected_email_to
    email_payload = email.get_payload()
    assert email_payload == expected_email_payload
