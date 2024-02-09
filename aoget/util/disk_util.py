import os


def get_local_file_size(file_path: str) -> int:
    """Get the size of a local file.
    :param file_path: The path to the file
    :return: The size of the file in bytes"""
    if not os.path.exists(file_path):
        return -1
    return os.path.getsize(file_path)