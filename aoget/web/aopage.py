from collections import defaultdict
import urllib.parse


class AoPage:
    """Represents an archive.org page, as a collection of links do downloadable files."""

    files_by_extension = defaultdict(list)
    extension_counts = defaultdict(lambda: 0)

    def add_file_by_extension(self, extension, url):
        self.files_by_extension[extension].append(url)
        self.extension_counts[extension] += 1

    def get_sorted_extensions(self):
        sorted_extensions = sorted(self.files_by_extension.keys())
        return sorted_extensions

    def get_sorted_filenames_by_extension(self, extension):
        if extension not in self.files_by_extension:
            return []
        sorted_filenames = sorted(self.files_by_extension[extension])
        sorted_stripped_filenames = list(
            map(lambda url: url.split("/")[-1], sorted_filenames)
        )
        return list(
            map(
                lambda filename: urllib.parse.unquote(filename),
                sorted_stripped_filenames,
            )
        )
