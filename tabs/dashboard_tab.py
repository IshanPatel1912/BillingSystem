from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QGroupBox)
from datetime import datetime
from database import Session, Sale, Purchase, Expenditure
from sqlalchemy import func
from sqlalchemy.orm import joinedload

class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(); self.setLayout(layout)
        
        self.lbl_today = QLabel(f"Dashboard - {datetime.now().strftime('%d-%m-%Y')}")
        layout.addWidget(self.lbl_today)
        self.stats_label = QLabel("Loading..."); layout.addWidget(self.stats_label)
        
        grp_p = QGroupBox("Today's Itemized Purchases")
        v1 = QVBoxLayout()
        self.table_p = QTableWidget(); self.table_p.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_p.setColumnCount(3); self.table_p.setHorizontalHeaderLabels(["Time", "Item Name", "Amount"])
        self.table_p.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        v1.addWidget(self.table_p)
        grp_p.setLayout(v1)
        layout.addWidget(grp_p)
        
        grp_e = QGroupBox("Today's Expenses")
        v2 = QVBoxLayout()
        self.table_e = QTableWidget(); self.table_e.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_e.setColumnCount(2); self.table_e.setHorizontalHeaderLabels(["Description", "Amount"])
        self.table_e.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        v2.addWidget(self.table_e)
        grp_e.setLayout(v2)
        layout.addWidget(grp_e)

        self.refresh_data()

    def refresh_data(self):
        session = Session()
        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')
        
        total = session.query(func.sum(Sale.net_total)).filter(func.date(Sale.date_time) == today_str).scalar() or 0
        count = session.query(Sale).filter(func.date(Sale.date_time) == today_str).count()
        self.stats_label.setText(f"Today's Sales: {count} | Revenue: {total}")
        
        purchases = session.query(Purchase).options(joinedload(Purchase.items)).filter(func.date(Purchase.date_time) == today_str).all()
        self.table_p.setRowCount(0)
        for p in purchases:
            time_str = p.date_time.strftime("%H:%M")
            for item in p.items:
                r = self.table_p.rowCount(); self.table_p.insertRow(r)
                self.table_p.setItem(r, 0, QTableWidgetItem(time_str))
                self.table_p.setItem(r, 1, QTableWidgetItem(item.item_name))
                self.table_p.setItem(r, 2, QTableWidgetItem(str(item.amount)))
            
        es = session.query(Expenditure).filter(func.date(Expenditure.date_time) == today_str).all()
        self.table_e.setRowCount(0)
        for e in es:
            r = self.table_e.rowCount(); self.table_e.insertRow(r)
            self.table_e.setItem(r, 0, QTableWidgetItem(e.description))
            self.table_e.setItem(r, 1, QTableWidgetItem(str(e.amount)))
        session.close()