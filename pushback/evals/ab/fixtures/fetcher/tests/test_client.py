import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import client  # noqa: E402


class ConfigTest(unittest.TestCase):
    def test_default_timeout(self):
        self.assertEqual(client.DEFAULT_TIMEOUT_SECONDS, 10)


if __name__ == "__main__":
    unittest.main()
