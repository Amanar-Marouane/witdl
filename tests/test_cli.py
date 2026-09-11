"""Tests for witdl.cli — URL detection and command routing."""

import argparse
import unittest
from unittest import mock

from witdl import cli


def _ns(**kwargs) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


class TestLooksLikeUrl(unittest.TestCase):
    def test_http_url(self):
        self.assertTrue(cli._looks_like_url("http://witanime.you/anime/foo/"))

    def test_https_url(self):
        self.assertTrue(cli._looks_like_url("https://witanime.you/anime/foo/"))

    def test_schemeless_url(self):
        self.assertTrue(cli._looks_like_url("witanime.you/anime/foo/"))

    def test_plain_query(self):
        self.assertFalse(cli._looks_like_url("iwamoto senpai"))

    def test_surrounding_whitespace_is_stripped(self):
        self.assertTrue(cli._looks_like_url("  https://witanime.you/anime/foo/  "))


class TestCmdSearchRouting(unittest.TestCase):
    """`witdl search` must route URLs instead of searching for them literally."""

    def test_url_without_download_routes_to_info(self):
        url = "https://witanime.you/anime/foo/"
        with mock.patch.object(cli, "cmd_info") as m_info, \
                mock.patch.object(cli, "cmd_download") as m_download, \
                mock.patch.object(cli, "search") as m_search:
            cli.cmd_search(_ns(query=url, download=False))

        m_info.assert_called_once()
        self.assertEqual(m_info.call_args.args[0].url_or_query, url)
        m_download.assert_not_called()
        m_search.assert_not_called()

    def test_url_with_download_routes_to_download(self):
        url = "https://witanime.you/anime/foo/"
        with mock.patch.object(cli, "cmd_info") as m_info, \
                mock.patch.object(cli, "cmd_download") as m_download, \
                mock.patch.object(cli, "search") as m_search:
            cli.cmd_search(_ns(query=url, download=True))

        m_download.assert_called_once()
        routed = m_download.call_args.args[0]
        self.assertEqual(routed.url_or_query, url)
        self.assertIsNone(routed.episodes)
        m_info.assert_not_called()
        m_search.assert_not_called()

    def test_schemeless_url_is_detected(self):
        url = "witanime.you/episode/%d9%81%d9%8a%d9%84%d9%85-the-ribbon-hero/"
        with mock.patch.object(cli, "cmd_info") as m_info, \
                mock.patch.object(cli, "search") as m_search:
            cli.cmd_search(_ns(query=url, download=False))

        m_info.assert_called_once()
        m_search.assert_not_called()

    def test_plain_query_still_searches(self):
        with mock.patch.object(cli, "search", return_value=[]) as m_search, \
                mock.patch.object(cli, "cmd_info") as m_info, \
                mock.patch.object(cli, "cmd_download") as m_download:
            cli.cmd_search(_ns(query="iwamoto senpai", download=False))

        m_search.assert_called_once_with("iwamoto senpai")
        m_info.assert_not_called()
        m_download.assert_not_called()

    def test_missing_download_attr_defaults_to_info(self):
        """Namespaces created without the flag (e.g. older call sites) still work."""
        url = "https://witanime.you/anime/foo/"
        with mock.patch.object(cli, "cmd_info") as m_info, \
                mock.patch.object(cli, "cmd_download") as m_download:
            cli.cmd_search(_ns(query=url))

        m_info.assert_called_once()
        m_download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
