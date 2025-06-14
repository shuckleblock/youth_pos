from flask import Flask, render_template, request, jsonify
import psycopg2
import os

from flask import request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps



app = Flask(__name__)

UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Database Connection ---
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )

# --- Initialize Tables ---
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER,
            total REAL
        )
    ''')

    # Insert demo data if not already there
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO products (name, price) VALUES (%s, %s)", [
            ('삼겹살', 15.00),
            ('Lemonade', 3.00)
        ])

    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/products')
def get_products():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    rows = cur.fetchall()
    products = [{"id": row[0], "name": row[1], "price": row[2]} for row in rows]
    cur.close()
    conn.close()
    return jsonify(products)

@app.route('/checkout', methods=["POST"])
def checkout():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    for item in data["cart"]:
        cur.execute(
            "INSERT INTO sales (product_id, quantity, total) VALUES (%s, %s, %s)",
            (item["id"], item["quantity"], item["total"])
        )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "message": "Transaction complete."})

#---auth for admin page---
def check_auth(username, password):
    return username == os.environ.get("ADMIN_USER") and password == os.environ.get("ADMIN_PASS")

def authenticate():
    return (
        "Could not verify access.",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route('/admin', methods=['GET', 'POST'])
@requires_auth
def admin():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])

        # Insert into DB
        cur.execute("INSERT INTO products (name, price) VALUES (%s, %s)", (name, price))

        # Handle image upload
        file = request.files.get('image')
        if file and file.filename != '':
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                filename = f"{name.lower()}.{ext}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
                file.save(filepath)

        conn.commit()

    cur.execute("SELECT name, price, id FROM products ORDER BY id")

    products = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin.html", products=products)

@app.route('/admin/edit/<int:product_id>', methods=['POST'])
def edit_product(product_id):
    name = request.form['name']
    price = float(request.form['price'])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET name = %s, price = %s WHERE id = %s", (name, price, product_id))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin'))

@app.route('/transactions')
def transactions():
    conn = get_db_connection()
    cur = conn.cursor()

    # Join sales and products tables to get readable product names
    cur.execute("""
        SELECT 
            s.timestamp, 
            p.name, 
            s.quantity, 
            s.total 
        FROM sales s
        JOIN products p ON s.product_id = p.id
        ORDER BY s.timestamp DESC
    """)
    sales = cur.fetchall()

    # Calculate running total
    cur.execute("SELECT SUM(total) FROM sales")
    total_sales = cur.fetchone()[0] or 0.0

    cur.close()
    conn.close()

    return render_template("transactions.html", sales=sales, total_sales=total_sales)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
