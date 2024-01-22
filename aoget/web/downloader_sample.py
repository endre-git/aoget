import logging
from pathlib import Path
from downloader import download_file, validate_file


class ConsoleProgressObserver:
    """Observer for download progress"""

    def on_update_progress(self, written, total):
        """Update download progress"""
        print(f"{written}/{total} bytes written")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s :: %(name)s :: %(asctime)s :: %(message)s",
    handlers=[logging.StreamHandler()],
)

"""
download_file('https://archive.org/download/wiiushopeu/000500001010fb00',
              'c:/dev/download/next.zip',
              progress_observer=ConsoleProgressObserver())
              """

expected_hash = "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
file = Path("test")
with file.open("wb") as f:
    f.write(b"test_data")
validate_file("test", expected_hash)
