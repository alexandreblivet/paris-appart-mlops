"""Download geo-dvf yearly files for Paris (département 75)."""

import argparse
import gzip
import logging
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/75.csv.gz"
DEFAULT_YEARS = [2020, 2021, 2022, 2023, 2024]
OUTPUT_DIR = Path("data/raw/dvf")


def download_year(year: int, output_dir: Path, force: bool = False) -> Path:
    """Download a single year's geo-dvf file for Paris."""
    output_path = output_dir / f"dvf_{year}_75.csv.gz"

    if output_path.exists() and not force:
        logger.info("Skipping %d — %s already exists", year, output_path)
        return output_path

    url = BASE_URL.format(year=year)
    logger.info("Downloading %s ...", url)

    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        output_path.write_bytes(response.read())

    # Verify gzip integrity
    try:
        with gzip.open(output_path, "rt") as f:
            f.readline()
    except Exception:
        output_path.unlink()
        raise ValueError(f"Corrupt gzip file for year {year}")

    size_kb = output_path.stat().st_size / 1024
    logger.info("Saved %s (%.0f KB)", output_path, size_kb)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Download geo-dvf data for Paris")
    parser.add_argument(
        "--years", nargs="+", type=int, default=DEFAULT_YEARS, help="Years to download"
    )
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for year in args.years:
        try:
            download_year(year, OUTPUT_DIR, force=args.force)
        except httpx.HTTPStatusError as e:
            logger.error("Failed to download %d: %s", year, e)
        except ValueError as e:
            logger.error("%s", e)


if __name__ == "__main__":
    main()
