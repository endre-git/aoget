from util.aogetutil import human_filesize


class FileDetailsController:
    """Data links for the file details dialog"""

    def __init__(
        self,
        file_details_dialog: any,
        app_controller: any,
        job_name: str,
        file_name: str,
    ):
        """Create a new FileDetailsController."""
        self.file_details_dialog = file_details_dialog
        self.app_controller = app_controller
        self.job_name = job_name
        self.file_name = file_name

    def get_properties(self):
        """Get the properties of the file."""
        file_model_dto = self.app_controller.files.get_file_dto(
            self.job_name, self.file_name
        )
        props = {}
        props["Name"] = file_model_dto.name
        props["Source URL"] = file_model_dto.url
        props["Target Path"] = file_model_dto.target_path
        size_bytes = (
            file_model_dto.size_bytes
            if file_model_dto.size_bytes is not None and file_model_dto.size_bytes > -1
            else ""
        )
        props["Size"] = human_filesize(size_bytes) or "Unknown"
        return props

    def get_history_entries(self):
        """Get the history entries of the file."""
        event_dtos = self.app_controller.files.get_file_event_dtos(
            self.job_name, self.file_name
        )
        event_dtos.sort(key=lambda event: event.timestamp, reverse=True)
        entries = {}
        for event_dto in event_dtos:
            entries[event_dto.timestamp] = event_dto.event
        return entries
