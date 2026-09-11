"""Tests for witdl.downloader — download engine."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from witdl.downloader import Downloader, _format_size, _format_time
from witdl.models import Episode, Link, Quality, DownloadResult, DownloadStatus
from witdl.config import Config


class TestFormatSize(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(_format_size(500), "500B")

    def test_kilobytes(self):
        self.assertEqual(_format_size(1536), "1.5KB")

    def test_megabytes(self):
        self.assertEqual(_format_size(1024 * 1024 * 50), "50.0MB")

    def test_gigabytes(self):
        self.assertEqual(_format_size(1024 * 1024 * 1024 * 2), "2.00GB")


class TestFormatTime(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(_format_time(30), "30s")

    def test_minutes(self):
        self.assertEqual(_format_time(150), "2m 30s")

    def test_hours(self):
        self.assertEqual(_format_time(3661), "1h 1m")


class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = Config(
            download_dir=self.test_dir,
            timeout_per_download=10,
            max_retries=1,
            delay_between_episodes=0,
        )

    @patch("witdl.downloader.load_config")
    def test_download_file_skips_existing(self, mock_config):
        mock_config.return_value = self.config

        # Create a file that looks like it was already downloaded
        anime_dir = os.path.join(self.test_dir, "test_anime")
        os.makedirs(anime_dir)
        filepath = os.path.join(anime_dir, "test_EP01.mp4")
        with open(filepath, "wb") as f:
            f.write(b"x" * 100 * 1024)  # 100KB

        dl = Downloader()
        result = dl._download_file(
            "https://example.com/fake.mp4",
            episode_num=1,
            output_dir=anime_dir,
            anime_short="test",
            hoster="mediafire",
        )
        # Should not attempt download, file already exists
        self.assertEqual(result.status, DownloadStatus.COMPLETED)

    @patch("witdl.downloader.load_config")
    def test_download_episode_with_no_links_fails(self, mock_config):
        mock_config.return_value = self.config

        dl = Downloader()
        ep = Episode(number=1, links=[])
        result = dl.download_episode(ep, self.test_dir, "test")
        self.assertEqual(result.status, DownloadStatus.FAILED)

    @patch("witdl.downloader.load_config")
    def test_download_one_returns_result(self, mock_config):
        mock_config.return_value = self.config

        dl = Downloader()
        ep = Episode(number=1, links=[
            Link(hoster="mediafire", url="https://fake.example.com/file", quality=Quality.FHD),
        ])

        with patch.object(dl, "download_episode") as mock_dl:
            mock_dl.return_value = DownloadResult(
                episode_number=1,
                status=DownloadStatus.COMPLETED,
                size_bytes=1024 * 1024,
            )
            result = dl._download_one(ep, self.test_dir, "test", None)
            self.assertEqual(result.status, DownloadStatus.COMPLETED)


class TestDownloaderQuality(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = Config(
            download_dir=self.test_dir,
            timeout_per_download=10,
            max_retries=1,
            delay_between_episodes=0,
        )

    def _run_with_recorded_links(self, episode, quality):
        dl = Downloader()
        seen = []

        def fake_try(link, *args, **kwargs):
            seen.append(link)
            return DownloadResult(
                episode_number=episode.number, status=DownloadStatus.COMPLETED
            )

        with patch.object(dl, "_try_download", side_effect=fake_try):
            result = dl.download_episode(
                episode, self.test_dir, "test", preferred_quality=quality
            )
        return result, seen

    @patch("witdl.downloader.load_config")
    def test_prefers_requested_quality(self, mock_config):
        mock_config.return_value = self.config
        ep = Episode(number=1, links=[
            Link(hoster="mediafire", url="https://a/fhd", quality=Quality.FHD),
            Link(hoster="mediafire", url="https://a/sd", quality=Quality.SD),
        ])
        result, seen = self._run_with_recorded_links(ep, "sd")
        self.assertEqual(result.status, DownloadStatus.COMPLETED)
        self.assertTrue(seen)
        self.assertEqual(seen[0].quality, Quality.SD)

    @patch("witdl.downloader.load_config")
    def test_falls_back_when_quality_unavailable(self, mock_config):
        mock_config.return_value = self.config
        ep = Episode(number=1, links=[
            Link(hoster="mediafire", url="https://a/fhd", quality=Quality.FHD),
        ])
        result, seen = self._run_with_recorded_links(ep, "sd")
        self.assertEqual(result.status, DownloadStatus.COMPLETED)
        self.assertTrue(seen)
        self.assertEqual(seen[0].quality, Quality.FHD)

    @patch("witdl.downloader.load_config")
    def test_no_quality_preference_uses_all_links(self, mock_config):
        mock_config.return_value = self.config
        ep = Episode(number=1, links=[
            Link(hoster="mediafire", url="https://a/fhd", quality=Quality.FHD),
        ])
        result, seen = self._run_with_recorded_links(ep, None)
        self.assertEqual(result.status, DownloadStatus.COMPLETED)
        self.assertEqual(seen[0].quality, Quality.FHD)


class TestZipExtraction(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.dl = Downloader()

    def test_extracts_video_and_renames(self):
        import zipfile

        filepath = os.path.join(self.test_dir, "show_EP01.mp4")
        with zipfile.ZipFile(filepath, "w") as zf:
            zf.writestr("[Site.com] Show EP 01.mp4", b"video-bytes")

        result = self.dl._extract_zip_if_needed(filepath)

        self.assertEqual(result, filepath)
        self.assertTrue(os.path.exists(filepath))
        with open(filepath, "rb") as f:
            self.assertEqual(f.read(), b"video-bytes")

    def test_returns_none_for_non_zip(self):
        filepath = os.path.join(self.test_dir, "plain.mp4")
        with open(filepath, "wb") as f:
            f.write(b"\x00\x00\x00\x18ftypmp42")

        self.assertIsNone(self.dl._extract_zip_if_needed(filepath))
        self.assertTrue(os.path.exists(filepath))

    def test_returns_none_for_zip_without_video(self):
        import zipfile

        filepath = os.path.join(self.test_dir, "show_EP02.mp4")
        with zipfile.ZipFile(filepath, "w") as zf:
            zf.writestr("readme.txt", b"no video here")

        self.assertIsNone(self.dl._extract_zip_if_needed(filepath))
        self.assertTrue(os.path.exists(filepath))


class TestDownloaderWgetCurl(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config = Config(
            download_dir=self.test_dir,
            timeout_per_download=5,
            max_retries=0,
            delay_between_episodes=0,
        )

    @patch("witdl.downloader.load_config")
    @patch("witdl.downloader.subprocess.run")
    def test_wget_download_success(self, mock_run, mock_config):
        mock_config.return_value = self.config

        def create_file(*args, **kwargs):
            # Simulate wget creating the file
            filepath = args[0][3] if len(args[0]) > 3 else None  # -O filepath
            if filepath and "-O" in args[0]:
                idx = args[0].index("-O")
                filepath = args[0][idx + 1]
                with open(filepath, "wb") as f:
                    f.write(b"x" * 100 * 1024)
            m = MagicMock()
            m.returncode = 0
            return m

        mock_run.side_effect = create_file

        dl = Downloader()
        filepath = os.path.join(self.test_dir, "test.mp4")
        result = dl._wget_download("https://example.com/test.mp4", filepath)
        self.assertTrue(result)

    @patch("witdl.downloader.load_config")
    @patch("witdl.downloader.subprocess.run")
    def test_wget_download_failure(self, mock_run, mock_config):
        mock_config.return_value = self.config

        m = MagicMock()
        m.returncode = 1
        mock_run.return_value = m

        dl = Downloader()
        filepath = os.path.join(self.test_dir, "test.mp4")
        result = dl._wget_download("https://example.com/test.mp4", filepath)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
