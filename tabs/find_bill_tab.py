import os
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence
from database import Session, Sale, get_current_business_details
from modules.pdf_generator import generate_bill_pdf
from sqlalchemy import func
from datetime import datetime

class FindBillTab(QWidget):
    edit_bill_signal = pyqtSignal(str) 

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        search_layout = QHBoxLayout()
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Bill ID", "Customer Name", "Car Number", "Mobile Number"])
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        btn_search = QPushButton("Search"); btn_search.clicked.connect(self.search_bills)
        self.search_input.returnPressed.connect(self.search_bills)
        
        search_layout.addWidget(QLabel("Search By:"))
        search_layout.addWidget(self.filter_combo)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)

        self.table = QTableWidget(); self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Bill ID", "Date", "Customer", "Car No", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.doubleClicked.connect(self.edit_bill)
        layout.addWidget(self.table)
        
        layout.addWidget(QLabel("(Double-click a bill to Edit in Sell Tab)"))

        actions = QHBoxLayout()
        # "Print Bill" now uses direct printing logic
        btn_print = QPushButton("🖨️ Print Bill"); btn_print.clicked.connect(self.direct_print_bill)
        btn_save_pdf = QPushButton("💾 Save PDF As..."); btn_save_pdf.clicked.connect(self.save_pdf_as)
        btn_edit = QPushButton("✏️ Edit Selected"); btn_edit.clicked.connect(self.edit_bill)
        btn_del = QPushButton("🗑️ Delete Selected"); btn_del.clicked.connect(self.delete_bill)
        
        actions.addWidget(btn_print); actions.addWidget(btn_save_pdf); actions.addWidget(btn_edit); actions.addWidget(btn_del)
        layout.addLayout(actions)
        
        # Add keyboard shortcuts
        save_pdf_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_pdf_shortcut.activated.connect(self.save_pdf_as)
        
        print_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        print_shortcut.activated.connect(self.direct_print_bill)

    def search_bills(self):
        txt = self.search_input.text().strip()
        search_by = self.filter_combo.currentText()
        session = Session()
        query = session.query(Sale)
        
        if txt:
            if search_by == "Bill ID": query = query.filter(Sale.bill_id.contains(txt))
            elif search_by == "Customer Name": query = query.filter(Sale.customer_name.contains(txt))
            elif search_by == "Car Number": query = query.filter(Sale.car_number.contains(txt))
            elif search_by == "Mobile Number": query = query.filter(Sale.mobile_number.contains(txt))
        
        results = query.order_by(Sale.date_time.desc()).limit(50).all()
        self.table.setRowCount(0)
        for s in results:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(s.bill_id))
            self.table.setItem(r, 1, QTableWidgetItem(s.date_time.strftime("%d-%m-%Y")))
            self.table.setItem(r, 2, QTableWidgetItem(s.customer_name))
            self.table.setItem(r, 3, QTableWidgetItem(s.car_number))
            self.table.setItem(r, 4, QTableWidgetItem(str(s.net_total)))
        session.close()

    def get_selected_id(self):
        row = self.table.currentRow()
        if row == -1: return None
        return self.table.item(row, 0).text()

    def _generate_pdf_data(self, bid):
        session = Session()
        sale = session.query(Sale).filter_by(bill_id=bid).first()
        data = None; biz = None
        if sale:
            biz = get_current_business_details()
            items = [{'sr_no': i.sr_no, 'item_name': i.item_name, 'quantity': i.quantity, 'rate': i.rate, 'amount': i.amount} for i in sale.items]
            car_num = sale.car_number if sale.car_number else "N/A"
            car_km = sale.car_km if sale.car_km else ""
            data = {'bill_id': sale.bill_id, 'date_time': sale.date_time, 'customer_name': sale.customer_name,
                    'mobile_number': sale.mobile_number, 'car_number': car_num, 'car_km': car_km, 'items': items}
        session.close()
        return data, biz

    def direct_print_bill(self):
        """Generates a TEMP PDF and prints it silently using Edge or PowerShell."""
        bid = self.get_selected_id()
        if not bid: 
            QMessageBox.warning(self, "Select", "Please select a bill.")
            return
            
        data, biz = self._generate_pdf_data(bid)
        if not data: return

        # 1. Generate PDF in TEMP folder
        temp_dir = os.environ['TEMP']
        temp_pdf = os.path.join(temp_dir, f"Print_{bid}.pdf")
        generate_bill_pdf(data, biz, temp_pdf)
        
        # 2. Print Logic (From old code)
        try:
            # Try MS Edge silent print
            edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            if not os.path.exists(edge_path):
                edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            
            if os.path.exists(edge_path):
                subprocess.run([edge_path, "--print-to-default", temp_pdf], check=True)
                QMessageBox.information(self, "Printing", "Document sent to printer.")
            else:
                # Fallback to Shell Print
                os.startfile(temp_pdf, "print")
                
        except Exception as e:
            # Final fallback: just open it
            os.startfile(temp_pdf)
            print(f"Print Error: {e}")
        finally:
            # Clean up temp PDF
            try:
                os.remove(temp_pdf)
            except:
                pass

    def save_pdf_as(self):
        bid = self.get_selected_id()
        if not bid: return
        data, biz = self._generate_pdf_data(bid)
        if data:
            path, _ = QFileDialog.getSaveFileName(self, "Save Bill PDF", f"Bill_{bid}.pdf", "PDF Files (*.pdf)")
            if path:
                generate_bill_pdf(data, biz, path)
                QMessageBox.information(self, "Success", "PDF Saved Successfully")

    def edit_bill(self):
        bid = self.get_selected_id()
        if bid: self.edit_bill_signal.emit(bid)

    def delete_bill(self):
        bid = self.get_selected_id()
        if not bid: return
        if QMessageBox.question(self, "Confirm", "Delete this bill?") == QMessageBox.StandardButton.Yes:
            session = Session()
            session.query(Sale).filter_by(bill_id=bid).delete()
            session.commit(); session.close()
            self.search_bills()