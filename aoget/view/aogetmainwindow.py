"""Main window of the application."""

from PyQt6.QtWidgets import QMainWindow, QHeaderView, QTableWidgetItem
from PyQt6 import uic

from view.newjobdialog import NewJobDialog
from util.aogetutil import human_timestamp_from


class AoGetMainWindow(QMainWindow):
    """Main window of the application. Note that this is more a controller than a view.
    View was done in Qt Designer and is loaded from a .ui file found under
    aoget/qt/main_window.ui"""

    jobs = {}

    def __init__(self):
        super(AoGetMainWindow, self).__init__()
        uic.loadUi("aoget/qt/main_window.ui", self)
        self.__setup_ui()
        self.show()

    def __setup_ui(self):
        """Setup the UI"""
        # jobs table header
        self.__setup_jobs_table()
        self.__setup_files_table()

    def __setup_jobs_table(self):
        """Setup the jobs table and controls around it"""
        self.tblJobs.setColumnCount(6)
        self.tblJobs.setHorizontalHeaderLabels(
            ["Name", "Status", "File Count", "Progress", "Page URL", "Target Folder"]
        )
        header = self.tblJobs.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tblJobs.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        self.tblJobs.setSelectionMode(QHeaderView.SelectionMode.SingleSelection)
        # job control buttons
        self.btnCreateNew.clicked.connect(self.__on_create_new_job)

        # jobs table selection
        self.tblJobs.itemSelectionChanged.connect(self.__on_job_selected)
        self.tblJobs.doubleClicked.connect(self.__on_job_table_double_clicked)

    def __setup_files_table(self):
        """Setup the files table and controls around it"""
        self.tblFiles.setColumnCount(7)
        self.tblFiles.setHorizontalHeaderLabels(
            ["Name", "Status", "Size", "Progress", "URL", "Last Updated", "Last Event"]
        )
        header = self.tblFiles.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.tblFiles.setSelectionBehavior(QHeaderView.SelectionBehavior.SelectRows)
        self.tblFiles.setSelectionMode(QHeaderView.SelectionMode.SingleSelection)

        # jobs table selection
        # self.tblFiles.doubleClicked.connect(self.__on_file_table_double_clicked)

    def __update_jobs_table(self):
        """Update the list of jobs"""
        self.tblJobs.setRowCount(len(self.jobs))

        for i, job in enumerate(self.jobs.values()):
            self.tblJobs.setItem(i, 0, QTableWidgetItem(job.name))
            self.tblJobs.setItem(i, 1, QTableWidgetItem(""))
            self.tblJobs.setItem(i, 2, QTableWidgetItem(""))
            self.tblJobs.setItem(i, 3, QTableWidgetItem(""))
            self.tblJobs.setItem(i, 4, QTableWidgetItem(job.page_url))
            self.tblJobs.setItem(i, 5, QTableWidgetItem(job.target_folder))

    def __on_job_selected(self):
        """A job has been selected in the jobs table"""
        self.__show_files(self.jobs[self.tblJobs.item(0, 0).text()])

    def __on_job_table_double_clicked(self):
        """A job has been double clicked in the jobs table"""
        self.__show_files(self.jobs[self.tblJobs.item(0, 0).text()])

    def __on_create_new_job(self):
        """Create a new job"""
        dlg = NewJobDialog()
        val = dlg.exec()
        if val == 1:
            print("New job created")
            self.__add_job(dlg.get_job())
        else:
            print("New job cancelled")

    def __add_job(self, job):
        """Add a job to the list of jobs"""
        self.jobs[job.name] = job
        self.__update_jobs_table()

    def __show_files(self, job):
        if job is None:
            return
        file_set = job.file_set
        selected_filenames = file_set.get_selected_filenames()
        self.tblFiles.setRowCount(len(selected_filenames))
        for i, filename in enumerate(selected_filenames):
            file = file_set.files[filename]
            if len(file.history) > 0:
                latest_history_timestamp = max(file.history.keys())
                latest_history_event = file.history[latest_history_timestamp]
            self.tblFiles.setItem(i, 0, QTableWidgetItem(file.name))
            self.tblFiles.setItem(i, 1, QTableWidgetItem(file.status))
            self.tblFiles.setItem(i, 2, QTableWidgetItem(file.size_bytes))
            self.tblFiles.setItem(i, 3, QTableWidgetItem())
            self.tblFiles.setItem(i, 4, QTableWidgetItem(file.url))
            self.tblFiles.setItem(i,
                                  5,
                                  QTableWidgetItem(human_timestamp_from(latest_history_timestamp) 
                                                   if latest_history_timestamp is not None
                                                   else ""))
            self.tblFiles.setItem(i,
                                  6,
                                  QTableWidgetItem(latest_history_event
                                                   if latest_history_event is not None
                                                   else ""))
