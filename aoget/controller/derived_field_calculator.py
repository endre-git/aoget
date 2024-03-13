import logging
from typing import Dict
from model.dto.file_model_dto import FileModelDTO
from model.dto.job_dto import JobDTO
from model.job_updates import JobUpdates

logger = logging.getLogger(__name__)


class DerivedFieldCalculator(object):
    """Calculate derived fields for the job and file models, based on a current view and a
    snapshot view. Derived fields include trends (ETA, rate, etc.) that are calculated based on
    the current values and a previous sampling a fixed time ago (1 second fixed currently).
    """

    def patch(
        current_job_updates: Dict[str, JobUpdates],
        job_updates_snapshot: Dict[str, JobUpdates],
    ) -> None:
        """Update the current_job_updates with the derived fields calculated using the
        job_updates_snapshot. Does this in-place, updating the current_job_updates."""
        global_rate = 0
        for jobname in current_job_updates:
            if jobname in job_updates_snapshot:
                current_job_update = current_job_updates[jobname]
                job_update_snapshot = job_updates_snapshot[jobname]
                DerivedFieldCalculator.__patch_job(
                    current_job_update, job_update_snapshot
                )
                global_rate += current_job_update.job_update.rate_bytes_per_sec

    def __patch_job(
        current_job_update: JobUpdates, job_update_snapshot: JobUpdates
    ) -> None:
        """Update the current_job_update with the derived fields calculated using the
        job_update_snapshot. Does this in-place, updating the current_job_update."""
        for filename, current_file in current_job_update.file_model_updates.items():
            if filename in job_update_snapshot.file_model_updates.keys():
                DerivedFieldCalculator.__patch_file(
                    current_file, job_update_snapshot.file_model_updates[filename]
                )
        if current_job_update.job_update is None:
            current_job_update.job_update = JobDTO(
                id=-1, name=current_job_update.job_name
            )
        total_rate = 0
        for filename, current_file in current_job_update.file_model_updates.items():
            total_rate += current_file.rate_bytes_per_sec
        current_job_update.job_update.rate_bytes_per_sec = total_rate

    def __patch_file(current_file: FileModelDTO, file_snapshot: FileModelDTO):
        """Update the current_file with the derived fields calculated using the
        file_snapshot. Does this in-place, updating the current_file."""
        total = current_file.size_bytes or 0
        written = current_file.downloaded_bytes or 0
        percent_completed = 0 if total == 0 else int(100 * written / total)
        snapshot_downloaded_bytes = file_snapshot.downloaded_bytes or 0
        delta = written - snapshot_downloaded_bytes
        eta_seconds = int((total - written) / delta) if delta > 0 else 0
        current_file.rate_bytes_per_sec = delta
        current_file.eta_seconds = eta_seconds
        current_file.percent_completed = percent_completed

    def file_deselected_in_job(job_dto, file_model):
        if job_dto.selected_files_count is not None:
            job_dto.selected_files_count -= 1
            if file_model.size_bytes and file_model.size_bytes > 0:
                job_dto.selected_files_with_known_size -= 1
                job_dto.total_size_bytes -= file_model.size_bytes
            if file_model.downloaded_bytes and file_model.downloaded_bytes > 0:
                job_dto.downloaded_bytes -= file_model.downloaded_bytes
        else:
            logger.error(
                "file_deselected_in_job: job_dto.selected_files_count is None"
            )
