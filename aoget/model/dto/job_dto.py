class JobDTO:
    def __init__(self, id, name, status, page_url, total_size_bytes, target_folder):
        self.id = id
        self.name = name
        self.status = status
        self.page_url = page_url
        self.total_size_bytes = total_size_bytes
        self.target_folder = target_folder
        self.deleted = False

    @classmethod
    def from_model(cls, job_model):
        job_dto = cls(
            id=job_model.id,
            name=job_model.name,
            status=job_model.status,
            page_url=job_model.page_url,
            total_size_bytes=job_model.total_size_bytes,
            target_folder=job_model.target_folder
        )
        # job_dto.files = [FileModelDTO.from_model(file_model) for file_model in job_model.files]
        return job_dto

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "page_url": self.page_url,
            "total_size_bytes": self.total_size_bytes,
            "target_folder": self.target_folder,
            "deleted": self.deleted
        }

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
        # if other.files:
        #     self.files = other.files
        return self

    def merge_into_model(self, job_model):
        job_model.name = self.name
        job_model.status = self.status
        job_model.page_url = self.page_url
        job_model.total_size_bytes = self.total_size_bytes
        job_model.target_folder = self.target_folder
