class JobDTO:
    def __init__(
        self,
        id,
        name,
        status=None,
        page_url=None,
        downloaded_bytes=None,
        total_size_bytes=None,
        target_folder=None,
        rate_bytes_per_sec=None,
        threads_active=None,
        threads_allocated=None,
        files_done=None,
        selected_files_count=None,
        selected_files_with_known_size=None,
        progress=None,
        size_resolver_status=None,
        deleted=False,
    ):
        self.id = id
        self.name = name
        self.status = status
        self.page_url = page_url
        self.downloaded_bytes = downloaded_bytes
        self.total_size_bytes = total_size_bytes
        self.target_folder = target_folder
        self.rate_bytes_per_sec = rate_bytes_per_sec
        self.threads_active = threads_active
        self.threads_allocated = threads_allocated
        self.files_done = files_done
        self.selected_files_count = selected_files_count
        self.selected_files_with_known_size = selected_files_with_known_size
        self.progress = progress
        self.size_resolver_status = size_resolver_status
        self.deleted = False

    @classmethod
    def from_model(cls, job_model):
        job_dto = cls(
            id=job_model.id,
            name=job_model.name,
            status=job_model.status,
            page_url=job_model.page_url,
            total_size_bytes=job_model.total_size_bytes,
            target_folder=job_model.target_folder,
            downloaded_bytes=job_model.downloaded_bytes,
            selected_files_count=job_model.selected_files_count,
            selected_files_with_known_size=job_model.selected_files_with_known_size,
            threads_allocated=job_model.threads_allocated,
            files_done=job_model.files_done,
        )
        # job_dto.files = [FileModelDTO.from_model(file_model) for file_model in job_model.files]
        return job_dto

    def merge(self, other):
        if other.name:
            self.name = other.name
        if other.status:
            self.status = other.status
        if other.page_url:
            self.page_url = other.page_url
        if other.total_size_bytes:
            self.total_size_bytes = other.total_size_bytes
        if other.target_folder:
            self.target_folder = other.target_folder
        if other.deleted:
            self.deleted = other.deleted
        if other.downloaded_bytes:
            self.downloaded_bytes = other.downloaded_bytes
        if other.threads_active:
            self.threads_active = other.threads_active
        if other.threads_allocated:
            self.threads_allocated = other.threads_allocated
        if other.files_done:
            self.files_done = other.files_done
        if other.selected_files_count:
            self.selected_files_count = other.selected_files_count
        if other.selected_files_with_known_size:
            self.selected_files_with_known_size = other.selected_files_with_known_size
        if other.progress:
            self.progress = other.progress
        if other.size_resolver_status:
            self.size_resolver_status = other.size_resolver_status
        return self

    def merge_into_model(self, job_model):
        job_model.name = self.name if self.name else job_model.name
        job_model.status = self.status if self.status else job_model.status
        job_model.page_url = self.page_url if self.page_url else job_model.page_url
        job_model.total_size_bytes = (
            self.total_size_bytes
            if self.total_size_bytes
            else job_model.total_size_bytes
        )
        job_model.target_folder = (
            self.target_folder if self.target_folder else job_model.target_folder
        )
        job_model.downloaded_bytes = (
            self.downloaded_bytes
            if self.downloaded_bytes
            else job_model.downloaded_bytes
        )
        job_model.selected_files_count = (
            self.selected_files_count
            if self.selected_files_count
            else job_model.selected_files_count
        )
        job_model.selected_files_with_known_size = (
            self.selected_files_with_known_size
            if self.selected_files_with_known_size
            else job_model.selected_files_with_known_size
        )
        job_model.threads_allocated = (
            self.threads_allocated
            if self.threads_allocated
            else job_model.threads_allocated
        )
        job_model.files_done = (
            self.files_done if self.files_done else job_model.files_done
        )

    def update_from_model(self, job_model):
        self.id = job_model.id
        self.name = job_model.name if job_model.name else self.name
        self.status = job_model.status if job_model.status else self.status
        self.page_url = job_model.page_url if job_model.page_url else self.page_url
        self.total_size_bytes = (
            job_model.total_size_bytes
            if job_model.total_size_bytes
            else self.total_size_bytes
        )
        self.target_folder = (
            job_model.target_folder if job_model.target_folder else self.target_folder
        )
        self.downloaded_bytes = (
            job_model.downloaded_bytes
            if job_model.downloaded_bytes
            else self.downloaded_bytes
        )
        self.selected_files_count = (
            job_model.selected_files_count
            if job_model.selected_files_count
            else self.selected_files_count
        )
        self.selected_files_with_known_size = (
            job_model.selected_files_with_known_size
            if job_model.selected_files_with_known_size
            else self.selected_files_with_known_size
        )
        self.threads_allocated = (
            job_model.threads_allocated
            if job_model.threads_allocated
            else self.threads_allocated
        )
        self.files_done = (
            job_model.files_done if job_model.files_done else self.files_done
        )
        return self

    def is_size_not_resolved(self):
        return self.total_size_bytes is None or (
            self.total_size_bytes is not None
            and self.selected_files_count is not None
            and self.selected_files_count != self.selected_files_with_known_size
        )
