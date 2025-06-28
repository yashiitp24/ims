import sqlite3
from datetime import datetime

DB_NAME = "inventory.db"
LOGIN_DB = "LoginData.db"

# Create the inventory table if it doesn’t already exist
def init_inventory_table():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

# Create the sales table to track transactions
def init_sales_table():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            total_amount REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

# Create the receipts table for storing each complete bill
def init_receipts_table():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL NOT NULL,
            contact_number TEXT,
            date TEXT,
            time TEXT,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

# Create a table to hold each item entry linked to a receipt
def init_receipt_items_table():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        CREATE TABLE IF NOT EXISTS receipt_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            price_per_unit REAL,
            subtotal REAL,
            FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id)
        )
    """)
    conn.commit()
    conn.close()

# Set up the USERS table for login and profile data
def init_users_table():
    conn = sqlite3.connect(LOGIN_DB)
    cr = conn.cursor()
    cr.execute("""
        CREATE TABLE IF NOT EXISTS USERS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            contact TEXT
        )
    """)
    conn.commit()
    conn.close()

# Add contact column to USERS if it's missing (for backward compatibility)
def add_contact_column():
    conn = sqlite3.connect(LOGIN_DB)
    cr = conn.cursor()
    try:
        cr.execute("ALTER TABLE USERS ADD COLUMN contact TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Already exists
    conn.close()

# Add user_id column to sales table if not already there
def add_user_id_column_to_sales():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("PRAGMA table_info(sales)")
    columns = [col[1] for col in cr.fetchall()]
    if 'user_id' not in columns:
        cr.execute("ALTER TABLE sales ADD COLUMN user_id INTEGER")
    conn.commit()
    conn.close()

# Add user_id column to inventory table if not already present
def add_user_id_column_to_inventory():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("PRAGMA table_info(inventory)")
    columns = [col[1] for col in cr.fetchall()]
    if 'user_id' not in columns:
        cr.execute("ALTER TABLE inventory ADD COLUMN user_id INTEGER")
    conn.commit()
    conn.close()

# ========== INVENTORY FUNCTIONS ==========

def get_all_items():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT * FROM inventory")
    items = cr.fetchall()
    conn.close()
    return items

def get_items_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT * FROM inventory WHERE user_id = ?", (user_id,))
    items = cr.fetchall()
    conn.close()
    return items

def add_item(name, qty, price, user_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("INSERT INTO inventory (name, quantity, price, user_id) VALUES (?, ?, ?, ?)", (name, qty, price, user_id))
    conn.commit()
    conn.close()

def delete_item(product_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("DELETE FROM inventory WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

def get_item_by_product_id(product_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT * FROM inventory WHERE product_id = ?", (product_id,))
    item = cr.fetchone()
    conn.close()
    return item

def update_item(product_id, name, qty, price):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("UPDATE inventory SET name = ?, quantity = ?, price = ? WHERE product_id = ?", (name, qty, price, product_id))
    conn.commit()
    conn.close()

def get_item_by_name(name):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT * FROM inventory WHERE name = ?", (name,))
    item = cr.fetchone()
    conn.close()
    return item

def reduce_product_quantity(product_name, quantity_to_reduce):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT quantity FROM inventory WHERE name = ?", (product_name,))
    result = cr.fetchone()
    if result:
        current_qty = result[0]
        new_qty = max(current_qty - quantity_to_reduce, 0)
        cr.execute("UPDATE inventory SET quantity = ? WHERE name = ?", (new_qty, product_name))
    conn.commit()
    conn.close()

# ========== SALES FUNCTIONS ==========

def add_sale(product_name, quantity, price_per_unit, total_amount, user_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        INSERT INTO sales (product_name, quantity, price_per_unit, total_amount, timestamp, user_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (product_name, quantity, price_per_unit, total_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    conn.close()

# ========== RECEIPT FUNCTIONS ==========

def get_receipts_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        SELECT receipt_id, total_amount, contact_number, date, time
        FROM receipts
        WHERE user_id = ?
        ORDER BY receipt_id DESC
    """, (user_id,))
    data = cr.fetchall()
    conn.close()
    return data

