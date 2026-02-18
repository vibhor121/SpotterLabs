"""
Management command: download_city_data

Downloads a public US cities CSV (city, state, lat, lon) and saves it to
server/data/us_cities.csv, which fuel_data.py uses to resolve city/state
pairs to lat/lon coordinates.

Source: github.com/kelvins/US-Cities-Database (MIT licensed)

Usage:
    python manage.py download_city_data
"""

import os
import urllib.request

from django.core.management.base import BaseCommand

_CSV_URL = (
    "https://raw.githubusercontent.com/kelvins/US-Cities-Database"
    "/main/csv/us_cities.csv"
)

# Destination: server/data/us_cities.csv
_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
)
_DEST_PATH = os.path.join(_DATA_DIR, "us_cities.csv")


class Command(BaseCommand):
    help = "Download US cities CSV used for city→lat/lon lookup in fuel data."

    def handle(self, *args, **options):
        os.makedirs(_DATA_DIR, exist_ok=True)

        self.stdout.write(f"Downloading US cities data …")
        try:
            with urllib.request.urlopen(_CSV_URL, timeout=60) as resp:
                raw = resp.read()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Download failed: {exc}"))
            raise SystemExit(1)

        with open(_DEST_PATH, "wb") as f:
            f.write(raw)

        line_count = raw.count(b"\n")
        self.stdout.write(
            self.style.SUCCESS(
                f"Saved {len(raw):,} bytes ({line_count:,} cities) to {_DEST_PATH}"
            )
        )
