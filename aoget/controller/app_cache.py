from typing import Dict, List
from model.dto.file_model_dto import FileModelDTO


class AppCache:
    """Cached state of the application, used to avoid unnecessary database queries.
    Contains a file_dto_cache field which holds the file DTOs for each job. The keys are the job
    names and the values are dictionaries that map file names to file DTOs."""

    def __init__(self):
        """Create a new AppCache object. Use set_cache to set the cache state."""
        self.file_dto_cache = {}

    def set_cache(self, file_dto_cache):
        """Explicitly set the cache state to the provided cache buildup."""
        self.file_dto_cache = file_dto_cache

    def set_cached_files(self, job_name: str, files: Dict[str, FileModelDTO]):
        """Set the cached files for the given job name"""
        self.file_dto_cache[job_name] = files

    def set_cached_file(self, job_name: str, file_name: str, file: FileModelDTO):
        """Set the cached file for the given job name and file name"""
        self.file_dto_cache[job_name][file_name] = file

    def get_files_of_job(self, job_name: str) -> List[FileModelDTO]:
        """Get the files of the given job name"""
        return list(self.file_dto_cache[job_name].values())

    def get_filesets(self):
        """Get all filesets in the cache"""
        return self.file_dto_cache.values()

    def get_cached_job_names(self) -> List[str]:
        """Get all job names in the cache"""
        return self.file_dto_cache.keys()

    def get_cached_file(self, job_name: str, file_name: str) -> FileModelDTO:
        """Get the file for the given job name and file name"""
        return self.file_dto_cache[job_name][file_name]

    def get_cached_files(self, job_name: str) -> Dict[str, FileModelDTO]:
        """Get all files for the given job name"""
        return self.file_dto_cache[job_name]

    def is_cached_job(self, job_name: str) -> bool:
        """Check if the given job is cached"""
        return job_name in self.file_dto_cache

    def is_cached_file(self, job_name: str, file_name: str) -> bool:
        """Check if the given file is cached"""
        return (
            self.is_cached_job(job_name) and file_name in self.file_dto_cache[job_name]
        )

    def get_cache(self):
        """Get the entire cache"""
        return self.file_dto_cache

    def drop_job(self, job_name: str) -> None:
        """Drop the given job from the cache"""
        if job_name in self.file_dto_cache:
            self.file_dto_cache.pop(job_name)

    def drop_file(self, job_name: str, file_name: str) -> None:
        """Delete the given file entry from the cache"""
        if job_name in self.file_dto_cache and file_name in self.file_dto_cache[job_name]:
            del self.file_dto_cache[job_name][file_name]