def add_receipt(total_amount, contact_number, date, time, user_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        INSERT INTO receipts (total_amount, contact_number, date, time, user_id)
        VALUES (?, ?, ?, ?, ?)
    """, (total_amount, contact_number, date, time, user_id))
    conn.commit()
    receipt_id = cr.lastrowid
    conn.close()
    return receipt_id

def add_receipt_item(receipt_id, name, quantity, price, subtotal):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        INSERT INTO receipt_items (receipt_id, product_name, quantity, price_per_unit, subtotal)
        VALUES (?, ?, ?, ?, ?)
    """, (receipt_id, name, quantity, price, subtotal))
    conn.commit()
    conn.close()

def get_items_by_receipt_id(receipt_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_name, quantity, price_per_unit, subtotal
        FROM receipt_items
        WHERE receipt_id = ?
    """, (receipt_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def get_receipt_by_id(receipt_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT total_amount, contact_number, date, time
        FROM receipts
        WHERE receipt_id = ?
    """, (receipt_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# ========== USER FUNCTIONS ==========

def get_user_by_id(user_id):
    conn = sqlite3.connect(LOGIN_DB)
    cr = conn.cursor()
    cr.execute("SELECT * FROM USERS WHERE id = ?", (user_id,))
    user = cr.fetchone()
    conn.close()
    return user

# ========== DASHBOARD SUMMARY ==========

def get_total_products():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT COUNT(*) FROM inventory")
    count = cr.fetchone()[0]
    conn.close()
    return count

def get_total_customers():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT COUNT(*) FROM sales")
    count = cr.fetchone()[0]
    conn.close()
    return count

def get_total_sales():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT SUM(total_amount) FROM sales")
    total = cr.fetchone()[0] or 0
    conn.close()
    return total

def get_all_products():
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("SELECT name FROM inventory")
    products = cr.fetchall()
    conn.close()
    return products

# ========== MONTHLY STATS ==========

def get_monthly_sales(user_id):
    now = datetime.now()
    month = now.strftime("%Y-%m")
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        SELECT SUM(total_amount)
        FROM sales
        WHERE user_id = ? AND strftime('%Y-%m', timestamp) = ?
    """, (user_id, month))
    total = cr.fetchone()[0] or 0
    conn.close()
    return total

def get_monthly_receipts(user_id):
    now = datetime.now()
    month = now.strftime("%Y-%m")
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    cr.execute("""
        SELECT COUNT(*)
        FROM receipts
        WHERE user_id = ? AND strftime('%Y-%m', date) = ?
    """, (user_id, month))
    count = cr.fetchone()[0] or 0
    conn.close()
    return count

def get_total_sales_this_month(user_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    current_month = datetime.now().strftime("%Y-%m")
    cr.execute("""
        SELECT SUM(total_amount) FROM sales
        WHERE strftime('%Y-%m', timestamp) = ? AND user_id = ?
    """, (current_month, user_id))
    total = cr.fetchone()[0] or 0
    conn.close()
    return total

def get_total_receipts_this_month(user_id):
    conn = sqlite3.connect(DB_NAME)
    cr = conn.cursor()
    current_month = datetime.now().strftime("%Y-%m")
    cr.execute("""
        SELECT COUNT(*) FROM receipts
        WHERE strftime('%Y-%m', date) = ? AND user_id = ?
    """, (current_month, user_id))
    count = cr.fetchone()[0]
    conn.close()
    return count

# Add a QR image column to USERS table if not already there
def add_qr_column():
    conn = sqlite3.connect(LOGIN_DB)
    cr = conn.cursor()
    try:
        cr.execute("ALTER TABLE USERS ADD COLUMN qr_image TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()

# Initialize everything if this file is run directly
if __name__ == "__main__":
    init_inventory_table()
    init_sales_table()
    init_users_table()
    init_receipts_table()
    init_receipt_items_table()
    add_contact_column()
    add_user_id_column_to_sales()
    add_user_id_column_to_inventory()
    add_qr_column()
