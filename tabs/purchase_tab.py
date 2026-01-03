from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
                             QGroupBox, QDialog, QFormLayout)
from PyQt6.QtGui import QShortcut, QKeySequence, QDoubleValidator
from PyQt6.QtCore import Qt
from database import Session, Purchase, PurchaseItem, Inventory
from datetime import datetime

class PurchaseTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_history()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # ==========================================
        # SECTION 1: ADD GENERAL PURCHASE
        # ==========================================
        group_new = QGroupBox("Add General Purchase (Expenses Only - NO Inventory Update)")
        group_new.setStyleSheet("QGroupBox { font-weight: bold; color: #d83b01; }")
        layout_new = QVBoxLayout()
        
        # Input Form
        form = QHBoxLayout()
        self.p_item = QLineEdit()
        self.p_item.setPlaceholderText("Item Description")
        self.p_qty = QLineEdit()
        self.p_qty.setPlaceholderText("Qty")
        # Add validator for quantity (positive numbers only)
        qty_validator = QDoubleValidator(0.0, 999999.0, 2)
        qty_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.p_qty.setValidator(qty_validator)
        
        self.p_rate = QLineEdit()
        self.p_rate.setPlaceholderText("Rate")
        # Add validator for rate (non-negative numbers)
        rate_validator = QDoubleValidator(0.0, 999999.0, 2)
        rate_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.p_rate.setValidator(rate_validator)
        
        add_btn = QPushButton("Add to List")
        add_btn.clicked.connect(self.add_row)
        
        # Enter key support removed to avoid validation issues
        
        form.addWidget(QLabel("Item:")); form.addWidget(self.p_item)
        form.addWidget(QLabel("Qty:")); form.addWidget(self.p_qty)
        form.addWidget(QLabel("Rate:")); form.addWidget(self.p_rate)
        form.addWidget(add_btn)
        layout_new.addLayout(form)

        # Temporary Table
        self.table_temp = QTableWidget()
        self.table_temp.setColumnCount(4)
        self.table_temp.setHorizontalHeaderLabels(["Item", "Qty", "Rate", "Amount"])
        self.table_temp.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_temp.setFixedHeight(150)
        
        # LIVE RECALCULATION (With Safety Fix)
        self.table_temp.cellChanged.connect(self.on_cell_change)
        
        layout_new.addWidget(self.table_temp)

        # Save Button
        save_btn = QPushButton("Save General Purchase")
        save_btn.setStyleSheet("background-color: #d83b01; color: white; padding: 10px;")
        save_btn.clicked.connect(self.save_purchase)
        
        # Add Ctrl+S shortcut for save purchase
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_purchase)
        
        layout_new.addWidget(save_btn)
        
        group_new.setLayout(layout_new)
        layout.addWidget(group_new)

        # ==========================================
        # SECTION 2: PURCHASE HISTORY
        # ==========================================
        group_hist = QGroupBox("Purchase History")
        layout_hist = QVBoxLayout()
        
        # Filters
        filter_layout = QHBoxLayout()
        self.date_filter = QLineEdit()
        self.date_filter.setPlaceholderText("DD-MM-YYYY")
        
        btn_filter = QPushButton("Filter Date")
        btn_filter.clicked.connect(self.load_history)
        
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(lambda: [self.date_filter.clear(), self.load_history()])
        
        filter_layout.addWidget(QLabel("Date Filter:"))
        filter_layout.addWidget(self.date_filter)
        filter_layout.addWidget(btn_filter)
        filter_layout.addWidget(btn_clear)
        layout_hist.addLayout(filter_layout)

        # History Table
        self.table_hist = QTableWidget()
        self.table_hist.setColumnCount(7) # ID, Date, Item, Qty, Rate, Amt, Type
        self.table_hist.setHorizontalHeaderLabels(["ID", "Date", "Item Name", "Qty", "Rate", "Amount", "Type"])
        self.table_hist.hideColumn(0) # Hide ID
        self.table_hist.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        # Double Click to Edit
        self.table_hist.doubleClicked.connect(self.edit_history_item)
        
        layout_hist.addWidget(self.table_hist)
        
        # Delete Button
        btn_del = QPushButton("Delete Selected History Item")
        btn_del.clicked.connect(self.delete_history_item)
        layout_hist.addWidget(btn_del)

        group_hist.setLayout(layout_hist)
        layout.addWidget(group_hist)

    # --- METHODS ---

    def add_row(self):
        try:
            name = self.p_item.text().strip()
            qty_text = self.p_qty.text().strip()
            rate_text = self.p_rate.text().strip()
            
            # Silent validation - return if any field is empty
            if not name or not qty_text or not rate_text:
                return
            
            # Try to convert to float with better error handling
            try:
                qty = float(qty_text)
            except ValueError:
                return  # Silent failure
                
            try:
                rate = float(rate_text)
            except ValueError:
                return  # Silent failure
            
            # Business logic validation
            if qty <= 0 or rate < 0:
                return  # Silent failure
            
            amt = qty * rate

            # BLOCK SIGNALS to prevent 'NoneType' crash during row creation
            self.table_temp.blockSignals(True)
            
            r = self.table_temp.rowCount()
            self.table_temp.insertRow(r)
            self.table_temp.setItem(r, 0, QTableWidgetItem(name))
            self.table_temp.setItem(r, 1, QTableWidgetItem(str(qty)))
            self.table_temp.setItem(r, 2, QTableWidgetItem(str(rate)))
            self.table_temp.setItem(r, 3, QTableWidgetItem(f"{amt:.2f}"))
            
            # UNBLOCK SIGNALS
            self.table_temp.blockSignals(False)
            
            self.p_item.clear(); self.p_qty.clear(); self.p_rate.clear(); self.p_item.setFocus()
        except Exception as e:
            # Silent failure for any unexpected errors
            pass

    def on_cell_change(self, row, column):
        # Trigger only if Qty (1) or Rate (2) changes
        if column in [1, 2]:
            try:
                q_item = self.table_temp.item(row, 1)
                r_item = self.table_temp.item(row, 2)
                
                # SAFETY CHECK: Ensure items exist before reading
                if q_item and r_item:
                    qty_text = q_item.text().strip() if q_item.text() else ""
                    rate_text = r_item.text().strip() if r_item.text() else ""
                    
                    if qty_text and rate_text:
                        try:
                            qty = float(qty_text)
                            rate = float(rate_text)
                            
                            if qty <= 0 or rate < 0:
                                return  # Don't update if invalid values
                            
                            amt = qty * rate
                            
                            self.table_temp.blockSignals(True)
                            
                            # Update Amount Cell
                            amt_item = self.table_temp.item(row, 3)
                            if amt_item:
                                amt_item.setText(f"{amt:.2f}")
                            else:
                                self.table_temp.setItem(row, 3, QTableWidgetItem(f"{amt:.2f}"))
                                
                            self.table_temp.blockSignals(False)
                        except ValueError:
                            # Invalid number format, don't update
                            pass
            except Exception:
                # Any other error, don't crash
                pass

    def save_purchase(self):
        if self.table_temp.rowCount() == 0: return
        
        session = Session()
        try:
            total = sum(float(self.table_temp.item(r, 3).text()) for r in range(self.table_temp.rowCount()))
            
            # Logic: track_item=False because this is GENERAL PURCHASE (No Inventory)
            purchase = Purchase(total_amount=total, date_time=datetime.now(), track_item=False, category="General")
            session.add(purchase)
            session.flush()

            for r in range(self.table_temp.rowCount()):
                name = self.table_temp.item(r, 0).text()
                qty = float(self.table_temp.item(r, 1).text())
                rate = float(self.table_temp.item(r, 2).text())
                amt = float(self.table_temp.item(r, 3).text())

                session.add(PurchaseItem(purchase_id=purchase.id, item_name=name, quantity=qty, rate=rate, amount=amt, track_item=False))
                
            session.commit()
            QMessageBox.information(self, "Success", "General Purchase Saved (Inventory NOT Updated)")
            self.table_temp.setRowCount(0)
            self.load_history()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def load_history(self):
        session = Session()
        query = session.query(PurchaseItem).join(Purchase).order_by(Purchase.date_time.desc())
        
        date_str = self.date_filter.text().strip()
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%d-%m-%Y").date()
                query = query.filter(Purchase.date_time >= datetime.combine(dt, datetime.min.time()),
                                     Purchase.date_time <= datetime.combine(dt, datetime.max.time()))
            except: pass
            
        items = query.limit(100).all()
        self.table_hist.setRowCount(0)
        for i in items:
            r = self.table_hist.rowCount()
            self.table_hist.insertRow(r)
            self.table_hist.setItem(r, 0, QTableWidgetItem(str(i.id)))
            self.table_hist.setItem(r, 1, QTableWidgetItem(i.purchase.date_time.strftime("%d-%m-%Y")))
            self.table_hist.setItem(r, 2, QTableWidgetItem(i.item_name))
            self.table_hist.setItem(r, 3, QTableWidgetItem(str(i.quantity)))
            self.table_hist.setItem(r, 4, QTableWidgetItem(str(i.rate)))
            self.table_hist.setItem(r, 5, QTableWidgetItem(str(i.amount)))
            
            type_str = "📦 Tracked" if i.track_item else "📝 General"
            self.table_hist.setItem(r, 6, QTableWidgetItem(type_str))
            
        session.close()

    def edit_history_item(self):
        row = self.table_hist.currentRow()
        if row == -1: return
        item_id = self.table_hist.item(row, 0).text()
        
        # --- Using Dialog for Editing (Like Old Code) ---
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Purchase Item")
        form = QFormLayout(dialog)
        
        e_name = QLineEdit(self.table_hist.item(row, 2).text())
        e_qty = QLineEdit(self.table_hist.item(row, 3).text())
        e_rate = QLineEdit(self.table_hist.item(row, 4).text())
        
        form.addRow("Name:", e_name)
        form.addRow("Qty:", e_qty)
        form.addRow("Rate:", e_rate)
        
        btn_save = QPushButton("Save Changes")
        btn_save.clicked.connect(lambda: dialog.accept())
        form.addWidget(btn_save)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            session = Session()
            try:
                item = session.query(PurchaseItem).filter_by(id=item_id).first()
                if item:
                    old_qty = item.quantity
                    new_qty = float(e_qty.text())
                    
                    item.item_name = e_name.text()
                    item.quantity = new_qty
                    item.rate = float(e_rate.text())
                    item.amount = item.quantity * item.rate
                    
                    # LOGIC: Only update inventory if it was a Tracked Item
                    if item.track_item:
                        inv = session.query(Inventory).filter_by(item_name=item.item_name).first()
                        if inv: 
                            # If new qty is higher, add difference. If lower, subtract difference.
                            inv.quantity += (new_qty - old_qty)
                    
                    # Update Parent Total
                    purch = session.query(Purchase).filter_by(id=item.purchase_id).first()
                    all_items = session.query(PurchaseItem).filter_by(purchase_id=item.purchase_id).all()
                    purch.total_amount = sum(i.amount for i in all_items)
                    
                    session.commit()
                    self.load_history()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
            finally:
                session.close()

    def delete_history_item(self):
        row = self.table_hist.currentRow()
        if row == -1: return
        
        if QMessageBox.question(self, "Confirm", "Delete selected item?") == QMessageBox.StandardButton.Yes:
            item_id = self.table_hist.item(row, 0).text()
            session = Session()
            try:
                item = session.query(PurchaseItem).filter_by(id=item_id).first()
                if item:
                    pid = item.purchase_id
                    
                    # LOGIC: If tracked, revert inventory
                    if item.track_item:
                        inv = session.query(Inventory).filter_by(item_name=item.item_name).first()
                        if inv: inv.quantity -= item.quantity
                    
                    session.delete(item)
                    
                    # Recalculate total
                    all_items = session.query(PurchaseItem).filter_by(purchase_id=pid).all()
                    purch = session.query(Purchase).filter_by(id=pid).first()
                    if purch: purch.total_amount = sum(i.amount for i in all_items)
                    
                    session.commit()
                    self.load_history()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()