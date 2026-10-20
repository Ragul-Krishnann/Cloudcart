import os
from decimal import Decimal

import mysql.connector


from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    flash,
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

app = Flask(__name__, static_folder="public", static_url_path="")

app.secret_key = os.getenv(
    "SECRET_KEY",
    "local-only-development-key"
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# --------------------------------------------------
# MYSQL CONNECTION
# --------------------------------------------------


import os
import mysql.connector

def get_db_connection():
    host = os.getenv("DB_HOST", "127.0.0.1")

    connection_config = {
        "host": host,
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME", "cloudcart_db"),
    }

    # Use SSL verification for the cloud database.
    if host != "127.0.0.1" and host != "localhost":
        connection_config["ssl_ca"] = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "aiven-ca.pem"
        )
        connection_config["ssl_verify_cert"] = True
        connection_config["ssl_verify_identity"] = True

    return mysql.connector.connect(**connection_config)


# --------------------------------------------------
# USER MODEL AND LOGIN MANAGEMENT
# --------------------------------------------------

class User(UserMixin):
    def __init__(self, user_id, name, email):
        self.id = str(user_id)
        self.name = name
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, name, email FROM users WHERE id = %s",
            (user_id,),
        )
        row = cursor.fetchone()

        if row:
            return User(row["id"], row["name"], row["email"])

        return None

    finally:
        cursor.close()
        conn.close()


# --------------------------------------------------
# PRODUCT FUNCTIONS
# --------------------------------------------------

def get_products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, name, price, description, stock
            FROM products
            ORDER BY id
            """
        )
        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def home():
    products = get_products()
    cart = session.get("cart", {})

    cart_items = []
    total = Decimal("0.00")

    for product in products:
        quantity = int(cart.get(str(product["id"]), 0))

        if quantity > 0:
            subtotal = Decimal(str(product["price"])) * quantity

            cart_items.append({
                **product,
                "quantity": quantity,
                "subtotal": subtotal,
            })

            total += subtotal

    return render_template(
        "index.html",
        products=products,
        cart_items=cart_items,
        total=total,
        cart_count=sum(int(q) for q in cart.values()),
    )


# --------------------------------------------------
# USER REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or len(name) > 100:
            flash("Please enter a valid name.")
            return redirect(url_for("register"))

        if not email or len(email) > 150:
            flash("Please enter a valid email address.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,),
            )

            if cursor.fetchone():
                flash("An account with this email already exists.")
                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (%s, %s, %s)
                """,
                (name, email, password_hash),
            )

            conn.commit()

            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:
            conn.rollback()
            flash("This email may already be registered.")
            return redirect(url_for("register"))

        except Exception:
            conn.rollback()
            app.logger.exception("Registration failed")
            flash("Registration failed. Please try again.")
            return redirect(url_for("register"))

        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


