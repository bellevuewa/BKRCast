import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QLineEdit, QHBoxLayout, QComboBox, QSplitter, QSizePolicy,
    QTabWidget, QMessageBox, QCheckBox, QGroupBox, QButtonGroup, QFormLayout, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        try:
            self.numeric_value = float(text)
        except ValueError:
            self.numeric_value = text

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)


class CSVAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV GroupBy Aggregator")
        self.df = pd.DataFrame() # original DataFrame
        self.filted_df = pd.DataFrame() # filtered DataFrame

        layout = QVBoxLayout()

        self.file_path = ""
        # File label
        self.file_label = QLabel("No file selected.")
        self.file_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.file_label)

        open_button = QPushButton("Open CSV/TXT File")
        open_button.clicked.connect(self.select_file)
        layout.addWidget(open_button)

        # Separator checkboxes
        sep_layout = QVBoxLayout()
        self.sep_groupbox = QGroupBox("Select Separator")
        self.sep_groupbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sep_group_layout = QHBoxLayout(self.sep_groupbox)

        self.sep_btngroup = QButtonGroup(self.sep_groupbox)
        self.sep_btngroup.setExclusive(True)  # Ensure only one button can be checked at a time

        self.comma_checkbox = QCheckBox(", (Comma)")
        self.semicolon_checkbox = QCheckBox("; (Semicolon)")
        self.space_checkbox = QCheckBox("Space")
        self.tab_checkbox = QCheckBox("Tab")

        for checkbox in [self.comma_checkbox, self.semicolon_checkbox, self.space_checkbox, self.tab_checkbox]:
            self.sep_btngroup.addButton(checkbox)
            checkbox.stateChanged.connect(self.update_separator)
            sep_group_layout.addWidget(checkbox)

        self.sep_groupbox.setLayout(sep_group_layout)
        sep_layout.addWidget(self.sep_groupbox)
        layout.addLayout(sep_layout)

        # Filter section
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter (e.g., City == 'Seattle'):")
        filter_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.filter_input = QLineEdit()
        self.filter_input.setToolTip("use pandas query syntax")
        self.filter_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        apply_filter_button = QPushButton("▶")
        apply_filter_button.setToolTip("Apply Filter")
        apply_filter_button.setFixedSize(30, self.filter_input.sizeHint().height())
        apply_filter_button.clicked.connect(self.apply_filter)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        filter_layout.addWidget(apply_filter_button)
        layout.addLayout(filter_layout)

        # Splitter for groupby and output
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # GroupBy list
        groupby_container = QWidget()
        groupby_layout = QVBoxLayout(groupby_container)
        groupby_layout.addWidget(QLabel("Select GroupBy Columns:"))
        self.groupby_list = QListWidget()
        self.groupby_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.groupby_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        groupby_layout.addWidget(self.groupby_list)
        groupby_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Tab view
        self.tabs = QTabWidget()
        self.result_table = QTableWidget()
        self.result_table.setSortingEnabled(True)
        self.result_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # Enable custom context menu
        self.result_table.customContextMenuRequested.connect(self.show_result_table_context_menu)        
        self.tabs.addTab(self.result_table, "Aggregation Result")

        self.raw_table = QTableWidget()
        self.tabs.addTab(self.raw_table, "Raw Data")

        splitter.addWidget(groupby_container)
        splitter.addWidget(self.tabs)
        splitter.setSizes([200, 800])
        layout.addWidget(splitter)

        # Aggregation configuration
        agg_config_label = QLabel("Aggregation Configuration:")
        agg_config_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(agg_config_label)

        self.agg_form = QFormLayout()
        self.agg_combos = {}  # Mapping from column to its combo box

        self.agg_widget = QWidget()
        self.agg_widget.setLayout(self.agg_form)
        layout.addWidget(self.agg_widget)

        apply_button = QPushButton("Apply GroupBy and Aggregation")
        apply_button.clicked.connect(self.apply_groupby)
        layout.addWidget(apply_button)

        export_button = QPushButton("Export Result to CSV")
        export_button.clicked.connect(self.export_result)
        layout.addWidget(export_button)

        self.setLayout(layout)

        self.separator = ','
        self.sep_input = QLineEdit(self.separator)
        self.sep_input.setEnabled(False)

    def show_result_table_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("Copy All to Clipboard", self)
        copy_action.triggered.connect(self.copy_result_to_clipboard)
        menu.addAction(copy_action)
        menu.exec(self.result_table.viewport().mapToGlobal(pos))

    def apply_filter(self):
        filter_str = self.filter_input.text().strip()

        try:
            if filter_str:
                self.filtered_df = self.df.query(filter_str)
            else:
                self.filtered_df = self.df
            self.raw_table.setRowCount(min(100, self.filtered_df.shape[0]))
            self.raw_table.setColumnCount(self.filtered_df.shape[1])
            self.raw_table.setHorizontalHeaderLabels(self.filtered_df.columns)

            for row in range(min(100, self.filtered_df.shape[0])):
                for col in range(self.filtered_df.shape[1]):
                    val = self.filtered_df.iat[row, col]
                    item = NumericTableWidgetItem(str(val))
                    self.raw_table.setItem(row, col, item)

        except Exception as e:
            QMessageBox.critical(self, "Filter Error", str(e))

    def copy_result_to_clipboard(self):
        rows = self.result_table.rowCount()
        cols = self.result_table.columnCount()

        # Include header row
        headers = [self.result_table.horizontalHeaderItem(i).text() for i in range(cols)]
        text = "\t".join(headers) + "\n"

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.result_table.item(row, col)
                row_data.append(item.text() if item else "")
            text += "\t".join(row_data) + "\n"

        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copied", "All data copied to clipboard including headers.")

    def update_separator(self):
        if self.comma_checkbox.isChecked():
            self.separator = ","
        elif self.semicolon_checkbox.isChecked():
            self.separator = ";"
        elif self.space_checkbox.isChecked():
            self.separator = " "
        elif self.tab_checkbox.isChecked():
            self.separator = "\t"
        self.sep_input.setText(self.separator)
        self.open_file()  # Reopen the file with the new separator

    def select_file(self):
        self.file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Data Files (*.csv *.txt *.*)")
        if self.file_path:
            try:
                self.file_label.setText(self.file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def open_file(self):
        if self.file_path:
            try:
                df = pd.read_csv(self.file_path, sep=self.separator)
                self.df = df                
                filter_str = self.filter_input.text().strip()
                if filter_str:
                    self.filtered_df = df.query(filter_str)
                else:
                    self.filtered_df = df
                self.file_label.setText(self.file_path)
                self.update_column_selection()
                self.populate_raw_table()
            except Exception as e:
                self.groupby_list.clear()
                self.agg_combos.clear()
                QMessageBox.critical(self, "Error", str(e))

    def update_column_selection(self):
        self.groupby_list.clear()
        self.agg_combos.clear()
        # Clear existing form rows
        while self.agg_form.rowCount() > 0:
            self.agg_form.removeRow(0)

        if self.filtered_df.empty:
            return

        for col in self.filtered_df.columns:
            item = QListWidgetItem(col)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.groupby_list.addItem(item)

            if pd.api.types.is_numeric_dtype(self.filtered_df[col]):
                combo = QComboBox()
                combo.addItems(["", "sum", "average", "count", "min", "max"])  # Default is blank
                self.agg_form.addRow(QLabel(col), combo)
                self.agg_combos[col] = combo

    def populate_raw_table(self):
        self.raw_table.setRowCount(min(100, self.filtered_df.shape[0]))
        self.raw_table.setColumnCount(self.filtered_df.shape[1])
        self.raw_table.setHorizontalHeaderLabels(self.filtered_df.columns)

        for row in range(min(100, self.filtered_df.shape[0])):
            for col in range(self.filtered_df.shape[1]):
                val = self.filtered_df.iat[row, col]
                item = NumericTableWidgetItem(str(val))
                self.raw_table.setItem(row, col, item)

    def apply_groupby(self):
        if self.filtered_df.empty:
            QMessageBox.warning(self, "GroupBy", "No data is selected.")
            return

        groupby_cols = [self.groupby_list.item(i).text()
                        for i in range(self.groupby_list.count())
                        if self.groupby_list.item(i).checkState() == Qt.CheckState.Checked]

        if not groupby_cols:
            QMessageBox.warning(self, "GroupBy", "Please select at least one groupby column.")
            return

        agg_dict = {}
        for col, combo in self.agg_combos.items():
            method = combo.currentText()
            if method:
                if method == "average":
                    agg_dict[col] = "mean"
                else:
                    agg_dict[col] = method

        if not agg_dict:
            QMessageBox.warning(self, "Aggregation", "Please select at least one column to aggregate.")
            return

        try:
            grouped_df = self.filtered_df.groupby(groupby_cols).agg(agg_dict).reset_index()
        except Exception as e:
            QMessageBox.critical(self, "Aggregation Error", str(e))
            return

        self.result_table.setRowCount(grouped_df.shape[0])
        self.result_table.setColumnCount(grouped_df.shape[1])
        self.result_table.setHorizontalHeaderLabels(grouped_df.columns)

        for row in range(grouped_df.shape[0]):
            for col in range(grouped_df.shape[1]):
                val = grouped_df.iat[row, col]
                item = NumericTableWidgetItem(str(val))
                self.result_table.setItem(row, col, item)

    def export_result(self):
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "Export Failed", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if file_path:
            data = []
            headers = [self.result_table.horizontalHeaderItem(i).text()
                       for i in range(self.result_table.columnCount())]
            for row in range(self.result_table.rowCount()):
                row_data = []
                for col in range(self.result_table.columnCount()):
                    item = self.result_table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            df_export = pd.DataFrame(data, columns=headers)
            df_export.to_csv(file_path, index=False)
            QMessageBox.information(self, "Export Successful", f"Saved to:\n{file_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CSVAnalyzer()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())
