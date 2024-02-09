import tempfile
from aoget.util.disk_util import get_local_file_size


def test_get_local_file_size_existing_file():
    # Create a temporary file
    with tempfile.NamedTemporaryFile() as tmp_file:
        # Write some data to the file
        tmp_file.write(b'1234567890')
        tmp_file.flush()

        # Check the size of the file
        assert get_local_file_size(tmp_file.name) == 10


def test_get_local_file_size_non_existing_file():
    # Generate a path for a non-existing file
    non_existing_file_path = tempfile.mktemp()

    # Check that the function returns -1 for a non-existing file
    assert get_local_file_size(non_existing_file_path) == -1
