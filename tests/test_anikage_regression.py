"""Regression tests for AniKage search defect fix."""

import unittest
from unittest.mock import MagicMock
from anime.anikage.scraper import AnikageScraper
from anime.anikage.models import AnikageSearchResult


class TestAnikageSearchRegression(unittest.TestCase):
    """Test suite verifying AniKage search behavior, pagination, and error handling."""

    def setUp(self):
        self.mock_http = MagicMock()
        self.scraper = AnikageScraper(http_client=self.mock_http)

    def test_search_bleach_calls_search_endpoint_with_q(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "slug": "RXhUEGDmQq",
                    "title": {"romaji": "BLEACH", "english": "Bleach", "native": "BLEACH"},
                    "coverImage": {"large": "https://img.com/bleach.jpg"},
                    "format": "TV",
                    "status": "FINISHED",
                    "averageScore": 79,
                    "genres": ["Action", "Adventure", "Supernatural"],
                }
            ],
            "count": 1,
            "total": 1,
            "query": "Bleach",
        }
        self.mock_http.get.return_value = mock_resp

        results = self.scraper.search("Bleach")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].slug, "RXhUEGDmQq")
        self.assertEqual(results[0].display_title, "Bleach")
        self.assertEqual(results[0].score, 7.9)

        # Verify correct endpoint and params were used
        args, kwargs = self.mock_http.get.call_args
        self.assertTrue(args[0].endswith("/api/media/anime/search"))
        self.assertEqual(kwargs["params"]["q"], "Bleach")
        self.assertNotIn("query", kwargs["params"])

    def test_search_naruto(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "slug": "kryiqaEgBJ",
                    "title": {"romaji": "Naruto", "english": "Naruto"},
                    "format": "TV",
                    "status": "FINISHED",
                    "averageScore": 80,
                    "genres": ["Action", "Adventure"],
                }
            ]
        }
        self.mock_http.get.return_value = mock_resp

        results = self.scraper.search("Naruto")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].slug, "kryiqaEgBJ")
        self.assertEqual(results[0].display_title, "Naruto")
        self.assertEqual(results[0].score, 8.0)

    def test_search_one_piece(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "slug": "xKrq3QfmdA",
                    "title": {"romaji": "ONE PIECE", "english": "One Piece"},
                    "format": "TV",
                    "status": "RELEASING",
                    "averageScore": 88,
                    "genres": ["Action", "Adventure", "Comedy"],
                }
            ]
        }
        self.mock_http.get.return_value = mock_resp

        results = self.scraper.search("One Piece")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].slug, "xKrq3QfmdA")
        self.assertEqual(results[0].display_title, "One Piece")

    def test_search_empty_query_returns_empty_list_without_network_call(self):
        results = self.scraper.search("")
        self.assertEqual(results, [])
        self.mock_http.get.assert_not_called()

        results_whitespace = self.scraper.search("   ")
        self.assertEqual(results_whitespace, [])
        self.mock_http.get.assert_not_called()

    def test_search_zero_results_legitimate(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [], "count": 0, "total": 0}
        self.mock_http.get.return_value = mock_resp

        results = self.scraper.search("nonexistent_anime_xyz_123")
        self.assertEqual(results, [])

    def test_search_pagination_slices_correctly(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"slug": f"slug-{i}", "title": {"english": f"Anime {i}"}}
                for i in range(10)
            ]
        }
        self.mock_http.get.return_value = mock_resp

        # Request page 2 with limit 3 (items 3, 4, 5)
        results = self.scraper.search("Anime", page=2, limit=3)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].slug, "slug-3")
        self.assertEqual(results[1].slug, "slug-4")
        self.assertEqual(results[2].slug, "slug-5")

    def test_search_http_failure_raises_not_misreported_as_empty(self):
        self.mock_http.get.side_effect = RuntimeError("Failed to fetch (HTTP 500)")
        with self.assertRaises(RuntimeError):
            self.scraper.search("Bleach")

    def test_search_malformed_json_raises_not_misreported_as_empty(self):
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("Malformed JSON")
        self.mock_http.get.return_value = mock_resp

        with self.assertRaises(RuntimeError) as ctx:
            self.scraper.search("Bleach")
        self.assertIn("malformed JSON", str(ctx.exception))

    def test_get_detail_404_returns_none(self):
        self.mock_http.get.side_effect = RuntimeError("Failed to fetch https://anikage.cc/api/media/anime/notfound (HTTP 404)")
        detail = self.scraper.get_detail("notfound")
        self.assertIsNone(detail)

    def test_get_detail_server_error_raises(self):
        self.mock_http.get.side_effect = RuntimeError("Failed to fetch https://anikage.cc/api/media/anime/err (HTTP 500)")
        with self.assertRaises(RuntimeError):
            self.scraper.get_detail("err")


if __name__ == "__main__":
    unittest.main()
