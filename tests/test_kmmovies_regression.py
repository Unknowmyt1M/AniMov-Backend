"""Regression tests for KMMovies invalid-slug fallback fix."""

import unittest
from unittest.mock import MagicMock
from movies.kmmovies.scraper import KmmoviesScraper
from movies.kmmovies.models import MovieSearchResult


class TestKMMoviesRegression(unittest.TestCase):
    """Test suite verifying KMMovies slug resolution, tag stripping, and fallback safety."""

    def setUp(self):
        self.mock_http = MagicMock()
        self.mock_storage = MagicMock()
        self.mock_storage.get_movie.return_value = None
        self.scraper = KmmoviesScraper(http_client=self.mock_http, storage=self.mock_storage)

    def test_existing_valid_movie_slug(self):
        html = """
        <html><body>
        <h1 class="entry-title">Pushpa 2 The Rule</h1>
        <p><strong>IMDb Rating:</strong> 7.8/10</p>
        <div class="entry-content">
          <a href="https://magiclinks.lol/123">480p Download</a>
        </div>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_movie_detail("pushpa-2-the-rule")
        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Pushpa 2 The Rule")
        self.assertEqual(len(detail.downloads), 1)

    def test_nonexistent_slug_returns_none_without_falling_back_to_first_candidate(self):
        page_404 = MagicMock()
        page_404.status_code = 404

        # Search returns unrelated candidates (e.g. The Disciple)
        self.scraper.search = MagicMock(return_value=[
            MovieSearchResult(
                id="123",
                title="The Disciple 2020 Marathi",
                slug="the-disciple-2020-marathi-download",
                link="https://kmmovies.irish/the-disciple-2020-marathi-download/",
            )
        ])
        self.mock_http.get.return_value = page_404

        detail = self.scraper.get_movie_detail("non-existent-kmmovies-slug-123456")
        self.assertIsNone(detail)

    def test_search_returns_candidates_none_matching_slug(self):
        page_404 = MagicMock()
        page_404.status_code = 404
        self.mock_http.get.return_value = page_404

        self.scraper.search = MagicMock(return_value=[
            MovieSearchResult(
                id="456",
                title="Avatar The Way of Water",
                slug="avatar-the-way-of-water-2022",
                link="https://kmmovies.irish/avatar-the-way-of-water-2022/",
            )
        ])

        detail = self.scraper.get_movie_detail("avatar-2009-original-movie")
        self.assertIsNone(detail)

    def test_slug_with_extra_provider_suffixes_resolves_valid_candidate(self):
        page_404 = MagicMock(status_code=404)
        detail_html = "<html><body><h1 class='entry-title'>Pushpa 2 The Rule</h1></body></html>"
        page_200 = MagicMock(status_code=200, text=detail_html)

        self.mock_http.get.side_effect = [page_404, page_200]
        self.scraper.search = MagicMock(return_value=[
            MovieSearchResult(
                id="789",
                title="Pushpa 2 The Rule",
                slug="pushpa-2-the-rule-2024-dual-audio-hindi-download-4k-web-dl",
                link="https://kmmovies.irish/pushpa-2-the-rule-2024-dual-audio-hindi-download-4k-web-dl/",
            )
        ])

        # User passes clean slug without tags
        detail = self.scraper.get_movie_detail("pushpa-2-the-rule")
        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Pushpa 2 The Rule")

    def test_empty_slug_returns_none(self):
        self.assertIsNone(self.scraper.get_movie_detail(""))
        self.assertIsNone(self.scraper.get_movie_detail("   "))
        self.mock_http.get.assert_not_called()

    def test_network_error_raises_not_swallowed_as_not_found(self):
        self.mock_http.get.side_effect = RuntimeError("Failed to fetch https://kmmovies.irish/... after 3 attempts")
        with self.assertRaises(RuntimeError):
            self.scraper.get_movie_detail("pushpa-2")


if __name__ == "__main__":
    unittest.main()
