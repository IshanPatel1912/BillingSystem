from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtGui import QShortcut, QKeySequence
from database import Session, Purchase, PurchaseItem, Inventory
from datetime import datetime

class TrackedItemsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(); self.setLayout(layout)
        
        form = QHBoxLayout()
        self.t_item = QLineEdit(); self.t_item.setPlaceholderText("Item")
        self.t_qty = QLineEdit(); self.t_qty.setPlaceholderText("Qty")
        self.t_rate = QLineEdit(); self.t_rate.setPlaceholderText("Rate")
        add_btn = QPushButton("Add"); add_btn.clicked.connect(self.add_row)
        form.addWidget(self.t_item); form.addWidget(self.t_qty); form.addWidget(self.t_rate); form.addWidget(add_btn)
        layout.addLayout(form)

        self.table = QTableWidget(); self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Item", "Qty", "Rate", "Amount"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.cellChanged.connect(self.on_cell_change)
        layout.addWidget(self.table)

        btns = QHBoxLayout()
        save_btn = QPushButton("Save & Update Inventory"); save_btn.clicked.connect(self.save_tracked)
        
        # Add Ctrl+S shortcut for save tracked items
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_tracked)
        
        del_btn = QPushButton("Delete Selected"); del_btn.clicked.connect(self.delete_row)
        clr_btn = QPushButton("Clear List"); clr_btn.clicked.connect(lambda: self.table.setRowCount(0))
        btns.addWidget(save_btn); btns.addWidget(del_btn); btns.addWidget(clr_btn)
        layout.addLayout(btns)

    def add_row(self):
        try:
            self.table.blockSignals(True)
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(self.t_item.text()))
            self.table.setItem(r, 1, QTableWidgetItem(self.t_qty.text()))
            self.table.setItem(r, 2, QTableWidgetItem(self.t_rate.text()))
            self.table.setItem(r, 3, QTableWidgetItem(str(float(self.t_qty.text())*float(self.t_rate.text()))))
            self.table.blockSignals(False)
            self.t_item.clear(); self.t_qty.clear(); self.t_rate.clear(); self.t_item.setFocus()
        except: QMessageBox.warning(self, "Error", "Invalid Input")

    def on_cell_change(self, row, column):
        if column in [1, 2]:
            try:
                q_item = self.table.item(row, 1)
                r_item = self.table.item(row, 2)
                
                # FIX: Check if items exist
                if q_item and r_item:
                    q = float(q_item.text() or 0)
                    r = float(r_item.text() or 0)
                    
                    self.table.blockSignals(True)
                    target = self.table.item(row, 3)
                    if target: target.setText(str(q*r))
                    else: self.table.setItem(row, 3, QTableWidgetItem(str(q*r)))
                    self.table.blockSignals(False)
            except: pass

    def delete_row(self):
        if self.table.currentRow() >= 0: self.table.removeRow(self.table.currentRow())

    def save_tracked(self):
        if self.table.rowCount() == 0: return
        session = Session()
        try:
            total = sum(float(self.table.item(r, 3).text()) for r in range(self.table.rowCount()))
            p = Purchase(total_amount=total, date_time=datetime.now(), track_item=True, category="Tracked")
            session.add(p); session.flush()
            for r in range(self.table.rowCount()):
                name = self.table.item(r, 0).text()
                qty = float(self.table.item(r, 1).text())
                rate = float(self.table.item(r, 2).text())
                session.add(PurchaseItem(purchase_id=p.id, item_name=name, quantity=qty, rate=rate, amount=qty*rate, track_item=True))
                inv = session.query(Inventory).filter_by(item_name=name).first()
                if inv: inv.quantity += qty
                else: session.add(Inventory(item_name=name, quantity=qty))
            session.commit(); QMessageBox.information(self, "Success", "Saved"); self.table.setRowCount(0)
        except Exception as e: session.rollback(); QMessageBox.critical(self, "Error", str(e))
        finally: session.close()