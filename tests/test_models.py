"""Tests for witdl.models."""

import unittest
from witdl.models import (
    Quality, DownloadStatus, Link, Episode, Anime,
    SearchResult, DownloadResult,
)


class TestQuality(unittest.TestCase):
    def test_from_str_valid(self):
        self.assertEqual(Quality.from_str("fhd"), Quality.FHD)
        self.assertEqual(Quality.from_str("hd"), Quality.HD)
        self.assertEqual(Quality.from_str("sd"), Quality.SD)

    def test_from_str_case_insensitive(self):
        self.assertEqual(Quality.from_str("FHD"), Quality.FHD)
        self.assertEqual(Quality.from_str("  Hd  "), Quality.HD)

    def test_from_str_invalid(self):
        with self.assertRaises(ValueError):
            Quality.from_str("4k")

    def test_display(self):
        self.assertEqual(Quality.FHD.display, "FHD")
        self.assertEqual(Quality.HD.display, "HD")
        self.assertEqual(Quality.SD.display, "SD")


class TestDownloadStatus(unittest.TestCase):
    def test_values(self):
        self.assertEqual(DownloadStatus.PENDING.value, "pending")
        self.assertEqual(DownloadStatus.DOWNLOADING.value, "downloading")
        self.assertEqual(DownloadStatus.COMPLETED.value, "completed")
        self.assertEqual(DownloadStatus.FAILED.value, "failed")
        self.assertEqual(DownloadStatus.SKIPPED.value, "skipped")


class TestLink(unittest.TestCase):
    def test_creation(self):
        link = Link(hoster="mediafire", url="https://example.com/file.mp4", quality=Quality.FHD)
        self.assertEqual(link.hoster, "mediafire")
        self.assertEqual(link.url, "https://example.com/file.mp4")
        self.assertEqual(link.quality, Quality.FHD)

    def test_repr(self):
        link = Link(hoster="mediafire", url="https://example.com/very-long-url-that-gets-truncated.mp4", quality=Quality.HD)
        r = repr(link)
        self.assertIn("HD", r)
        self.assertIn("mediafire", r)


class TestEpisode(unittest.TestCase):
    def test_best_link_selects_fhd_over_sd(self):
        links = [
            Link(hoster="mediafire", url="https://example.com/sd", quality=Quality.SD),
            Link(hoster="hexload", url="https://example.com/fhd", quality=Quality.FHD),
        ]
        ep = Episode(number=1, links=links)
        best = ep.best_link
        self.assertEqual(best.quality, Quality.FHD)

    def test_best_link_selects_mediafire_over_hexload(self):
        links = [
            Link(hoster="hexload", url="https://example.com/1", quality=Quality.FHD),
            Link(hoster="mediafire", url="https://example.com/2", quality=Quality.FHD),
        ]
        ep = Episode(number=1, links=links)
        best = ep.best_link
        self.assertEqual(best.hoster, "mediafire")

    def test_best_link_none_when_empty(self):
        ep = Episode(number=1, links=[])
        self.assertIsNone(ep.best_link)


class TestAnime(unittest.TestCase):
    def test_episode_count(self):
        anime = Anime(name="Test", slug="test", episodes=[
            Episode(number=1), Episode(number=2), Episode(number=3),
        ])
        self.assertEqual(anime.episode_count, 3)

    def test_episode_count_empty(self):
        anime = Anime(name="Test", slug="test")
        self.assertEqual(anime.episode_count, 0)


class TestSearchResult(unittest.TestCase):
    def test_creation(self):
        r = SearchResult(name="One Piece", url="https://example.com/anime/one-piece")
        self.assertEqual(r.name, "One Piece")


class TestDownloadResult(unittest.TestCase):
    def test_size_mb(self):
        r = DownloadResult(
            episode_number=1,
            status=DownloadStatus.COMPLETED,
            size_bytes=1024 * 1024 * 100,  # 100 MB
        )
        self.assertAlmostEqual(r.size_mb, 100.0, places=1)

    def test_default_values(self):
        r = DownloadResult(episode_number=1, status=DownloadStatus.PENDING)
        self.assertEqual(r.filepath, "")
        self.assertEqual(r.size_bytes, 0)
        self.assertEqual(r.error, "")


if __name__ == "__main__":
    unittest.main()
