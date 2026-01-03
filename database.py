import os
import sys
import bcrypt
import configparser
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# --- CONFIGURATION ---
config = configparser.ConfigParser()
config.read('config.ini')

# --- FIX: SMART DATABASE PATH LOGIC ---
# This ensures the database is saved in a writable location (AppData)
# instead of the "Program Files" folder where it gets blocked.
APP_NAME = "BillingSystem"

# Get the standard AppData folder (e.g., C:\Users\Name\AppData\Roaming\BillingSystem)
if sys.platform == 'win32':
    app_data_dir = os.path.join(os.environ['APPDATA'], APP_NAME)
else:
    app_data_dir = os.path.join(os.path.expanduser('~'), '.' + APP_NAME)

# Create the folder if it doesn't exist
if not os.path.exists(app_data_dir):
    os.makedirs(app_data_dir)

# Define the full path for the database
DATABASE_PATH = os.path.join(app_data_dir, 'billing_data.db')

# Print for debugging (optional, helps see where DB is going)
print(f"Database location: {DATABASE_PATH}")

Base = declarative_base()

# --- MODELS (No Changes Here) ---
class Sale(Base):
    __tablename__ = 'sales'
    bill_id = Column(String, primary_key=True)
    date_time = Column(DateTime, default=datetime.now)
    customer_name = Column(String, nullable=True, index=True)
    mobile_number = Column(String, nullable=True, index=True)
    car_number = Column(String, nullable=True)
    car_model = Column(String, nullable=True)
    car_km = Column(String, nullable=True)
    subtotal = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    net_total = Column(Float, default=0.0)
    paid_status = Column(Boolean, default=False)
    is_edited = Column(Boolean, default=False)
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = 'sale_items'
    id = Column(Integer, primary_key=True)
    sale_bill_id = Column(String, ForeignKey('sales.bill_id'))
    sr_no = Column(Integer)
    item_name = Column(String)
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    sale = relationship("Sale", back_populates="items")

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime, default=datetime.now)
    total_amount = Column(Float, default=0.0)
    track_item = Column(Boolean, default=False)
    category = Column(String, nullable=True)
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = 'purchase_items'
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey('purchases.id'))
    sr_no = Column(Integer, nullable=True)
    item_name = Column(String)
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    category = Column(String, nullable=True)
    track_item = Column(Boolean, default=False)
    purchase = relationship("Purchase", back_populates="items")

class Expenditure(Base):
    __tablename__ = 'expenditures'
    id = Column(Integer, primary_key=True)
    date_time = Column(DateTime, default=datetime.now)
    sr_no_daily = Column(Integer, nullable=True)
    description = Column(String)
    amount = Column(Float)

class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    item_name = Column(String, unique=True)
    quantity = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class ServiceReminder(Base):
    __tablename__ = 'service_reminders'
    id = Column(Integer, primary_key=True)
    bill_id = Column(String, ForeignKey('sales.bill_id'))
    car_number = Column(String)
    customer_name = Column(String)
    mobile_number = Column(String)
    service_due_date = Column(DateTime)
    is_notified = Column(Boolean, default=False)

class BusinessDetail(Base):
    __tablename__ = 'business_details'
    id = Column(Integer, primary_key=True)
    name = Column(String, default="Your Business Name")
    address = Column(String, default="123 Business Street, City")
    phone = Column(String, default="+1234567890")
    owner_name = Column(String, default="Owner Name")
    logo_path = Column(String, nullable=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="admin")

# --- DATABASE SETUP ---
def setup_database():
    # Use the new writable path
    engine = create_engine(f'sqlite:///{DATABASE_PATH}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    if session.query(BusinessDetail).count() == 0:
        session.add(BusinessDetail())
    
    if session.query(User).count() == 0:
        # Default Admin: admin / admin123
        hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
        admin_user = User(username="admin", password_hash=hashed.decode('utf-8'))
        session.add(admin_user)
        print("Default user created: admin / admin123")

    session.commit()
    session.close()
    return Session, engine

Session, engine = setup_database()

def get_current_business_details():
    session = Session()
    details = session.query(BusinessDetail).first()
    session.close()
    return details