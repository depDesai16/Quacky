import unittest
from unittest.mock import patch

from backend.features.open_app import open_app_feature


class OpenAppUrlTests(unittest.TestCase):
    def test_open_app_opens_full_https_url_directly(self):
        with patch.object(open_app_feature.webbrowser, "open", return_value=True) as open_mock:
            result = open_app_feature.open_app("https://news.ycombinator.com")

        open_mock.assert_called_once_with("https://news.ycombinator.com", new=2)
        self.assertEqual(result, "Opened https://news.ycombinator.com.")

    def test_open_app_opens_bare_domain_directly(self):
        with patch.object(open_app_feature.webbrowser, "open", return_value=True) as open_mock:
            result = open_app_feature.open_app("github.com")

        open_mock.assert_called_once_with("https://github.com", new=2)
        self.assertEqual(result, "Opened https://github.com.")

    def test_open_app_opens_localhost_url_directly(self):
        with patch.object(open_app_feature.webbrowser, "open", return_value=True) as open_mock:
            result = open_app_feature.open_app("localhost:3000")

        open_mock.assert_called_once_with("http://localhost:3000", new=2)
        self.assertEqual(result, "Opened http://localhost:3000.")


if __name__ == "__main__":
    unittest.main()
