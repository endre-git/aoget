from model.file_event import FileEvent


class FileEventDTO:
    def __init__(self, timestamp: str, event: str):
        self.timestamp = timestamp
        self.event = event

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "event": self.event
        }

    def build_model(self, file_model):
        return FileEvent(
            timestamp=self.timestamp,
            event=self.event,
            file=file_model
        )

    @classmethod
    def from_model(cls, file_event: FileEvent):
        return cls(
            timestamp=file_event.timestamp,
            event=file_event.event
        )

    def __str__(self):
        return f"FileEventDTO(timestamp={self.timestamp}, event={self.event})"

    def __repr__(self):
        return self.__str__()
