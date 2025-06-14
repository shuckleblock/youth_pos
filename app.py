from flask import Flask, render_template, request, jsonify
import psycopg2
import os

app = Flask(__name__)

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
            ('Apple', 0.50),
            ('Banana', 0.30),
            ('Orange', 0.80),
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

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
