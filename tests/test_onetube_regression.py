"""Regression tests for OneTube Movie/TV ID collision fix."""

import unittest
from unittest.mock import MagicMock
from movies.onetube.scraper import OneTubeScraper
from movies.onetube.models import MovieDetail


class TestOneTubeRegression(unittest.TestCase):
    """Test suite verifying OneTube Movie vs TV disambiguation, caching, and error handling."""

    def setUp(self):
        self.mock_http = MagicMock()
        self.mock_storage = MagicMock()
        self.mock_storage.get_movie.return_value = None
        self.scraper = OneTubeScraper(http_client=self.mock_http, storage=self.mock_storage)

    def test_breaking_bad_tv_id_1396_routes_to_tv(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "name": "Breaking Bad",
            "original_name": "Breaking Bad",
            "media_type": "tv",
            "first_air_date": "2008-01-20",
            "number_of_seasons": 5,
            "number_of_episodes": 62,
            "vote_average": 9.0,
            "vote_count": 18000,
            "genres": [{"name": "Drama"}, {"name": "Crime"}],
            "overview": "Walter White enters drug world.",
            "tagline": "Change the equation.",
        }
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_movie_detail("1396", media_type="tv")

        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Breaking Bad")
        self.assertEqual(detail.media_type, "TV Series")
        self.assertEqual(detail.release_year, "2008")
        self.assertIn("5 Seasons", detail.duration)
        self.assertIn("/watch/tv/1396", detail.watch_url)

        # Verify that ?type=tv was sent to API
        args, kwargs = self.mock_http.get.call_args_list[0]
        self.assertIn("/api/details/1396?type=tv", args[0])

    def test_game_of_thrones_tv_id_1399(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "name": "Game of Thrones",
            "first_air_date": "2011-04-17",
            "number_of_seasons": 8,
            "number_of_episodes": 73,
            "vote_average": 8.4,
            "genres": [{"name": "Sci-Fi & Fantasy"}, {"name": "Drama"}],
            "overview": "Seven noble families fight for control of the mythical land of Westeros.",
        }
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_movie_detail("https://www.1tube.org/watch/tv/1399")
        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Game of Thrones")
        self.assertEqual(detail.media_type, "TV Series")
        self.assertEqual(detail.release_year, "2011")

    def test_valid_movie_id(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Avengers: Endgame",
            "media_type": "movie",
            "release_date": "2019-04-24",
            "runtime": 181,
            "vote_average": 8.3,
            "genres": [{"name": "Action"}, {"name": "Sci-Fi"}],
            "overview": "After the devastating events of Avengers: Infinity War...",
        }
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_movie_detail("299534", media_type="movie")
        self.assertIsNotNone(detail)
        self.assertEqual(detail.title, "Avengers: Endgame")
        self.assertEqual(detail.media_type, "Movie")
        self.assertEqual(detail.release_year, "2019")
        self.assertEqual(detail.duration, "181 min")

        # Verify movie endpoint was called without ?type=tv
        args, kwargs = self.mock_http.get.call_args_list[0]
        self.assertEqual(args[0], "https://www.1tube.org/api/details/299534")

    def test_same_numeric_id_differentiates_movie_and_tv(self):
        movie_resp = MagicMock()
        movie_resp.status_code = 200
        movie_resp.json.return_value = {
            "title": "Mirror",
            "release_date": "1975-03-07",
            "runtime": 107,
        }
        tv_resp = MagicMock()
        tv_resp.status_code = 200
        tv_resp.json.return_value = {
            "name": "Breaking Bad",
            "first_air_date": "2008-01-20",
            "number_of_seasons": 5,
        }

        self.mock_http.get.side_effect = [movie_resp, MagicMock(status_code=404), tv_resp, MagicMock(status_code=404)]

        movie_detail = self.scraper.get_movie_detail("1396", media_type="movie")
        self.assertEqual(movie_detail.title, "Mirror")
        self.assertEqual(movie_detail.media_type, "Movie")

        tv_detail = self.scraper.get_movie_detail("1396", media_type="tv")
        self.assertEqual(tv_detail.title, "Breaking Bad")
        self.assertEqual(tv_detail.media_type, "TV Series")

    def test_cache_keys_include_media_type_separation(self):
        movie_resp = MagicMock(status_code=200)
        movie_resp.json.return_value = {"title": "Mirror Movie", "runtime": 100}
        self.mock_http.get.return_value = movie_resp

        self.scraper.get_movie_detail("1396", media_type="movie", use_cache=True)
        # Check that storage was queried with "movie:1396"
        self.mock_storage.get_movie.assert_called_with("movie:1396")
        self.mock_storage.set_movie.assert_called()
        self.assertEqual(self.mock_storage.set_movie.call_args[0][0], "movie:1396")

        # Now fetch TV
        tv_resp = MagicMock(status_code=200)
        tv_resp.json.return_value = {"name": "Breaking Bad TV", "number_of_seasons": 5}
        self.mock_http.get.return_value = tv_resp

        self.scraper.get_movie_detail("1396", media_type="tv", use_cache=True)
        self.mock_storage.get_movie.assert_called_with("tv:1396")
        self.assertEqual(self.mock_storage.set_movie.call_args[0][0], "tv:1396")

    def test_ambiguous_numeric_id_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.scraper.get_movie_detail("1396")
        self.assertIn("Ambiguous TMDB ID '1396'", str(ctx.exception))
        self.assertIn("media_type='movie' or media_type='tv'", str(ctx.exception))

    def test_unsupported_media_type_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.scraper.get_movie_detail("1396", media_type="podcast")
        self.assertIn("Unsupported media_type 'podcast'", str(ctx.exception))

    def test_unknown_id_returns_none(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_movie_detail("999999999", media_type="movie")
        self.assertIsNone(detail)

    def test_provider_http_error_returns_none(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        self.mock_http.get.return_value = mock_resp

        detail = self.scraper.get_movie_detail("1396", media_type="tv")
        self.assertIsNone(detail)

    def test_get_tv_season(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "season_number": 1,
            "episodes": [{"episode_number": 1, "name": "Pilot"}],
        }
        self.mock_http.get.return_value = mock_resp

        season_data = self.scraper.get_tv_season("1396", season_number=1)
        self.assertIsNotNone(season_data)
        self.assertEqual(season_data["season_number"], 1)
        self.assertEqual(season_data["episodes"][0]["name"], "Pilot")
        self.assertIn("/api/tv/1396/season/1", self.mock_http.get.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
