"""Regression tests for Toonstream Movie and Series path handling fix."""

import unittest
from unittest.mock import MagicMock
from donghua.toonstream.scraper import ToonstreamScraper
from donghua.toonstream.models import ToonstreamDetail


class TestToonstreamRegression(unittest.TestCase):
    """Test suite verifying Toonstream URL resolution for movies and series."""

    def setUp(self):
        self.mock_http = MagicMock()
        self.mock_http.base_url = "https://toonstream.vip"
        self.scraper = ToonstreamScraper(http_client=self.mock_http)

    def _sample_detail_html(self, title="Test Title", is_series=True):
        return f"""
        <html><body>
        <header class="entry-header"><h1>{title}</h1></header>
        <div class="description"><p>Synopsis here</p></div>
        {"<div class='season-swiper-wrapper'><a data-url='/season-1'>Season 1</a></div>" if is_series else "<div class='play-box-wrapper'></div>"}
        </body></html>
        """

    def test_explicit_movie_path_with_leading_slash(self):
        mock_resp = MagicMock(status_code=200, text=self._sample_detail_html("Avatar Movie", is_series=False))
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_detail("/movies/avatar-aang-the-last-airbender", include_episodes=False)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Avatar Movie")
        self.assertEqual(detail.media_type, "movies")

        # Verify correct URL without /series/ prefix
        args, kwargs = self.mock_http.get.call_args
        self.assertEqual(args[0], "https://toonstream.vip/movies/avatar-aang-the-last-airbender")

    def test_explicit_series_path_with_leading_slash(self):
        mock_resp = MagicMock(status_code=200, text=self._sample_detail_html("Ben 10", is_series=True))
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_detail("/series/ben-10-alien-force", include_episodes=False)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Ben 10")
        self.assertEqual(detail.media_type, "series")

        args, kwargs = self.mock_http.get.call_args
        self.assertEqual(args[0], "https://toonstream.vip/series/ben-10-alien-force")

    def test_movie_path_without_leading_slash_prevents_duplicate_segments(self):
        mock_resp = MagicMock(status_code=200, text=self._sample_detail_html("Avatar Movie", is_series=False))
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_detail("movies/avatar-aang-the-last-airbender", include_episodes=False)
        self.assertIsNotNone(detail)

        args, kwargs = self.mock_http.get.call_args
        self.assertEqual(args[0], "https://toonstream.vip/movies/avatar-aang-the-last-airbender")
        self.assertNotIn("/series/movies/", args[0])

    def test_bare_movie_slug_falls_back_when_series_returns_error(self):
        # 1. /series/ returns RuntimeError (e.g. HTTP 500)
        # 2. /movies/ returns 200 OK
        series_error = RuntimeError("Failed to fetch https://toonstream.vip/series/avatar-movie (HTTP 500)")
        movie_ok = MagicMock(status_code=200, text=self._sample_detail_html("Avatar Movie", is_series=False))

        self.mock_http.get.side_effect = [series_error, movie_ok]
        self.scraper.get_stream_servers = MagicMock(return_value=[])

        detail = self.scraper.get_detail("avatar-movie", include_episodes=False)
        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Avatar Movie")
        self.assertEqual(detail.media_type, "movies")

        # Verify two attempts: first /series/, then /movies/
        call_urls = [c[0][0] for c in self.mock_http.get.call_args_list]
        self.assertEqual(call_urls, [
            "https://toonstream.vip/series/avatar-movie",
            "https://toonstream.vip/movies/avatar-movie"
        ])

    def test_bare_slug_with_explicit_media_type_movies(self):
        mock_resp = MagicMock(status_code=200, text=self._sample_detail_html("Avatar Movie", is_series=False))
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_detail("avatar-movie", media_type="movies", include_episodes=False)
        self.assertIsNotNone(detail)

        args, kwargs = self.mock_http.get.call_args
        self.assertEqual(args[0], "https://toonstream.vip/movies/avatar-movie")

    def test_bare_series_slug_succeeds_on_first_attempt(self):
        mock_resp = MagicMock(status_code=200, text=self._sample_detail_html("Ben 10", is_series=True))
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_detail("ben-10-alien-force", include_episodes=False)
        self.assertIsNotNone(detail)

        # Only one request to /series/
        self.assertEqual(self.mock_http.get.call_count, 1)
        args, kwargs = self.mock_http.get.call_args
        self.assertEqual(args[0], "https://toonstream.vip/series/ben-10-alien-force")

    def test_empty_slug_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.scraper.get_detail("")
        with self.assertRaises(ValueError):
            self.scraper.get_detail("   ")

    def test_unknown_slug_fails_gracefully(self):
        # Both /series/ and /movies/ fail
        self.mock_http.get.side_effect = RuntimeError("Failed to fetch (HTTP 404)")
        with self.assertRaises(RuntimeError):
            self.scraper.get_detail("completely-unknown-slug-xyz", include_episodes=False)

    def test_connection_error_does_not_trigger_redundant_movie_fallback(self):
        self.mock_http.get.side_effect = RuntimeError("Connection reset by peer")
        with self.assertRaises(RuntimeError):
            self.scraper.get_detail("any-slug", include_episodes=False)
        # Verify it did not attempt a second fallback request
        self.assertEqual(self.mock_http.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
