import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QMainWindow,
    QLabel, QListWidget, QListWidgetItem, QDialog, QTableWidget, QTableWidgetItem,
    QLineEdit, QHBoxLayout, QComboBox, QSplitter, QSizePolicy, QDialogButtonBox,
    QTabWidget, QMessageBox, QCheckBox, QGroupBox, QButtonGroup, QFormLayout, QMenu,
    QScrollArea, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QBrush, QColor

# This tool is used to merge multiple CSV files based on user-selected primary keys and separators.
# It provides functionalities to filter data, validate data,  perform groupby aggregations, and export results.
# 9/30/2025
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


class CSVAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV GroupBy Aggregator")
        self.filtered_df = pd.DataFrame() # filtered DataFrame
        self.join_file_path = ""
        self.file_configs = []
        self.dataframes = []

        widget = QWidget()
        layout = QVBoxLayout()

        open_button = QPushButton("Select Files")
        open_button.clicked.connect(self.select_file)
        layout.addWidget(open_button)

        self.file_list_widget = QListWidget()
        layout.addWidget(self.file_list_widget)

        # Merge type selection
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Merge type:"))
        self.merge_type_combo = QComboBox()
        self.merge_type_combo.addItems(["inner", "left", "right", "outer"])
        hbox.addWidget(self.merge_type_combo)
        layout.addLayout(hbox)

        hbox = QHBoxLayout()
        self.sum_btn = QPushButton("Merge or Load Files")
        self.sum_btn.clicked.connect(self.merge_files)
        hbox.addWidget(self.sum_btn)

        self.save_btn = QPushButton("Save Merged CSV")
        self.save_btn.clicked.connect(self.export_merged_results)

        self.validation_btn = QPushButton("Validate")
        self.validation_btn.clicked.connect(self.validation)
        hbox.addWidget(self.validation_btn)
        hbox.addWidget(self.save_btn)

        layout.addLayout(hbox)

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
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # Enable custom context menu
        self.result_table.customContextMenuRequested.connect(lambda pos: self.show_table_context_menu(self.result_table, pos))
         # connected like this in __init__
         # self.result_table.customContextMenuRequested.connect(self.show_result_table_context_menu)
         # Qt will call: show_result_table_context_menu(pos) for you
        self.tabs.addTab(self.result_table, "Aggregation Result")

        self.raw_table = QTableWidget()
        self.raw_table.setSortingEnabled(True)
        self.raw_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.tabs.addTab(self.raw_table, "Raw Data")

        self.valid_table = QTableWidget()
        self.valid_table.setSortingEnabled(True)
        self.valid_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.valid_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu) # Enable custom context menu
        self.valid_table.customContextMenuRequested.connect(lambda pos: self.show_table_context_menu(self.valid_table, pos))
        self.tabs.addTab(self.valid_table, "Validation")

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

        self.form_container = QWidget()
        self.form_container.setLayout(self.agg_form)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.form_container)
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.scroll_area)

        apply_button = QPushButton("Apply GroupBy and Aggregation")
        apply_button.clicked.connect(self.apply_groupby)
        layout.addWidget(apply_button)

        export_button = QPushButton("Export Result to CSV")
        export_button.clicked.connect(self.export_result)
        layout.addWidget(export_button)

        widget.setLayout(layout)
        self.setCentralWidget(widget)

        # Permanent status label for filtered_df shape (won't be overwritten by showMessage)
        self.shape_label = QLabel("Filtered: 0 rows x 0 cols")
        self.statusBar().addPermanentWidget(self.shape_label)
        self.update_shape_label()

    def show_table_context_menu(self, table, pos):
        menu = QMenu(self)
        copy_action = QAction("Copy All to Clipboard", self)
        copy_action.triggered.connect(lambda: self.copy_result_to_clipboard(table))
        menu.addAction(copy_action)
        menu.exec(table.viewport().mapToGlobal(pos))

    def validation(self):
        if self.filtered_df.empty:
            QMessageBox.warning(self, "Validation", "No data is loaded.")
            return

        self.valid_table.setRowCount(len(self.filtered_df.columns))
        header = ["Column", "Data Type", "Unique Values", "Missing Values", "Duplicated Values", "Min", "Max", "Sum", "Mean"]
        self.valid_table.setColumnCount(len(header))
        self.valid_table.setHorizontalHeaderLabels(header)

        for row_idx, col in enumerate(self.filtered_df.columns):
            series = self.filtered_df[col]
            missing = series.isna().sum()
            unique = series.nunique()
            duplicated = len(series) - unique - missing
            self.valid_table.setItem(row_idx, 0, QTableWidgetItem(col))
            self.valid_table.setItem(row_idx, 1, QTableWidgetItem(str(self.filtered_df[col].dtype)))
            self.valid_table.setItem(row_idx, 2, QTableWidgetItem(str(unique)))
            self.valid_table.setItem(row_idx, 3, QTableWidgetItem(str(missing)))
            self.valid_table.setItem(row_idx, 4, QTableWidgetItem(str(duplicated)))

            if pd.api.types.is_numeric_dtype(self.filtered_df[col]):
                self.valid_table.setItem(row_idx, 5, QTableWidgetItem(str(self.filtered_df[col].min())))
                self.valid_table.setItem(row_idx, 6, QTableWidgetItem(str(self.filtered_df[col].max())))
                self.valid_table.setItem(row_idx, 7, QTableWidgetItem(str(self.filtered_df[col].sum())))
                self.valid_table.setItem(row_idx, 8, QTableWidgetItem(str(self.filtered_df[col].mean())))
            else:
                self.valid_table.setItem(row_idx, 5, QTableWidgetItem("N/A"))
                self.valid_table.setItem(row_idx, 6, QTableWidgetItem("N/A"))
                self.valid_table.setItem(row_idx, 7, QTableWidgetItem("N/A"))
                self.valid_table.setItem(row_idx, 8, QTableWidgetItem("N/A"))

        self.valid_table.resizeColumnsToContents()

    def merge_files(self):
        if len(self.dataframes) == 0:
            QMessageBox.warning(self, "Merge Error", "Please select at least one file to merge or load.")
            return
        elif len(self.dataframes) == 1:
            self.statusBar().showMessage(f"Only one file is selected. Load the file instead.", 5000)

            self.filtered_df = self.dataframes[0]
            self.merged_df = self.dataframes[0]
        else:
            # when merge multiple files, always use the base_key = the first file's keys
            merge_type = self.merge_type_combo.currentText()
            self.merged_df = self.dataframes[0]
            base_key = self.file_configs[0]["keys"]

            try:
                for i in range(1, len(self.dataframes)):
                    df = self.dataframes[i]
                    keys = self.file_configs[i]["keys"]
                    self.merged_df = pd.merge(self.merged_df, df, left_on=base_key, right_on = keys, how=merge_type)
                    self.filtered_df = self.merged_df
            except Exception as e:
                QMessageBox.critical(self, "Merge Error", str(e))
                return
            
        self.update_column_selection()
        self.populate_raw_table()
        self.update_shape_label()
        self.statusBar().showMessage(f"Merge/Load Successfully.", 5000)

    def apply_filter(self):
        # Apply filter to self.merged_df and update self.filtered_df
        # then refresh raw_table display
        # only use ' ' (single quote) for string values in filter expression
        filter_str = self.filter_input.text().strip()

        try:
            if filter_str:
                self.filtered_df = self.merged_df.query(filter_str)
            else:
                self.filtered_df = self.merged_df
            self.raw_table.setRowCount(min(100, self.filtered_df.shape[0]))
            self.raw_table.setColumnCount(self.filtered_df.shape[1])
            self.raw_table.setHorizontalHeaderLabels(self.filtered_df.columns)

            for row in range(min(100, self.filtered_df.shape[0])):
                for col in range(self.filtered_df.shape[1]):
                    val = self.filtered_df.iat[row, col]
                    item = NumericTableWidgetItem(str(val))
                    self.raw_table.setItem(row, col, item)
            self.update_shape_label()

        except Exception as e:
            QMessageBox.critical(self, "Filter Error", str(e))

    def copy_result_to_clipboard(self, table):
        rows = table.rowCount()
        cols = table.columnCount()

        # Include header row
        headers = [table.horizontalHeaderItem(i).text() for i in range(cols)]
        text = "\t".join(headers) + "\n"

        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = table.item(row, col)
                row_data.append(item.text() if item else "")
            text += "\t".join(row_data) + "\n"

        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copied", "All data copied to clipboard including headers.")

    def update_shape_label(self):
        """Update the permanent status bar label showing filtered_df shape."""
        try:
            if hasattr(self, "filtered_df") and not self.filtered_df.empty:
                r, c = self.filtered_df.shape
            else:
                r, c = 0, 0
        except Exception:
            r, c = 0, 0
        self.shape_label.setText(f"Filtered: {r} rows x {c} cols")
        

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Data Files (*.csv *.txt *.*)")
        if not file_path:
            return
        dialog = FileConfigDialog(file_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            if not config["keys"]:
                self.statusBar().showMessage("You must select at least one primary key!", 5000)
                return
            self.file_configs.append(config)
            df = pd.read_csv(config["path"], sep=config["sep"])
            self.dataframes.append(df)
            self.file_list_widget.addItem(f"{file_path} | Keys: {', '.join(config['keys'])} | Sep: '{config['sep']}'")

    def update_column_selection(self):
        self.groupby_list.clear()
        self.agg_combos.clear()
        # Clear existing form rows
        while self.agg_form.rowCount() > 0:
            self.agg_form.removeRow(0)

        if self.filtered_df.empty:
            return

        # populate groupby_list and agg_form
        for col in self.filtered_df.columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
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
        self.update_shape_label()

    def apply_groupby(self):
        if self.filtered_df.empty:
            QMessageBox.warning(self, "GroupBy", "No data is selected.")
            return

        groupby_cols = [self.groupby_list.item(i).text()
                        for i in range(self.groupby_list.count())
                        if self.groupby_list.item(i).checkState() == Qt.CheckState.Checked]

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
            if not groupby_cols: # if no groupby columns are selected. aggregate all
                grouped_df = self.filtered_df.agg(agg_dict).to_frame().T
            else:
                grouped_df = self.filtered_df.groupby(groupby_cols).agg(agg_dict).reset_index()
        except Exception as e:
            QMessageBox.critical(self, "Aggregation Error", str(e))
            return

        # load aggregated result to result_table
        self.result_table.setRowCount(grouped_df.shape[0])
        self.result_table.setColumnCount(grouped_df.shape[1])
        self.result_table.setHorizontalHeaderLabels(grouped_df.columns)

        for row in range(grouped_df.shape[0]):
            for col in range(grouped_df.shape[1]):
                val = grouped_df.iat[row, col]
                item = NumericTableWidgetItem(str(val))
                self.result_table.setItem(row, col, item)

    def export_merged_results(self):
        if self.filtered_df.empty:
            QMessageBox.warning(self, "Export Failed", "No data to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Merged CSV", "", "CSV Files (*.csv)")
        if file_path:
            self.filtered_df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Export Successful", f"Merged file saved to:\n{file_path}")

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

class FileConfigDialog(QDialog):
    def __init__(self, file_path):
        super().__init__()
        self.setWindowTitle(f"Configure {file_path}")
        self.file_path = file_path
        self.selected_keys = []
        self.selected_sep = ','

        layout = QVBoxLayout()

        # separator selection
        layout.addWidget(QLabel("Select Separator:"))
        self.sep_combo = QComboBox()
        self.sep_combo.addItems([",", ";", "Space", "\\t (Tab)"])
        layout.addWidget(self.sep_combo)

        # Load columns button
        self.load_cols_btn = QPushButton("Load Columns")
        layout.addWidget(self.load_cols_btn)

        # Primary key input with checkboxes
        layout.addWidget(QLabel("Enter Primary Key(s):"))
        self.key_list = QListWidget()
        layout.addWidget(self.key_list)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

        # Signals
        self.load_cols_btn.clicked.connect(self.load_columns)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.key_list.itemChanged.connect(self.update_highlight)

    def load_columns(self):
        sep_text = self.sep_combo.currentText()
        if sep_text.startswith("\\t"):
            sep = "\t"
        elif sep_text == "Space":
            sep = " " 
        else:
            sep = sep_text
            
        try:
            df = pd.read_csv(self.file_path, sep=sep, nrows=1000)
        except Exception as e:
            self.key_list.clear()
            self.key_list.addItem(f"Error reading file: {e}")
            return
        self.key_list.clear()
        for col in df.columns:
            item = QListWidgetItem(col)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.key_list.addItem(item)

    def update_highlight(self, item):
        ''' Highlight selected items '''
        for i in range(self.key_list.count()):
            item = self.key_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                item.setBackground(QBrush(QColor("lightblue")))
            else:
                item.setBackground(QBrush(Qt.GlobalColor.white))

    def get_config(self):
        sep_text = self.sep_combo.currentText()
        self.selected_sep = "\t" if sep_text.startswith("\\t") else " " if sep_text == "Space" else sep_text
        self.selected_keys = [self.key_list.item(i).text()
                              for i in range(self.key_list.count())
                              if self.key_list.item(i).checkState() == Qt.CheckState.Checked]
        return {"path": self.file_path, "sep": self.selected_sep, "keys": self.selected_keys}

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CSVAnalyzer()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())
