from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QHeaderView, QMessageBox)
from database import Session, Inventory

class InventoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(); self.setLayout(layout)
        self.table = QTableWidget(); self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Item Name", "Available Qty"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        btn_del = QPushButton("Delete Selected Item"); btn_del.clicked.connect(self.delete_item)
        layout.addWidget(btn_del)

    def load_data(self):
        session = Session()
        inv = session.query(Inventory).all()
        self.table.setRowCount(0)
        for i in inv:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(i.id)))
            self.table.setItem(r, 1, QTableWidgetItem(i.item_name))
            self.table.setItem(r, 2, QTableWidgetItem(str(i.quantity)))
        session.close()

    def delete_item(self):
        row = self.table.currentRow()
        if row == -1: return
        if QMessageBox.question(self, "Confirm", "Delete?") == QMessageBox.StandardButton.Yes:
            iid = self.table.item(row, 0).text()
            session = Session()
            session.query(Inventory).filter_by(id=iid).delete()
            session.commit(); session.close(); self.load_data()