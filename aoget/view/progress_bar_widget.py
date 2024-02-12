from PyQt6.QtWidgets import QProgressBar


class ProgressBarWidget(QProgressBar):
    """Custom progress bar widget that is sortable and can be passivated
    or activated."""

    PROGRESS_BAR_PASSIVE_STYLE = """
        QProgressBar {
            border: 1px solid grey;
            border-radius: 0px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #d0d6db;
            width: 1px;
        }"""

    PROGRESS_BAR_ACTIVE_STYLE = """
        QProgressBar {
            border: 1px solid grey;
            border-radius: 0px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #31a7f5;
            width: 1px;
        }"""

    def set_active(self):
        """Set the progress bar to active."""
        self.setStyleSheet(self.PROGRESS_BAR_ACTIVE_STYLE)

    def set_passive(self):
        """Set the progress bar to passive."""
        self.setStyleSheet(self.PROGRESS_BAR_PASSIVE_STYLE)

    def __lt__(self, other):
        """Sort the table by the progress."""
        if isinstance(other, ProgressBarWidget):
            return self.value() < other.value()
        elif other.__class__.__name__ == "ProgressBarPlaceholderWidgetItem":
            return False
        else:
            return super().__lt__(other)

    def sort_table(table, progress_column_idx):
        """Sort the table."""
        rows = []
        for row in range(table.rowCount()):
            widget = None
            item = None
            if table.item(row, progress_column_idx) is not None:
                item = table.item(row, progress_column_idx)
            else:
                widget = table.cellWidget(row, progress_column_idx)
            val = widget.value() if widget else 101
            rows.append((val, item, widget, row))
        table_sort_order = table.horizontalHeader().sortIndicatorOrder()
        rows.sort(reverse=table_sort_order.value == 1)

        # Reorder the rows in the table
        for newRow, (val, item, widget, oldRow) in enumerate(rows):
            for col in range(table.columnCount()):
                table_item = table.item(oldRow, col)
                cell_widget = table.cellWidget(oldRow, col)
                if cell_widget:
                    w = table.cellWidget(oldRow, col)
                    table.setCellWidget(newRow, col, w)
                elif table_item:
                    it = table.takeItem(oldRow, col)
                    table.setItem(newRow, col, it)
