"""Tests for witdl.scraper — link decryption and parsing."""

import base64
import unittest

from witdl.scraper import (
    _xor_decrypt,
    _parse_episode_range,
    extract_download_links,
)
from witdl.models import Quality


class TestXorDecrypt(unittest.TestCase):
    def test_simple_xor(self):
        key = "abc"
        original = "hello"
        encrypted = ""
        for i, ch in enumerate(original):
            encrypted += format(ord(ch) ^ ord(key[i % len(key)]), "02x")
        decrypted = _xor_decrypt(encrypted, key)
        self.assertEqual(decrypted, original)

    def test_empty_string(self):
        self.assertEqual(_xor_decrypt("", "key"), "")

    def test_roundtrip(self):
        key = "secret123"
        original = "https://example.com/video.mp4"
        encrypted = ""
        for i, ch in enumerate(original):
            encrypted += format(ord(ch) ^ ord(key[i % len(key)]), "02x")
        decrypted = _xor_decrypt(encrypted, key)
        self.assertEqual(decrypted, original)


class TestParseEpisodeRange(unittest.TestCase):
    def test_single_episode(self):
        self.assertEqual(_parse_episode_range("5"), [5])

    def test_range(self):
        self.assertEqual(_parse_episode_range("1-5"), [1, 2, 3, 4, 5])

    def test_comma_separated(self):
        self.assertEqual(_parse_episode_range("1,3,5"), [1, 3, 5])

    def test_mixed(self):
        self.assertEqual(_parse_episode_range("1-3,7,10-12"), [1, 2, 3, 7, 10, 11, 12])

    def test_sorted_output(self):
        self.assertEqual(_parse_episode_range("5,1,3"), [1, 3, 5])

    def test_duplicates_removed(self):
        self.assertEqual(_parse_episode_range("1-3,2-4"), [1, 2, 3, 4])

    def test_spaces(self):
        self.assertEqual(_parse_episode_range("1 - 3, 5"), [1, 2, 3, 5])


def _encrypt(text, key):
    """Encrypt text with XOR for testing."""
    return "".join(format(ord(ch) ^ ord(key[i % len(key)]), "02x") for i, ch in enumerate(text))


def _build_html(secret_b64, p_arrays, x_arrays, labels):
    """Build minimal WitAnime HTML for testing.
    
    Each p_array is a list of hex-encoded chunks for one download link.
    Each x_array is the hex-encoded reorder sequence for the corresponding p_array.
    b_count = len(p_arrays) = number of download links.
    """
    download_section = ""
    for i, label in enumerate(labels):
        download_section += f'''
            <a class="btn btn-default download-link"
               data-index="{i}" href="#" rel="nofollow">
                <span class="notice">{label}</span>
            </a>'''

    # Format _p arrays
    p_vars = ""
    for i, p_arr in enumerate(p_arrays):
        chunks = ", ".join(f'"{c}"' for c in p_arr)
        p_vars += f"var _p{i} = [{chunks}];\n"

    # Format _x array
    x_chunks = ", ".join(f'"{x}"' for x in x_arrays)

    return f'''
    <html><body>
        <div class="episode-download-container">{download_section}</div>
    </body>
    <script>
    var _m = {{"r":"{secret_b64}"}};
    {p_vars}
    var _x = [{x_chunks}];
    var _b = {{"l":"{len(p_arrays)}"}};
    </script></html>
    '''


class TestExtractDownloadLinks(unittest.TestCase):
    def test_single_link(self):
        key = "testkey123"
        secret_b64 = base64.b64encode(key.encode()).decode()
        url = "https://example.com/video.mp4"

        html = _build_html(
            secret_b64,
            p_arrays=[[_encrypt(url, key)]],
            x_arrays=[_encrypt("[0]", key)],
            labels=["mediafire"],
        )

        links = extract_download_links(html)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].url, url)
        self.assertEqual(links[0].hoster, "mediafire")

    def test_two_links_unordered(self):
        key = "mysecretkey"
        secret_b64 = base64.b64encode(key.encode()).decode()
        url1 = "https://a.com/first.mp4"
        url2 = "https://b.com/second.mp4"

        # Each _p array has chunks that combine into one URL
        # Here each URL is a single chunk, so no reorder needed
        html = _build_html(
            secret_b64,
            p_arrays=[
                [_encrypt(url1, key)],  # _p0 → link 0
                [_encrypt(url2, key)],  # _p1 → link 1
            ],
            x_arrays=[
                _encrypt("[0]", key),  # seq for _p0
                _encrypt("[0]", key),  # seq for _p1
            ],
            labels=["hexload", "mp4upload"],
        )

        links = extract_download_links(html)
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].hoster, "hexload")
        self.assertEqual(links[0].url, url1)
        self.assertEqual(links[1].hoster, "mp4upload")
        self.assertEqual(links[1].url, url2)

    def test_two_links_with_reorder(self):
        key = "mysecretkey"
        secret_b64 = base64.b64encode(key.encode()).decode()
        url = "https://example.com/video.mp4"

        # URL split into 2 chunks, reordered [1, 0]
        part_a = _encrypt("https://ex", key)
        part_b = _encrypt("ample.com/video.mp4", key)

        html = _build_html(
            secret_b64,
            p_arrays=[
                [part_a, part_b],  # _p0: 2 chunks
            ],
            x_arrays=[
                _encrypt("[0, 1]", key),  # swap order
            ],
            labels=["mediafire"],
        )

        links = extract_download_links(html)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0].url, url)

    def test_empty_html(self):
        links = extract_download_links("<html><body>nothing</body></html>")
        self.assertEqual(links, [])

    def test_quality_sd(self):
        key = "q"
        secret_b64 = base64.b64encode(key.encode()).decode()
        url = "https://example.com/video+sd+file.mp4"

        html = _build_html(
            secret_b64,
            p_arrays=[[_encrypt(url, key)]],
            x_arrays=[_encrypt("[0]", key)],
            labels=["mediafire"],
        )

        links = extract_download_links(html)
        self.assertEqual(links[0].quality, Quality.SD)

    def test_quality_hd(self):
        key = "q"
        secret_b64 = base64.b64encode(key.encode()).decode()
        url = "https://example.com/video+hd+file.mp4"

        html = _build_html(
            secret_b64,
            p_arrays=[[_encrypt(url, key)]],
            x_arrays=[_encrypt("[0]", key)],
            labels=["mediafire"],
        )

        links = extract_download_links(html)
        self.assertEqual(links[0].quality, Quality.HD)

    def test_three_links(self):
        key = "abc"
        secret_b64 = base64.b64encode(key.encode()).decode()
        url1 = "https://a.com/1.mp4"
        url2 = "https://b.com/2.mp4"
        url3 = "https://c.com/3.mp4"

        html = _build_html(
            secret_b64,
            p_arrays=[
                [_encrypt(url1, key)],
                [_encrypt(url2, key)],
                [_encrypt(url3, key)],
            ],
            x_arrays=[
                _encrypt("[0]", key),
                _encrypt("[0]", key),
                _encrypt("[0]", key),
            ],
            labels=["mediafire", "hexload", "mp4upload"],
        )

        links = extract_download_links(html)
        self.assertEqual(len(links), 3)
        self.assertEqual(links[0].url, url1)
        self.assertEqual(links[1].url, url2)
        self.assertEqual(links[2].url, url3)


if __name__ == "__main__":
    unittest.main()
