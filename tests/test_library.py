"""Tests for witdl.library — state tracking and management."""

import os
import tempfile
from pathlib import Path
import unittest

from witdl.library import Library, EpisodeState
from witdl.models import DownloadResult, DownloadStatus


class TestLibrary(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.state_file = self.test_dir / "state.json"

    def _make_library(self):
        import witdl.library as lib_mod
        original = lib_mod.STATE_FILE
        lib_mod.STATE_FILE = self.state_file
        try:
            lib = Library()
            yield lib
        finally:
            lib_mod.STATE_FILE = original

    def test_get_or_create_anime(self):
        lib = next(self._make_library())
        anime = lib.get_or_create_anime("Test Anime", "test-anime")
        self.assertEqual(anime.name, "Test Anime")
        self.assertEqual(anime.slug, "test-anime")

    def test_get_or_create_returns_existing(self):
        lib = next(self._make_library())
        anime1 = lib.get_or_create_anime("Test", "test")
        anime2 = lib.get_or_create_anime("Test 2", "test")
        self.assertEqual(anime1, anime2)
        self.assertEqual(anime2.name, "Test")

    def test_is_downloaded_false(self):
        lib = next(self._make_library())
        self.assertFalse(lib.is_downloaded("test", 1))

    def test_update_episode_completed(self):
        lib = next(self._make_library())
        lib.get_or_create_anime("Test", "test")

        result = DownloadResult(
            episode_number=1,
            status=DownloadStatus.COMPLETED,
            filepath="/tmp/test.mp4",
            size_bytes=100 * 1024 * 1024,
        )
        lib.update_episode("test", result)

        anime = lib.get_anime("test")
        self.assertIn(1, anime.episodes)
        self.assertEqual(anime.episodes[1].status, "completed")

    def test_update_episode_failed_increments_attempts(self):
        lib = next(self._make_library())
        lib.get_or_create_anime("Test", "test")

        result = DownloadResult(episode_number=1, status=DownloadStatus.FAILED, error="timeout")
        lib.update_episode("test", result)
        lib.update_episode("test", result)

        anime = lib.get_anime("test")
        self.assertEqual(anime.episodes[1].attempts, 2)

    def test_mark_skipped(self):
        lib = next(self._make_library())
        lib.get_or_create_anime("Test", "test")
        # Create a real temp file so is_downloaded finds it
        tmp = self.test_dir / "ep1.mp4"
        tmp.write_bytes(b"x" * 200 * 1024 * 1024)
        lib.mark_skipped("test", 1, str(tmp), 200 * 1024 * 1024)
        self.assertTrue(lib.is_downloaded("test", 1))

    def test_get_downloaded_episodes(self):
        lib = next(self._make_library())
        lib.get_or_create_anime("Test", "test")
        lib.mark_skipped("test", 1, "/tmp/ep1.mp4", 100)
        lib.mark_skipped("test", 3, "/tmp/ep3.mp4", 100)

        downloaded = lib.get_downloaded_episodes("test")
        self.assertEqual(downloaded, [1, 3])

    def test_get_missing_episodes(self):
        lib = next(self._make_library())
        lib.get_or_create_anime("Test", "test")
        lib.mark_skipped("test", 1, "/tmp/ep1.mp4", 100)
        lib.mark_skipped("test", 3, "/tmp/ep3.mp4", 100)

        missing = lib.get_missing_episodes("test", 5)
        self.assertEqual(missing, [2, 4, 5])

    def test_list_all(self):
        lib = next(self._make_library())
        lib.get_or_create_anime("Anime A", "a")
        lib.get_or_create_anime("Anime B", "b")
        lib.mark_skipped("a", 1, "/tmp/a1.mp4", 100)

        items = lib.list_all()
        self.assertEqual(len(items), 2)
        self.assertEqual(items["a"]["downloaded"], 1)
        self.assertEqual(items["b"]["downloaded"], 0)

    def test_clean_failed(self):
        lib = next(self._make_library())
        lib.get_or_create_anime("Test", "test")
        lib.update_episode("test", DownloadResult(1, DownloadStatus.COMPLETED, filepath="/tmp/x"))
        lib.update_episode("test", DownloadResult(2, DownloadStatus.FAILED, error="err"))
        lib.update_episode("test", DownloadResult(3, DownloadStatus.FAILED, error="err"))

        lib.clean_failed()

        anime = lib.get_anime("test")
        self.assertIn(1, anime.episodes)
        self.assertNotIn(2, anime.episodes)
        self.assertNotIn(3, anime.episodes)

    def test_persistence(self):
        import witdl.library as lib_mod
        original = lib_mod.STATE_FILE
        lib_mod.STATE_FILE = self.state_file

        try:
            lib1 = Library()
            lib1.get_or_create_anime("Test", "test")
            # Use a real file so is_downloaded works
            tmp = self.test_dir / "ep1.mp4"
            tmp.write_bytes(b"x" * 100)
            lib1.mark_skipped("test", 1, str(tmp), 100)
            lib1.save()

            lib2 = Library()
            self.assertTrue(lib2.is_downloaded("test", 1))
        finally:
            lib_mod.STATE_FILE = original


class TestEpisodeState(unittest.TestCase):
    def test_defaults(self):
        ep = EpisodeState(number=5)
        self.assertEqual(ep.status, "pending")
        self.assertEqual(ep.filepath, "")
        self.assertEqual(ep.attempts, 0)


if __name__ == "__main__":
    unittest.main()
