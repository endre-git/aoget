from urllib.parse import unquote


class FileModelDTO:
    """Data transfer object for file models. This is used to access the database models in a
    thread-safe manner. History entries are sorted by timestamp in descending order, no matter
    in which order they were added to the model.
    """

    def __init__(
        self,
        job_name: str,
        name: str,
        extension: str = None,
        selected: bool = True,
        url: str = None,
        size_bytes: int = None,
        downloaded_bytes: int = None,
        status: str = None,
        rate_bytes_per_sec: int = -1,
        eta_seconds: int = -1,
        percent_completed: int = -1,
        last_event_timestamp: str = None,
        last_event: str = None,
        target_path: str = None,
        priority: int = None,
        deleted: bool = False,
    ):
        self.name = name
        self.job_name = job_name
        self.extension = extension
        self.selected = selected
        self.url = url
        self.size_bytes = size_bytes
        self.downloaded_bytes = downloaded_bytes
        self.status = status
        self.rate_bytes_per_sec = rate_bytes_per_sec
        self.eta_seconds = eta_seconds
        self.percent_completed = percent_completed
        self.last_event_timestamp = last_event_timestamp
        self.last_event = last_event
        self.target_path = target_path
        self.priority = priority
        self.set_percent_completed
        self.deleted = False

    @classmethod
    def from_url(cls, url):
        name = unquote(url.split("/")[-1])
        extension = name.split(".")[-1] if "." in name else ""
        file_model_dto = cls(
            name=name,
            extension=extension,
            job_name=None,
            url=url,
        )
        return file_model_dto

    @classmethod
    def from_model(cls, file_model, job_name):
        file_model_dto = cls(
            name=file_model.name,
            job_name=job_name,
            extension=file_model.extension,
            selected=file_model.selected,
            url=file_model.url,
            size_bytes=file_model.size_bytes,
            downloaded_bytes=file_model.downloaded_bytes,
            status=file_model.status,
            last_event_timestamp=file_model.get_latest_history_timestamp(),
            last_event=file_model.get_latest_history_entry().event,
            target_path=file_model.get_target_path(),
            priority=file_model.priority,
        )
        file_model_dto.set_percent_completed()
        return file_model_dto

    def to_dict(self):
        return {
            "name": self.name,
            "extension": self.extension,
            "selected": self.selected,
            "url": self.url,
            "size_bytes": self.size_bytes,
            "downloaded_bytes": self.downloaded_bytes,
            "status": self.status,
            "rate_bytes_per_sec": self.rate_bytes_per_sec,
            "eta_seconds": self.eta_seconds,
            "percent_completed": self.percent_completed,
            "last_event_timestamp": self.last_event_timestamp,
            "last_event": self.last_event,
            "target_path": self.target_path,
            "priority": self.priority,
            "deleted": self.deleted,
        }

    def __merge_static_fields(self, other_file_model_dto):
        """Merge the static fields from the other file model DTO into this one. The static fields
        are those that are not updated during the download process, such as the name, extension,
        selected, URL, priority, and target path. The other file model DTO's fields take
        precedence over this one's fields, if they are not None or empty."""
        if other_file_model_dto.name:
            self.name = other_file_model_dto.name
        if other_file_model_dto.extension:
            self.extension = other_file_model_dto.extension
        self.selected = (
            other_file_model_dto.selected
            if not other_file_model_dto.selected
            else self.selected
        )
        if other_file_model_dto.job_name:
            self.job_name = other_file_model_dto.job_name
        if other_file_model_dto.url:
            self.url = other_file_model_dto.url
        if other_file_model_dto.priority:
            self.priority = other_file_model_dto.priority
        if other_file_model_dto.target_path:
            self.target_path = other_file_model_dto.target_path

    def __merge_dynamic_fields(self, other_file_model_dto):
        """Merge the dynamic fields from the other file model DTO into this one. The dynamic fields
        are those that are updated during the download process, such as the size, downloaded bytes,
        status, rate, ETA, percent completed, last event timestamp, and last event. The other file
        model DTO's fields take precedence over this one's fields, if they are not None or empty.
        """
        if other_file_model_dto.size_bytes and other_file_model_dto.size_bytes > -1:
            self.size_bytes = other_file_model_dto.size_bytes
        if (
            other_file_model_dto.downloaded_bytes
            and other_file_model_dto.downloaded_bytes > -1
        ):
            self.downloaded_bytes = other_file_model_dto.downloaded_bytes
        if other_file_model_dto.status:
            self.status = other_file_model_dto.status
        if other_file_model_dto.deleted:
            self.deleted = other_file_model_dto.deleted
        if (
            other_file_model_dto.percent_completed
            and other_file_model_dto.percent_completed > -1
        ):
            self.percent_completed = other_file_model_dto.percent_completed
        if other_file_model_dto.last_event_timestamp:
            self.last_event_timestamp = other_file_model_dto.last_event_timestamp
        if other_file_model_dto.last_event:
            self.last_event = other_file_model_dto.last_event
        if (
            other_file_model_dto.rate_bytes_per_sec
            and other_file_model_dto.rate_bytes_per_sec > -1
        ):
            self.rate_bytes_per_sec = other_file_model_dto.rate_bytes_per_sec
        if other_file_model_dto.eta_seconds and other_file_model_dto.eta_seconds > -1:
            self.eta_seconds = other_file_model_dto.eta_seconds

    def merge(self, other_file_model_dto):
        self.__merge_static_fields(other_file_model_dto)
        self.__merge_dynamic_fields(other_file_model_dto)
        self.set_percent_completed()
        return self

    def merge_into_model(self, file_model):
        file_model.name = self.name if self.name else file_model.name
        file_model.extension = (
            self.extension if self.extension else file_model.extension
        )
        file_model.selected = self.selected
        file_model.url = self.url if self.url else file_model.url
        file_model.size_bytes = (
            self.size_bytes
            if self.size_bytes is not None and self.size_bytes > -1
            else file_model.size_bytes
        )
        file_model.downloaded_bytes = (
            self.downloaded_bytes
            if self.downloaded_bytes is not None and self.downloaded_bytes > -1
            else file_model.downloaded_bytes
        )
        file_model.status = self.status if self.status else file_model.status
        file_model.priority = self.priority if self.priority else file_model.priority

    def update_from_model(self, file_model):
        self.name = file_model.name if file_model.name else self.name
        self.extension = (
            file_model.extension if file_model.extension else self.extension
        )
        self.selected = (
            file_model.selected if not file_model.selected else self.selected
        )
        self.job_name = file_model.job.name
        self.url = file_model.url if file_model.url else self.url
        self.size_bytes = (
            file_model.size_bytes
            if file_model.size_bytes is not None and file_model.size_bytes > -1
            else self.size_bytes
        )
        self.downloaded_bytes = (
            file_model.downloaded_bytes
            if file_model.downloaded_bytes is not None
            and file_model.downloaded_bytes > -1
            else self.downloaded_bytes
        )
        self.status = file_model.status if file_model.status else self.status
        self.last_event_timestamp = file_model.get_latest_history_timestamp()
        self.last_event = file_model.get_latest_history_entry().event
        self.priority = file_model.priority
        self.target_path = file_model.get_target_path()
        self.set_percent_completed()

    def set_percent_completed(self):
        if (
            self.size_bytes is not None
            and self.size_bytes > 0
            and self.downloaded_bytes is not None
            and self.downloaded_bytes > -1
        ):
            self.percent_completed = int(100 * self.downloaded_bytes / self.size_bytes)

    def __str__(self):
        return (
            f"FileModelDTO(name={self.name}, job_name={self.job_name}, "
            f"extension={self.extension}, selected={self.selected}, "
            f"url={self.url}, size_bytes={self.size_bytes}, "
            f"downloaded_bytes={self.downloaded_bytes}, status={self.status}, "
            f"rate_bytes_per_sec={self.rate_bytes_per_sec}, "
            f"eta_seconds={self.eta_seconds}, "
            f"percent_completed={self.percent_completed}, "
            f"last_event_timestamp={self.last_event_timestamp}, "
            f"last_event={self.last_event}, "
            f"target_path={self.target_path}, deleted={self.deleted}, "
            f"priority={self.priority})"
        )

    def __repr__(self):
        return self.__str__()

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, FileModelDTO):
            return False
        return (
            self.name == __value.name
            and self.job_name == __value.job_name
            and self.extension == __value.extension
            and self.selected == __value.selected
            and self.url == __value.url
            and self.size_bytes == __value.size_bytes
            and self.downloaded_bytes == __value.downloaded_bytes
            and self.status == __value.status
            and self.rate_bytes_per_sec == __value.rate_bytes_per_sec
            and self.eta_seconds == __value.eta_seconds
            and self.percent_completed == __value.percent_completed
            and self.last_event_timestamp == __value.last_event_timestamp
            and self.last_event == __value.last_event
            and self.target_path == __value.target_path
            and self.deleted == __value.deleted
            and self.priority == __value.priority
        )

    def __lt__(self, other):
        return self.name < other.name
