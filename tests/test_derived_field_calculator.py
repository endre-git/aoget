import pytest
from aoget.model.job_updates import JobUpdates
from aoget.model.dto.file_model_dto import FileModelDTO
from aoget.controller.derived_field_calculator import DerivedFieldCalculator

# Sample data for testing
job_name = "test_job"
file_name = "test_file"
total_size = 1000
downloaded_initial = 400
downloaded_snapshot = 300


@pytest.fixture
def current_job_updates():
    file_dto = FileModelDTO(
        job_name=job_name,
        name=file_name,
        size_bytes=total_size,
        downloaded_bytes=downloaded_initial,
    )
    job_updates = JobUpdates(job_name)
    job_updates.file_model_updates[file_name] = file_dto
    return {job_name: job_updates}


@pytest.fixture
def job_updates_snapshot():
    file_dto_snapshot = FileModelDTO(
        job_name=job_name,
        name=file_name,
        size_bytes=total_size,
        downloaded_bytes=downloaded_snapshot,
    )
    job_updates = JobUpdates(job_name)
    job_updates.file_model_updates[file_name] = file_dto_snapshot
    return {job_name: job_updates}


def test_patch(current_job_updates, job_updates_snapshot):
    DerivedFieldCalculator.patch(current_job_updates, job_updates_snapshot)
    file_update = current_job_updates[job_name].file_model_updates[file_name]

    # Test if percent_completed is calculated correctly
    assert file_update.percent_completed == int(100 * downloaded_initial / total_size)

    # Test if rate_bytes_per_sec is calculated correctly
    assert file_update.rate_bytes_per_sec == (downloaded_initial - downloaded_snapshot)

    # Test if eta_seconds is calculated correctly
    expected_eta = int(
        (total_size - downloaded_initial) / (downloaded_initial - downloaded_snapshot)
    )
    assert file_update.eta_seconds == expected_eta
