import csv
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog)
from PyQt6.QtGui import QShortcut, QKeySequence
from database import Session, Sale, Purchase, Expenditure
from sqlalchemy import func
from datetime import datetime, date
# Required for PDF Export
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

class PortfolioTab(QWidget):
    def __init__(self):
        super().__init__()
        self.stats = {} # Store calculation results here
        self.init_ui()
        # Auto-calculate "All Time" on startup
        self.calculate("all")

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # --- 1. Time Filters (UI from your uploaded code) ---
        filter_layout = QHBoxLayout()
        btn_today = QPushButton("Today")
        btn_today.clicked.connect(lambda: self.calculate("day"))
        
        btn_month = QPushButton("This Month")
        btn_month.clicked.connect(lambda: self.calculate("month"))
        
        btn_year = QPushButton("This Year")
        btn_year.clicked.connect(lambda: self.calculate("year"))
        
        btn_all = QPushButton("All Time")
        btn_all.clicked.connect(lambda: self.calculate("all"))
        
        filter_layout.addWidget(btn_today)
        filter_layout.addWidget(btn_month)
        filter_layout.addWidget(btn_year)
        filter_layout.addWidget(btn_all)
        layout.addLayout(filter_layout)

        # --- 2. Statistics Labels (UI from your uploaded code) ---
        self.lbl_sales = QLabel("Total Sales: 0.00")
        self.lbl_purch = QLabel("Total Purchases: 0.00")
        self.lbl_exp = QLabel("Total Expenses: 0.00")
        self.lbl_profit = QLabel("Net Profit: 0.00")
        
        # Apply Big Font Style
        font = self.lbl_sales.font()
        font.setPointSize(16)
        font.setBold(True)
        
        for l in [self.lbl_sales, self.lbl_purch, self.lbl_exp, self.lbl_profit]:
            l.setFont(font)
            layout.addWidget(l)

        # --- 3. Recalculate Button ---
        btn_recalc = QPushButton("🔄 Recalculate Stats")
        btn_recalc.clicked.connect(lambda: self.calculate("all"))
        layout.addWidget(btn_recalc)
        
        layout.addStretch()

        # --- 4. Export Buttons (Combined Old & New Features) ---
        export_layout = QHBoxLayout()
        
        # CSV Export (From your uploaded code)
        btn_csv = QPushButton("📄 Export Report (CSV)")
        btn_csv.clicked.connect(self.export_csv)
        
        # PDF Export (Requested Feature)
        btn_pdf = QPushButton("📑 Export Report (PDF)")
        btn_pdf.setStyleSheet("background-color: #d83b01; color: white; font-weight: bold;")
        btn_pdf.clicked.connect(self.export_pdf)
        
        # Add Ctrl+S shortcut for export PDF
        export_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        export_shortcut.activated.connect(self.export_pdf)
        
        export_layout.addWidget(btn_csv)
        export_layout.addWidget(btn_pdf)
        layout.addLayout(export_layout)

    def calculate(self, period):
        session = Session()
        q_s = session.query(func.sum(Sale.net_total))
        q_p = session.query(func.sum(Purchase.total_amount))
        q_e = session.query(func.sum(Expenditure.amount))
        
        now = datetime.now()
        start_dt = None
        
        # Date Logic
        if period == "day": 
            start_dt = datetime(now.year, now.month, now.day)
        elif period == "month": 
            start_dt = datetime(now.year, now.month, 1)
        elif period == "year": 
            start_dt = datetime(now.year, 1, 1)
        
        # Apply Filters
        if start_dt:
            q_s = q_s.filter(Sale.date_time >= start_dt)
            q_p = q_p.filter(Purchase.date_time >= start_dt)
            q_e = q_e.filter(Expenditure.date_time >= start_dt)

        # Fetch Data (Handle None if DB is empty)
        s = q_s.scalar() or 0.0
        p = q_p.scalar() or 0.0
        e = q_e.scalar() or 0.0
        session.close()
        
        profit = s - p - e
        
        # Update UI
        self.lbl_sales.setText(f"Total Sales: {s:,.2f}")
        self.lbl_purch.setText(f"Total Purchases: {p:,.2f}")
        self.lbl_exp.setText(f"Total Expenses: {e:,.2f}")
        self.lbl_profit.setText(f"Net Profit: {profit:,.2f}")
        
        # Set Color for Profit
        if profit >= 0:
            self.lbl_profit.setStyleSheet("color: green")
        else:
            self.lbl_profit.setStyleSheet("color: red")
        
        # Save for Export
        self.stats = {
            'sales': s, 
            'purchase': p, 
            'expense': e, 
            'profit': profit, 
            'period': period
        }

    def export_csv(self):
        if not self.stats: 
            QMessageBox.warning(self, "Error", "Please calculate stats first.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "Portfolio_Report.csv", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Metric", "Amount"])
                    writer.writerow(["Period", self.stats.get('period', 'Unknown')])
                    writer.writerow(["Total Sales", self.stats['sales']])
                    writer.writerow(["Total Purchases", self.stats['purchase']])
                    writer.writerow(["Total Expenses", self.stats['expense']])
                    writer.writerow(["Net Profit", self.stats['profit']])
                QMessageBox.information(self, "Success", "CSV Report Exported Successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def export_pdf(self):
        if not self.stats: 
            self.calculate("all")
        
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "Portfolio_Report.pdf", "PDF Files (*.pdf)")
        if path:
            try:
                c = canvas.Canvas(path, pagesize=A4)
                
                # Title
                c.setFont("Helvetica-Bold", 16)
                c.drawString(100, 800, "Business Portfolio Report")
                
                c.setFont("Helvetica", 12)
                c.drawString(100, 780, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
                c.drawString(100, 765, f"Period: {self.stats.get('period', 'All Time').capitalize()}")
                
                # Line
                c.line(100, 755, 500, 755)
                
                # Stats
                c.setFont("Helvetica", 14)
                c.drawString(100, 730, f"Total Sales:       {self.stats['sales']:,.2f}")
                c.drawString(100, 710, f"Total Purchases:   {self.stats['purchase']:,.2f}")
                c.drawString(100, 690, f"Total Expenses:    {self.stats['expense']:,.2f}")
                
                # Profit Highlight
                c.setFont("Helvetica-Bold", 14)
                if self.stats['profit'] >= 0:
                    c.setFillColorRGB(0, 0.5, 0) # Green
                else:
                    c.setFillColorRGB(0.8, 0, 0) # Red
                    
                c.drawString(100, 660, f"Net Profit:        {self.stats['profit']:,.2f}")
                
                c.save()
                QMessageBox.information(self, "Success", "PDF Report Exported Successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))