# --------------------------------------------------
# USER LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT id, name, email, password_hash
                FROM users
                WHERE email = %s
                """,
                (email,),
            )
            row = cursor.fetchone()

        finally:
            cursor.close()
            conn.close()

        if row and check_password_hash(row["password_hash"], password):
            user = User(row["id"], row["name"], row["email"])
            login_user(user)

            flash("Welcome back, " + user.name + "!")
            return redirect(url_for("home"))

        flash("Invalid email or password.")

    return render_template("login.html")


# --------------------------------------------------
# USER LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have logged out.")
    return redirect(url_for("home"))


# --------------------------------------------------
# ADD PRODUCT TO CART
# --------------------------------------------------

@app.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, stock FROM products WHERE id = %s",
            (product_id,),
        )
        product = cursor.fetchone()

    finally:
        cursor.close()
        conn.close()

    if not product:
        flash("Product not found.")
        return redirect(url_for("home"))

    cart = session.get("cart", {})
    key = str(product_id)
    current_quantity = int(cart.get(key, 0))

    if current_quantity < product["stock"]:
        cart[key] = current_quantity + 1
        session["cart"] = cart
    else:
        flash("Sorry, no more stock is available.")

    return redirect(url_for("home"))


# --------------------------------------------------
# REMOVE PRODUCT FROM CART
# --------------------------------------------------

@app.route("/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = session.get("cart", {})

    cart.pop(str(product_id), None)
    cart.pop(product_id, None)

    session["cart"] = cart
    session.modified = True

    flash("Product removed from your cart.")
    return redirect(url_for("checkout"))

# --------------------------------------------------
# CHECKOUT
# --------------------------------------------------

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = session.get("cart", {})

    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("home"))

    # Ignore invalid or non-positive quantities.
    try:
        quantities = {
            int(pid): int(qty)
            for pid, qty in cart.items()
            if int(qty) > 0
        }
    except (ValueError, TypeError):
        session["cart"] = {}
        flash("Your cart was invalid. Please add your products again.")
        return redirect(url_for("home"))

    if not quantities:
        session["cart"] = {}
        flash("Your cart is empty.")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Start a transaction and lock products to prevent
        # concurrent checkouts from overselling stock.
        conn.start_transaction()

        product_ids = sorted(quantities.keys())
        placeholders = ", ".join(["%s"] * len(product_ids))

        cursor.execute(
            f"""
            SELECT id, name, price, stock
            FROM products
            WHERE id IN ({placeholders})
            ORDER BY id
            FOR UPDATE
            """,
            tuple(product_ids),
        )

        products = cursor.fetchall()
        product_map = {p["id"]: p for p in products}

        if len(products) != len(product_ids):
            conn.rollback()
            flash("A product in your cart no longer exists.")
            return redirect(url_for("home"))

        cart_items = []
        total = Decimal("0.00")

        for product_id in product_ids:
            product = product_map[product_id]
            quantity = quantities[product_id]

            if quantity > product["stock"]:
                conn.rollback()
                flash(
                    f"Insufficient stock for {product['name']}. "
                    "Please review your cart."
                )
                return redirect(url_for("home"))

            price = Decimal(str(product["price"]))
            subtotal = price * quantity
            total += subtotal

            cart_items.append({
                **product,
                "quantity": quantity,
                "subtotal": subtotal,
            })

        if request.method == "GET":
            # No database changes on the checkout display.
            conn.rollback()

            return render_template(
                "checkout.html",
                cart_items=cart_items,
                total=total,
            )

        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        postal_code = request.form.get("postal_code", "").strip()
        payment_method = request.form.get("payment_method", "")

        if not address or len(address) > 500:
            conn.rollback()
            flash("Please enter a valid delivery address.")
            return redirect(url_for("checkout"))

        if not city or len(city) > 100:
            conn.rollback()
            flash("Please enter a valid city.")
            return redirect(url_for("checkout"))

        if len(postal_code) != 6 or not postal_code.isdigit():
            conn.rollback()
            flash("Please enter a valid 6-digit PIN code.")
            return redirect(url_for("checkout"))

        if payment_method != "cod":
            conn.rollback()
            flash("Please select Cash on Delivery.")
            return redirect(url_for("checkout"))

        # Create the order.
        cursor.execute(
            """
            INSERT INTO orders
                (user_id, address, city, postal_code,
                 payment_method, total, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                int(current_user.id),
                address,
                city,
                postal_code,
                payment_method,
                total,
                "Placed",
            ),
        )

        order_id = cursor.lastrowid

        # Save order items and reduce stock atomically.
        for item in cart_items:
            cursor.execute(
                """
                INSERT INTO order_items
                    (order_id, product_id, product_name,
                     quantity, price, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    order_id,
                    item["id"],
                    item["name"],
                    item["quantity"],
                    item["price"],
                    item["subtotal"],
                ),
            )

            cursor.execute(
                """
                UPDATE products
                SET stock = stock - %s
                WHERE id = %s AND stock >= %s
                """,
                (
                    item["quantity"],
                    item["id"],
                    item["quantity"],
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Stock changed for {item['name']}. "
                    "Please try checkout again."
                )

        conn.commit()

        session["cart"] = {}

        return redirect(
            url_for("order_success", order_id=order_id)
        )

    except ValueError as error:
        conn.rollback()
        flash(str(error))
        return redirect(url_for("home"))

    except Exception:
        conn.rollback()
        app.logger.exception("Checkout failed")
        flash("We couldn't place your order. Please try again.")
        return redirect(url_for("home"))

    finally:
        cursor.close()
        conn.close()


# --------------------------------------------------
# ORDER CONFIRMATION
# --------------------------------------------------

@app.route("/order-success/<int:order_id>")
@login_required
def order_success(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, total, status, created_at
            FROM orders
            WHERE id = %s AND user_id = %s
            """,
            (order_id, int(current_user.id)),
        )

        order = cursor.fetchone()

    finally:
        cursor.close()
        conn.close()

    if not order:
        flash("Order not found.")
        return redirect(url_for("home"))

    return render_template(
        "order_success.html",
        order=order,
    )


# --------------------------------------------------
# ORDER HISTORY
# --------------------------------------------------

@app.route("/my-orders")
@login_required
def my_orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, address, city, postal_code,
                   total, status, created_at
            FROM orders
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (int(current_user.id),),
        )

        orders = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "order_history.html",
        orders=orders,
    )


# --------------------------------------------------
# INDIVIDUAL ORDER DETAILS
# --------------------------------------------------

@app.route("/order-details/<int:order_id>")
@login_required
def order_detail(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, address, city, postal_code,
                   total, status, created_at, payment_method
            FROM orders
            WHERE id = %s AND user_id = %s
            """,
            (order_id, int(current_user.id)),
        )

        order = cursor.fetchone()

        if not order:
            flash("Order not found.")
            return redirect(url_for("my_orders"))

        cursor.execute(
            """
            SELECT product_name, quantity, price, subtotal
            FROM order_items
            WHERE order_id = %s
            ORDER BY id
            """,
            (order_id,),
        )

        items = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "order_detail.html",
        order=order,
        items=items,
    )


@app.route("/cancel-order/<int:order_id>", methods=["POST"])
@login_required
def cancel_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        # Find this customer's order and lock it during cancellation.
        cursor.execute(
            """
            SELECT id, status
            FROM orders
            WHERE id = %s AND user_id = %s
            FOR UPDATE
            """,
            (order_id, int(current_user.id))
        )

        order = cursor.fetchone()

        if not order:
            conn.rollback()
            flash("Order not found.")
            return redirect(url_for("my_orders"))

        if order["status"] != "Placed":
            conn.rollback()
            flash("Only orders with Placed status can be cancelled.")
            return redirect(url_for("my_orders"))

        # Restore stock for the cancelled order.
        cursor.execute(
            """
            SELECT product_id, quantity
            FROM order_items
            WHERE order_id = %s
            """,
            (order_id,)
        )
        items = cursor.fetchall()

        for item in items:
            cursor.execute(
                """
                UPDATE products
                SET stock = stock + %s
                WHERE id = %s
                """,
                (item["quantity"], item["product_id"])
            )

        # Keep the order record, but update its status.
        cursor.execute(
            """
            UPDATE orders
            SET status = 'Cancelled'
            WHERE id = %s AND user_id = %s
            """,
            (order_id, int(current_user.id))
        )

        conn.commit()
        flash(f"Order #{order_id} was cancelled successfully.")

    except Exception:
        conn.rollback()
        app.logger.exception("Order cancellation failed.")
        flash("Could not cancel the order. Please try again.")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("my_orders"))

# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
