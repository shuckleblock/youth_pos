from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("pos.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                 id INTEGER PRIMARY KEY,
                 name TEXT NOT NULL,
                 price REAL NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                 id INTEGER PRIMARY KEY,
                 product_id INTEGER,
                 quantity INTEGER,
                 total REAL,
                 FOREIGN KEY(product_id) REFERENCES products(id))''')
    # Sample data
    c.execute("INSERT OR IGNORE INTO products VALUES (1, 'Apple', 0.50)")
    c.execute("INSERT OR IGNORE INTO products VALUES (2, 'Banana', 0.30)")
    c.execute("INSERT OR IGNORE INTO products VALUES (3, 'Orange', 0.80)")
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/products')
def get_products():
    conn = sqlite3.connect("pos.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    rows = c.fetchall()
    conn.close()
    products = [{"id": row[0], "name": row[1], "price": row[2]} for row in rows]
    return jsonify(products)

@app.route('/checkout', methods=["POST"])
def checkout():
    data = request.json
    for item in data["cart"]:
        conn = sqlite3.connect("pos.db")
        c = conn.cursor()
        c.execute("INSERT INTO sales (product_id, quantity, total) VALUES (?, ?, ?)", 
                  (item["id"], item["quantity"], item["total"]))
        conn.commit()
        conn.close()
    return jsonify({"status": "success", "message": "Transaction complete."})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)  # Accessible from iPad on local network
