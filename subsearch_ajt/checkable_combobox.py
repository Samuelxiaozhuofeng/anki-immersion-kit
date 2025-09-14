# Copyright: Ren Tatsumoto <tatsu at autistici.org>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# Implementations
# https://gis.stackexchange.com/questions/350148/qcombobox-multiple-selection-pyqt5
# https://www.geeksforgeeks.org/pyqt5-checkable-combobox-showing-checked-items-in-textview/

from typing import Any
from collections.abc import Iterable, Collection

from aqt.qt import *

MISSING = object()


class CheckableComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Initial state
        self._opened = False

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        # Make the lineedit the same color as QPushButton
        palette = QApplication.palette()
        palette.setBrush(QPalette.ColorRole.Base, palette.button())
        self.lineEdit().setPalette(palette)

        # Use custom delegate and model
        self.setItemDelegate(QStyledItemDelegate())
        self.setModel(QStandardItemModel(self))

        # when any item get pressed
        qconnect(self.view().pressed, self.handle_item_pressed)

        # Update the text when an item is toggled
        qconnect(self.model().dataChanged, self.update_text)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def handle_item_pressed(self, index):
        """ Check the pressed item if unchecked and vice-versa """
        item: QStandardItem = self.model().itemFromIndex(index)
        item.setCheckState(
            Qt.CheckState.Unchecked
            if item.checkState() == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )

    def resize_event(self, event):
        """ Recompute text to elide as needed """
        self.update_text()
        super().resize_event(event)

    def event_filter(self, obj: QObject, event: QEvent):
        if event.type() == QEvent.Type.MouseButtonRelease:
            if obj == self.lineEdit():
                self.toggle_popup()
                return True
            if obj == self.view().viewport():
                return True
        return False

    def toggle_popup(self):
        return self.hide_popup() if self._opened else self.show_popup()

    def show_popup(self):
        """ When the popup is displayed, a click on the lineedit should close it """
        super().show_popup()
        self._opened = True

    def hide_popup(self):
        super().hide_popup()
        self._opened = False
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.update_text()

    def timer_event(self, event):
        """ After timeout, kill timer, and re-enable click on line-edit """
        self.killTimer(event.timerId())
        self._opened = False

    def update_text(self):
        self.lineEdit().setText(", ".join(self.checked_texts()))

    def add_checkable_text(self, text: str):
        return self.add_checkable_item(text)

    def add_checkable_item(self, text: str, data: Any = MISSING):
        item = QStandardItem()
        item.setText(text)
        item.setCheckable(True)
        item.setEnabled(True)
        item.setCheckState(Qt.CheckState.Unchecked)
        if data is not MISSING:
            item.setData(data)
        self.model().appendRow(item)

    def set_checkable_texts(self, texts: Iterable[str]):
        self.clear()
        for text in texts:
            self.add_checkable_text(text)

    def items(self) -> Iterable[QStandardItem]:
        return (self.model().item(i) for i in range(self.model().rowCount()))

    def checked_items(self) -> Iterable[QStandardItem]:
        return filter(lambda item: item.checkState() == Qt.CheckState.Checked, self.items())

    def checked_data(self) -> Iterable[Any]:
        return map(QStandardItem.data, self.checked_items())

    def checked_texts(self) -> Iterable[str]:
        return map(QStandardItem.text, self.checked_items())

    def set_checked_texts(self, texts: Collection[str]):
        for item in self.items():
            item.setCheckState(Qt.CheckState.Checked if (item.text() in texts) else Qt.CheckState.Unchecked)

    def set_checked_data(self, data_items: Collection[Any]):
        for item in self.items():
            item.setCheckState(Qt.CheckState.Checked if (item.data() in data_items) else Qt.CheckState.Unchecked)


class MainWindowTest(QMainWindow):
    items = (
        "Milk",
        "Eggs",
        "Butter",
        "Cheese",
        "Yogurt",
        "Chicken",
        "Fish",
        "Potatoes",
        "Carrots",
        "Onions",
        "Garlic",
        "Sugar",
        "Salt",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        widget = QWidget()
        main_layout = QVBoxLayout()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        combo_box = CheckableComboBox()
        print_button = QPushButton('Print Values')
        main_layout.addWidget(combo_box)  # type: ignore
        main_layout.addWidget(print_button)  # type: ignore
        combo_box.set_checkable_texts(self.items)
        combo_box.set_checked_texts(self.items[3:6])
        qconnect(print_button.clicked, lambda: print('\n'.join(combo_box.checked_texts())))


def main():
    app = QApplication(sys.argv)
    window = MainWindowTest()
    window.show()
    window.resize(480, 320)
    app.exit(app.exec())


if __name__ == '__main__':
    main()
