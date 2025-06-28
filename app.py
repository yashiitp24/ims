from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from datetime import datetime
import os
from werkzeug.utils import secure_filename

import db
from db import DB_NAME
from db import (
    init_inventory_table,
    init_sales_table,
    init_users_table,
    init_receipts_table,
    add_item,
    get_all_items,
    delete_item,
    get_item_by_product_id,
    update_item,
    get_item_by_name,
    add_sale,
    get_user_by_id,
    get_total_products,
    get_total_customers,
    get_total_sales,
    get_all_products,
    reduce_product_quantity,
    add_receipt_item,
    get_receipts_by_user,
    get_items_by_receipt_id,
    get_receipt_by_id,
    get_items_by_user
)

app = Flask(__name__)
app.secret_key = "fixed_secret_key_1234567890"  # Needed to securely manage sessions

# Make sure the folder for uploaded QR codes exists
UPLOAD_FOLDER = 'static/qr_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create all the required tables if they don’t exist
init_inventory_table()
init_sales_table()
init_users_table()
init_receipts_table()
db.add_contact_column()
db.add_user_id_column_to_sales()

# Get the filename of the QR code image for a specific user
def get_user_qr_image(user_id):
    conn = sqlite3.connect("LoginData.db")
    cursor = conn.cursor()
    cursor.execute("SELECT qr_image FROM USERS WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Makes `now()` available inside HTML templates for dynamic date/time
@app.context_processor
def inject_now():
    return {'now': datetime.now()}


# ========== AUTHENTICATION ROUTES ==========

# Show login page
@app.route('/')
def login():
    return render_template('login.html')


# Handle login form submission
@app.route('/login_validation', methods=['POST'])
def login_validation():
    email = request.form.get('email')
    password = request.form.get('password')

    conn = sqlite3.connect("LoginData.db")
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM USERS WHERE email=? AND password=?", (email, password)).fetchone()
    conn.close()

    if user:
        session['user_id'] = user[0]
        session['user_name'] = user[1]
        return redirect('/dashboard')
    else:
        return redirect('/')


# Show sign-up form
@app.route('/signUp')
def signUp():
    return render_template('signUp.html')


# Handle registration form submission
@app.route('/add_user', methods=['POST'])
def add_user():
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('email')
    password = request.form.get('password')

    conn = sqlite3.connect("LoginData.db")
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM USERS WHERE email=?", (email,)).fetchone()

    if user:
        return render_template('signUp.html', msg="User already exists")
    else:
        cursor.execute("INSERT INTO USERS (first_name, last_name, email, password) VALUES (?, ?, ?, ?)", (fname, lname, email, password))
        conn.commit()
        conn.close()
        return redirect('/')


# Show the main dashboard after login
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    user_name = session.get('user_name', 'User')

    total_products = len(db.get_items_by_user(user_id))
    total_receipts = len(db.get_receipts_by_user(user_id))
    total_sales_month = db.get_monthly_sales(user_id)
    total_receipts_month = db.get_monthly_receipts(user_id)

    return render_template('homepage.html',
                           user=user_name,
                           total_products=total_products,
                           total_receipts=total_receipts,
                           total_sales_month=total_sales_month,
                           total_receipts_month=total_receipts_month)


# Logs the user out and clears their session
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ========== BILLING SYSTEM ==========

# Display billing form and handle billing logic
@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    items = [item for item in db.get_items_by_user(user_id) if item[2] > 0]
    products = [{'name': item[1], 'price': item[3]} for item in items]

    if request.method == 'POST':
        selected_names = request.form.getlist('product_name')
        selected_quantities = request.form.getlist('quantity')

        bill_items = []
        total_amount = 0

        for name, qty in zip(selected_names, selected_quantities):
            if not name or not qty:
                continue

            quantity = int(qty)
            product = db.get_item_by_name(name)

            if not product or product[2] < quantity:
                continue

            price = product[3]
            subtotal = quantity * price
            total_amount += subtotal

            db.add_sale(name, quantity, price, subtotal, user_id)
            db.reduce_product_quantity(name, quantity)

            bill_items.append({
                'name': name,
                'quantity': quantity,
                'price': price,
                'subtotal': subtotal
            })

        now = datetime.now()
        date_part = now.strftime("%Y-%m-%d")
        time_part = now.strftime("%H:%M:%S")
        contact_number = db.get_user_by_id(user_id)[5]

        # Save the receipt in the DB
        db_conn = sqlite3.connect(DB_NAME)
        cr = db_conn.cursor()
        cr.execute("""
            INSERT INTO receipts (total_amount, contact_number, date, time, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, (total_amount, contact_number, date_part, time_part, user_id))
        db_conn.commit()
        receipt_id = cr.lastrowid
        db_conn.close()

        # Save each item in the receipt
        for item in bill_items:
            db.add_receipt_item(receipt_id, item['name'], item['quantity'], item['price'], item['subtotal'])

        total_products = sum([item['quantity'] for item in bill_items])
        user_qr = get_user_qr_image(user_id)

        return render_template("receipt.html",
                               bill_items=bill_items,
                               total=total_amount,
                               date_part=date_part,
                               time_part=time_part,
                               total_products=total_products,
                               contact_number=contact_number,
                               qr_code_path=f'qr_uploads/{user_qr}' if user_qr else None)

    return render_template("billing.html", products=products)


# View a specific receipt by ID
@app.route('/receipt/<int:receipt_id>')
def view_receipt(receipt_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    receipt = db.get_receipt_by_id(receipt_id)

    if not receipt:
        return "Receipt not found", 404

    total_amount, contact_number, date_part, time_part = receipt
    items = db.get_items_by_receipt_id(receipt_id)

    bill_items = []
    total_products = 0

    for item in items:
        name, qty, price, subtotal = item
        bill_items.append({
            'name': name,
            'quantity': qty,
            'price': price,
            'subtotal': subtotal
        })
        total_products += qty

    user = db.get_user_by_id(user_id)
    qr_image_filename = user[6] if user and len(user) > 6 else None

    return render_template(
        'receipt.html',
        bill_items=bill_items,
        total=total_amount,
        contact_number=contact_number,
        date_part=date_part,
        time_part=time_part,
        total_products=total_products,
        qr_code_path=f'qr_uploads/{qr_image_filename}' if qr_image_filename else None
    )


# ========== USER PROFILE ==========

# Profile editing route (also handles QR upload)
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/')

    conn = sqlite3.connect("LoginData.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        email = request.form.get('email')
        password = request.form.get('password')
        contact = request.form.get('contact')

        # Handle QR code upload
        if 'qr_code' in request.files:
            qr_file = request.files['qr_code']
            if qr_file.filename:
                filename = secure_filename(qr_file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                qr_file.save(path)
                cursor.execute("UPDATE USERS SET qr_image = ? WHERE id = ?", (filename, user_id))

        cursor.execute("""
            UPDATE USERS
            SET first_name = ?, email = ?, password = ?, contact = ?
            WHERE id = ?
        """, (first_name, email, password, contact, user_id))

        conn.commit()
        conn.close()
        session['user_name'] = first_name
        return redirect('/edit_profile')

    user = cursor.execute("""
        SELECT first_name, email, password, contact, qr_image FROM USERS WHERE id = ?
    """, (user_id,)).fetchone()
    conn.close()

    return render_template("edit_profile.html", user=user)


# ========== OTHER PAGES ==========

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    receipts = db.get_receipts_by_user(user_id)
    return render_template('history.html', receipts=receipts)


@app.route('/sales')
def sales():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, product_name, quantity, price_per_unit, total_amount, timestamp
        FROM sales
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """, (user_id,))
    sales_data = cursor.fetchall()
    conn.close()
    return render_template('sales.html', sales=sales_data)


@app.route('/feedback')
def feedback():
    return render_template('feedback_form.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


# ========== PRODUCT MANAGEMENT ==========

@app.route('/stocks')
def stocks():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    search_query = request.args.get('search', '').strip().lower()

    if search_query:
        items = [item for item in db.get_items_by_user(user_id) if search_query in item[1].lower()]
    else:
        items = db.get_items_by_user(user_id)

    return render_template('stocks.html', items=items, search=search_query)


@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    search_query = request.args.get('search', '').strip().lower()

    if search_query:
        items = [item for item in db.get_items_by_user(user_id) if search_query in item[1].lower()]
    else:
        items = db.get_items_by_user(user_id)

    return render_template('products.html', items=items, search=search_query)


@app.route('/add')
def add():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('add.html')


@app.route('/add_item', methods=['POST'])
def add_item_route():
    if 'user_id' not in session:
        return redirect('/login')

    name = request.form.get('name')
    quantity = int(request.form.get('quantity'))
    price = float(request.form.get('price'))
    user_id = session['user_id']

    db.add_item(name, quantity, price, user_id)
    return redirect('/stocks')


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_item(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    item = db.get_item_by_product_id(product_id)

    if not item or item[-1] != user_id:
        return "Item not found or unauthorized", 404

    if request.method == 'POST':
        name = request.form['name']
        qty = int(request.form['qty'])
        price = float(request.form['price'])
        db.update_item(product_id, name, qty, price)
        return redirect('/stocks')

    return render_template('edit.html', item=item)


@app.route('/update_item', methods=['POST'])
def update_item_route():
    if 'user_id' not in session:
        return redirect('/login')

    product_id = int(request.form.get('product_id'))
    name = request.form.get('name')
    quantity = int(request.form.get('quantity'))
    price = float(request.form.get('price'))
    db.update_item(product_id, name, quantity, price)
    return redirect('/stocks')


@app.route('/delete/<int:product_id>')
def delete(product_id):
    if 'user_id' not in session:
        return redirect('/login')

    db.delete_item(product_id)
    return redirect('/stocks')


@app.route('/search_stock', methods=['GET'])
def search_stock():
    if 'user_id' not in session:
        return redirect('/login')

    query = request.args.get('query', '')
    user_id = session['user_id']
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM inventory WHERE user_id = ? AND LOWER(name) LIKE ?
    """, (user_id, f'%{query.lower()}%'))

    items = cursor.fetchall()
    conn.close()

    return render_template('stocks.html', items=items, query=query)


# Show forgot password form (uses same style as feedback)
@app.route("/forgot_password")
def forgot_password():
    return render_template("forgot_password.html")


# Run the app locally on port 46000
if __name__ == "__main__":
    app.run(debug=True, port=46000)
