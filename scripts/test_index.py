#!/usr/bin/env python3
"""Fast offline regression tests for GitHub Explorer index helpers."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_index", ROOT / "scripts" / "build_index.py")
INDEX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INDEX)
CATEGORIES = json.loads((ROOT / "config" / "categories.json").read_text(encoding="utf-8"))

class IndexHelpersTest(unittest.TestCase):
    def test_https_url_validation(self):
        self.assertTrue(INDEX.valid_url("https://example.com"))
        self.assertFalse(INDEX.valid_url("http://example.com"))
        self.assertFalse(INDEX.valid_url("javascript:alert(1)"))
        self.assertFalse(INDEX.valid_url(None))

    def test_date_parser(self):
        self.assertIsNotNone(INDEX.parse_date("2026-10-19T10:08:28Z"))
        self.assertIsNone(INDEX.parse_date("not-a-date"))

    def test_category_classification(self):
        repo = {"name": "sample-ai-tool", "description": "A machine learning toolkit", "topics": ["ai", "machine-learning"], "language": "Python", "stargazers_count": 20}
        categories = INDEX.categories_for(repo, CATEGORIES)
        self.assertIn("Artificial Intelligence and Machine Learning", categories)
        self.assertIn("Open-Source Projects", categories)

    def test_android_game_signals_are_searchable(self):
        repo = {"name": "sample-mobile-game", "description": "Android game project", "topics": ["android-game", "mobile-game"], "language": "Kotlin", "stargazers_count": 2}
        categories = INDEX.categories_for(repo, CATEGORIES)
        self.assertIn("Mobile Applications", categories)

    def test_usefulness_is_bounded(self):
        repo = {"pushed_at": "2026-10-19T10:08:28Z", "stargazers_count": 1000, "forks_count": 100}
        score = INDEX.usefulness(repo, "2026-10-01T00:00:00Z", True)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

if __name__ == "__main__":
    unittest.main(verbosity=2)
