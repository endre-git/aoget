import unittest
from unittest.mock import MagicMock
from aoget.web.background_resolver import BackgroundResolver, ResolverMonitor
from aoget.model.file_model import FileModel


class TestBackgroundResolver(unittest.TestCase):

    def test_resolve_file_sizes(self):
        # Mock the resolve_remote_file_size function
        resolve_remote_file_size_mock = MagicMock(return_value=1024)

        # Patch the resolve_remote_file_size in the context of this test
        with unittest.mock.patch('aoget.web.downloader.resolve_remote_file_size',
                                 resolve_remote_file_size_mock):
            # Create a mock ResolverMonitor
            resolver_monitor_mock = MagicMock(spec=ResolverMonitor)

            # Create a BackgroundResolver instance
            resolver = BackgroundResolver()

            # Mock filemodels with URLs
            filemodels = [FileModel(None, 'http://example.com/file1'),
                          FileModel(None, 'http://example.com/file2')]

            # Run the method under test
            resolver.resolve_file_sizes("test-job", filemodels, resolver_monitor_mock)

            # Wait for thread to complete (simple way - better to use more robust synchronization)
            import time
            time.sleep(0.5)

            # Check if resolve_remote_file_size was called for each filemodel
            self.assertEqual(resolve_remote_file_size_mock.call_count, len(filemodels))

            # Check if on_resolved_file_size was called with the right arguments
            for filemodel in filemodels:
                resolver_monitor_mock.on_resolved_file_size.assert_any_call(filemodel.url, 1024)


if __name__ == '__main__':
    unittest.main()
