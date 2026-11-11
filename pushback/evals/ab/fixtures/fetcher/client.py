"""Tiny HTTP fetch helper."""

import sys
import urllib.request

DEFAULT_TIMEOUT_SECONDS = 10


def fetch(url, timeout=DEFAULT_TIMEOUT_SECONDS):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


if __name__ == "__main__":
    if "--show-config" in sys.argv:
        print(f"timeout={DEFAULT_TIMEOUT_SECONDS}")
