import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QLabel, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QLineEdit, QHBoxLayout, QComboBox, QSplitter, QSizePolicy,
    QTabWidget, QMessageBox, QCheckBox, QGroupBox, QButtonGroup
)
from PyQt6.QtCore import Qt

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        try:
            self.numeric_value = float(text)
        except ValueError:
            self.numeric_value = text  # If it's not numeric, fallback to string sorting.

    def __lt__(self, other):
        # Compare numeric values if possible, otherwise fallback to string comparison
        if isinstance(other, NumericTableWidgetItem):
            return self.numeric_value < other.numeric_value
        return super().__lt__(other)

class CSVAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV GroupBy Aggregator")
        self.df = pd.DataFrame()

        layout = QVBoxLayout()

        # File selection section
        self.file_label = QLabel("No file selected.")
        self.file_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Fix size
        layout.addWidget(self.file_label)

        open_button = QPushButton("Open CSV/TXT File")
        open_button.clicked.connect(self.open_file)
        layout.addWidget(open_button)

        # Separator input section with checkboxes for predefined separators
        sep_layout = QVBoxLayout()
        # Create a group box for the checkboxes
        self.sep_groupbox = QGroupBox("Select Separator")
        self.sep_groupbox.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sep_group_layout = QHBoxLayout(self.sep_groupbox)

        self.sep_btngroup = QButtonGroup(self.sep_groupbox)
        self.sep_btngroup.setExclusive(True)  # Ensure only one button can be checked at a time
        
        # Create checkboxes for each separator
        self.comma_checkbox = QCheckBox(", (Comma)")
        self.semicolon_checkbox = QCheckBox("; (Semicolon)")
        self.space_checkbox = QCheckBox("Space")
        self.tab_checkbox = QCheckBox("Tab")
        
        self.sep_btngroup.addButton(self.comma_checkbox)
        self.sep_btngroup.addButton(self.semicolon_checkbox)
        self.sep_btngroup.addButton(self.space_checkbox)
        self.sep_btngroup.addButton(self.tab_checkbox)

        # Set default separator to comma
        self.comma_checkbox.setChecked(True)

        # Connect the checkboxes to the update_separator method
        self.comma_checkbox.stateChanged.connect(self.update_separator)
        self.semicolon_checkbox.stateChanged.connect(self.update_separator)
        self.space_checkbox.stateChanged.connect(self.update_separator)
        self.tab_checkbox.stateChanged.connect(self.update_separator)

        sep_group_layout.addWidget(self.comma_checkbox)
        sep_group_layout.addWidget(self.semicolon_checkbox)
        sep_group_layout.addWidget(self.space_checkbox)
        sep_group_layout.addWidget(self.tab_checkbox)

        sep_layout.addWidget(self.sep_groupbox)
        layout.addLayout(sep_layout)

        # Filter input section
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter (e.g., City == 'Seattle'):")
        filter_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Fix height of label
        filter_layout.addWidget(filter_label)
        
        # Set filter input to expand horizontally
        self.filter_input = QLineEdit()
        self.filter_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow horizontal expansion
        filter_layout.addWidget(self.filter_input)
        layout.addLayout(filter_layout)

        # Create QSplitter only for GroupBy and Output widgets
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # GroupBy Checkbox List
        groupby_container = QWidget()
        groupby_layout = QVBoxLayout(groupby_container)
        groupby_layout.addWidget(QLabel("Select GroupBy Numeric Columns:"))
        self.groupby_list = QListWidget()
        self.groupby_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.groupby_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        groupby_layout.addWidget(self.groupby_list)
        groupby_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Output Tabs (Raw Data and Aggregation Results)
        self.tabs = QTabWidget()
        self.result_table = QTableWidget()
        self.result_table.setSortingEnabled(True)
        self.tabs.addTab(self.result_table, "Aggregation Result")

        self.raw_table = QTableWidget()
        self.tabs.addTab(self.raw_table, "Raw Data")

        # Add GroupBy and Output to splitter, so only these can resize
        splitter.addWidget(groupby_container)
        splitter.addWidget(self.tabs)

        # Set the initial size of splitter sections
        splitter.setSizes([200, 800])  # GroupBy is 200px wide, Output takes the rest

        layout.addWidget(splitter)

        # Aggregation settings (non-resizable)
        agg_label = QLabel("Aggregation method:")
        agg_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Fix height of label
        layout.addWidget(agg_label)

        self.agg_combo = QComboBox()
        self.agg_combo.addItems(["sum", "average", "count"])
        layout.addWidget(self.agg_combo)

        column_label = QLabel("Select column for aggregation:")
        column_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Fix height of label
        layout.addWidget(column_label)

        self.column_combo = QComboBox()
        layout.addWidget(self.column_combo)

        apply_button = QPushButton("Apply GroupBy and Aggregation")
        apply_button.clicked.connect(self.apply_groupby)
        layout.addWidget(apply_button)

        export_button = QPushButton("Export Result to CSV")
        export_button.clicked.connect(self.export_result)
        layout.addWidget(export_button)

        self.setLayout(layout)

        # Initialize separator field to store separator for reading CSV
        self.separator = ','  # Default separator is comma
        self.sep_input = QLineEdit(self.separator)
        self.sep_input.setEnabled(False)  # Make the separator input non-editable

    def update_separator(self):
        """Update the separator based on checkbox selection."""


        # Update the separator based on the selected checkbox
        if self.comma_checkbox.isChecked():
            self.separator = ","
        elif self.semicolon_checkbox.isChecked():
            self.separator = ";"
        elif self.space_checkbox.isChecked():
            self.separator = " "
        elif self.tab_checkbox.isChecked():
            self.separator = "\t"
        
        # Show the current separator in the read-only input field
        self.sep_input.setText(self.separator)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Data Files (*.csv *.txt *.*)")
        if file_path:
            try:
                # Use the selected separator to read the file
                df = pd.read_csv(file_path, sep=self.separator)
                filter_str = self.filter_input.text().strip()
                if filter_str:
                    df = df.query(filter_str)
                self.df = df
                self.file_label.setText(file_path)
                self.update_column_selection()
                self.populate_raw_table()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def update_column_selection(self):
        self.groupby_list.clear()
        self.column_combo.clear()
        if self.df.empty:
            return

        for col in self.df.columns:
            if pd.api.types.is_numeric_dtype(self.df[col]):
                item = QListWidgetItem(col)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.groupby_list.addItem(item)
                self.column_combo.addItem(col)

    def populate_raw_table(self):
        self.raw_table.setRowCount(min(100, self.df.shape[0]))
        self.raw_table.setColumnCount(self.df.shape[1])
        self.raw_table.setHorizontalHeaderLabels(self.df.columns)

        for row in range(min(100, self.df.shape[0])):
            for col in range(self.df.shape[1]):
                val = self.df.iat[row, col]
                item = NumericTableWidgetItem(str(val))
                self.raw_table.setItem(row, col, item)

    def apply_groupby(self):
        if self.df.empty:
            return

        groupby_cols = [self.groupby_list.item(i).text() for i in range(self.groupby_list.count())
                        if self.groupby_list.item(i).checkState() == Qt.CheckState.Checked]
        if not groupby_cols:
            QMessageBox.warning(self, "GroupBy", "Please select at least one groupby column.")
            return

        agg_column = self.column_combo.currentText()
        agg_method = self.agg_combo.currentText()

        # Perform GroupBy operation efficiently
        if agg_method == "sum":
            grouped_df = self.df.groupby(groupby_cols)[agg_column].sum().reset_index()
        elif agg_method == "average":
            grouped_df = self.df.groupby(groupby_cols)[agg_column].mean().reset_index()
        else:
            grouped_df = self.df.groupby(groupby_cols)[agg_column].count().reset_index()

        # Display in result_table
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
            headers = [self.result_table.horizontalHeaderItem(i).text() for i in range(self.result_table.columnCount())]
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
