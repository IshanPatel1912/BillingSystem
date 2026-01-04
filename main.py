import sys
import os
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QLabel, QDialog, 
                             QLineEdit, QPushButton, QMessageBox, QFormLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt

# Initialize logging as early as possible so other modules can log
from modules.logging_config import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from database import setup_database, Session, User, ServiceReminder, get_current_business_details
from datetime import datetime
import bcrypt
import threading

# Import All Tabs
from tabs.sell_tab import SellTab
from tabs.purchase_tab import PurchaseTab
from tabs.expenditure_tab import ExpenditureTab
from tabs.find_bill_tab import FindBillTab
from tabs.inventory_tab import InventoryTab
from tabs.portfolio_tab import PortfolioTab
from tabs.dashboard_tab import DashboardTab
from tabs.business_detail_tab import BusinessDetailTab
from tabs.tracked_items_tab import TrackedItemsTab

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setFixedSize(300, 150)
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.user = QLineEdit(); self.user.setPlaceholderText("Username")
        self.pwd = QLineEdit(); self.pwd.setPlaceholderText("Password"); self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("User:", self.user)
        form.addRow("Pass:", self.pwd)
        
        btn = QPushButton("Login")
        btn.clicked.connect(self.check_login)
        
        layout.addLayout(form)
        layout.addWidget(btn)
        self.setLayout(layout)

    def check_login(self):
        u = self.user.text()
        p = self.pwd.text()
        session = Session()
        user = session.query(User).filter_by(username=u).first()
        session.close()
        
        if user and bcrypt.checkpw(p.encode(), user.password_hash.encode()):
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid Login")

class ReminderDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Service Reminders Due")
        self.resize(700, 400)
        layout = QVBoxLayout(self)
        
        self.table = QTableWidget(); self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Customer", "Car", "Mobile", "Due Date"])
        self.table.hideColumn(0)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        btns = QHBoxLayout()
        btn_mark = QPushButton("✅ Mark Notified")
        btn_mark.clicked.connect(self.mark_notified)
        
        btn_wa = QPushButton("📤 Send WhatsApp Reminder")
        btn_wa.setStyleSheet("background-color: #25D366; color: white; font-weight: bold;")
        btn_wa.clicked.connect(self.send_wa)
        
        btns.addWidget(btn_mark)
        btns.addWidget(btn_wa)
        layout.addLayout(btns)
        
        self.load_reminders()

    def load_reminders(self):
        session = Session()
        rems = session.query(ServiceReminder).filter(ServiceReminder.service_due_date <= datetime.now(), ServiceReminder.is_notified == False).all()
        self.table.setRowCount(0)
        for r in rems:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(r.id)))
            self.table.setItem(row, 1, QTableWidgetItem(r.customer_name))
            self.table.setItem(row, 2, QTableWidgetItem(r.car_number))
            self.table.setItem(row, 3, QTableWidgetItem(r.mobile_number))
            self.table.setItem(row, 4, QTableWidgetItem(r.service_due_date.strftime("%d-%m-%Y")))
        session.close()

    def mark_notified(self):
        row = self.table.currentRow()
        if row == -1: return
        rid = self.table.item(row, 0).text()
        
        session = Session()
        r = session.query(ServiceReminder).filter_by(id=rid).first()
        if r: 
            r.is_notified = True
            session.commit()
        session.close()
        self.load_reminders()

    def send_wa(self):
        row = self.table.currentRow()
        if row == -1: 
            QMessageBox.warning(self, "Select", "Please select a row first.")
            return
            
        customer_name = self.table.item(row, 1).text()
        car_number = self.table.item(row, 2).text()
        mobile = self.table.item(row, 3).text()
        due_date = self.table.item(row, 4).text()
        rid = self.table.item(row, 0).text()
        
        biz = get_current_business_details()
        biz_name = biz.name if biz else "Service Center"
        country_code = biz.country_code if biz and biz.country_code else "+91"

        message = (f"🔔 Vehicle Service Reminder\n"
                   f"Hello {customer_name},\n"
                   f"This is a reminder that the next service of your vehicle is due.\n"
                   f"🚗 Car Number: {car_number}\n"
                   f"📅 Service Due Date: {due_date}\n"
                   f"Please contact us for booking.\n"
                   f"Thank you!\n"
                   f"– {biz_name}")

        def run():
            try:
                import pywhatkit as kit
                kit.sendwhatmsg_instantly(f"{country_code}{mobile}", message, 15, True, 4)
            except Exception:
                logger.exception("WhatsApp Error while sending reminder to %s", mobile)
        
        threading.Thread(target=run, daemon=True).start()
        
        session = Session()
        r = session.query(ServiceReminder).filter_by(id=rid).first()
        if r: 
            r.is_notified = True
            session.commit()
        session.close()
        
        QMessageBox.information(self, "Sending", "WhatsApp initiated... Please wait for browser.")
        self.load_reminders()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern Billing System")
        self.resize(1200, 800)
        
        self.setStyleSheet("""
            QMainWindow { background-color: #f3f3f3; }
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { background: #ddd; padding: 10px 20px; border-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #0078d4; color: white; font-weight: bold; }
            QLineEdit, QTableWidget { border: 1px solid #ccc; padding: 5px; }
            QComboBox { padding: 5px; }
        """)

        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("Billing & Inventory System"))
        self.btn_bell = QPushButton("🔔 Reminders")
        self.btn_bell.setStyleSheet("background-color: #ffcccb; font-weight: bold; padding: 5px 15px;")
        self.btn_bell.clicked.connect(self.show_reminders)
        header.addStretch()
        header.addWidget(self.btn_bell)
        layout.addLayout(header)
        
        self.tabs = QTabWidget()
        
        self.tab_sell = SellTab()
        self.tab_purchase = PurchaseTab()
        self.tab_expense = ExpenditureTab()
        self.tab_find = FindBillTab()
        self.tab_inventory = InventoryTab()
        self.tab_tracked = TrackedItemsTab()
        self.tab_portfolio = PortfolioTab()
        self.tab_dash = DashboardTab()
        self.tab_biz = BusinessDetailTab()

        self.tab_find.edit_bill_signal.connect(self.open_edit_bill)

        self.tabs.addTab(self.tab_sell, "💰 Sell")
        self.tabs.addTab(self.tab_purchase, "🛒 Purchase")
        self.tabs.addTab(self.tab_expense, "💸 Expenditure")
        self.tabs.addTab(self.tab_find, "🔍 Find Bill")
        self.tabs.addTab(self.tab_tracked, "📋 Tracked Items")
        self.tabs.addTab(self.tab_inventory, "📦 Inventory")
        self.tabs.addTab(self.tab_portfolio, "📊 Portfolio")
        self.tabs.addTab(self.tab_dash, "🏠 Dashboard")
        self.tabs.addTab(self.tab_biz, "⚙️ Settings")
        
        layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_change)
        self.check_reminders()

    def keyPressEvent(self, event):
        current_tab = self.tabs.currentWidget()
        
        # --- F5 KEY LOGIC ---
        if event.key() == Qt.Key.Key_F5:
            if current_tab == self.tab_sell:
                self.tab_sell.reset_form()
            elif current_tab == self.tab_expense:
                self.tab_expense.load_data()
            elif current_tab == self.tab_tracked:
                self.tab_tracked.clear_list()
            elif current_tab == self.tab_portfolio:
                self.tab_portfolio.calculate("all")
            else:
                # Default refresh for other tabs
                if hasattr(current_tab, 'load_data'): current_tab.load_data()
                elif hasattr(current_tab, 'refresh_data'): current_tab.refresh_data()
                elif hasattr(current_tab, 'load_history'): current_tab.load_history()
        
        # --- DELETE KEY LOGIC ---
        elif event.key() == Qt.Key.Key_Delete:
            if current_tab == self.tab_sell:
                self.tab_sell.delete_item()
            elif current_tab == self.tab_purchase:
                self.tab_purchase.delete_history_item()
            elif current_tab == self.tab_expense:
                self.tab_expense.delete_selected()
            elif current_tab == self.tab_find:
                self.tab_find.delete_bill()
            elif current_tab == self.tab_tracked:
                self.tab_tracked.delete_row()
            elif current_tab == self.tab_inventory:
                self.tab_inventory.delete_item()

        # --- ENTER KEY LOGIC (Existing) ---
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if hasattr(current_tab, 'add_item'): current_tab.add_item()
            elif hasattr(current_tab, 'add_row'): current_tab.add_row()
            elif hasattr(current_tab, 'save_expense'): current_tab.save_expense()
            elif hasattr(current_tab, 'search_bills'): current_tab.search_bills()
            
        super().keyPressEvent(event)

    def refresh_current_tab(self):
        # Helper for generic refresh logic
        w = self.tabs.currentWidget()
        if hasattr(w, 'refresh_data'): w.refresh_data()
        elif hasattr(w, 'load_data'): w.load_data()
        elif hasattr(w, 'load_history'): w.load_history()
        elif hasattr(w, 'search_bills'): w.search_bills()
        self.check_reminders()

    def open_edit_bill(self, bill_id):
        self.tabs.setCurrentWidget(self.tab_sell)
        self.tab_sell.load_bill_for_edit(bill_id)

    def on_tab_change(self, index):
        self.refresh_current_tab()

    def show_reminders(self):
        ReminderDialog(self).exec()
        self.check_reminders()

    def check_reminders(self):
        session = Session()
        count = session.query(ServiceReminder).filter(ServiceReminder.service_due_date <= datetime.now(), ServiceReminder.is_notified == False).count()
        session.close()
        self.btn_bell.setText(f"🔔 Reminders ({count})")
        if count > 0:
            self.btn_bell.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold; padding: 5px 15px; border-radius: 4px;")
        else:
            self.btn_bell.setStyleSheet("background-color: #e0e0e0; color: #333; padding: 5px 15px; border-radius: 4px;")

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        setup_database()

        if LoginDialog().exec() == QDialog.DialogCode.Accepted:
            win = MainWindow()
            win.showMaximized() # FULL DESKTOP MODE
            sys.exit(app.exec())
    except Exception:
        logger.exception('Unhandled exception in application')
        raise