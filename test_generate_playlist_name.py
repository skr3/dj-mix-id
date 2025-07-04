import unittest
from datetime import datetime
from djmix_shazamio import generate_playlist_name

class test_generate_playlist_name(unittest.TestCase):
    def test_generate_playlist_name(self):
        mix_date = datetime.strptime("2024-12-31", "%Y-%m-%d")
        mix_title = "New Year Special"
        expected = "241231-New Year Special"
        result = generate_playlist_name(mix_date, mix_title)
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()