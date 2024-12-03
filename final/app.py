from flask import Flask, render_template, request, redirect, flash, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from sqlite3 import Error
from openai import OpenAI
import os

# Replace the CS50 DB configuration with sqlite3 connection function
def get_db_connection():
    try:
        conn = sqlite3.connect('christmas_list.db')
        # This allows accessing columns by name
        conn.row_factory = sqlite3.Row  
        return conn
    except Error as e:
        print(e)
        return None

# Initialize the database
def init_db():
    conn = get_db_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        username TEXT NOT NULL,
        hash TEXT NOT NULL
    )
    """)
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS username ON users (username);""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        user_id INTEGER NOT NULL,
        item TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_user_id ON items(user_id);""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS secret_santa_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        group_name TEXT NOT NULL,
        price_limit REAL NOT NULL,
        exchange_date DATE,
        created_by INTEGER NOT NULL,
        FOREIGN KEY (created_by) REFERENCES users (id)
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS secret_santa_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        group_id INTEGER NOT NULL,
        santa_id INTEGER NOT NULL,
        recipient_id INTEGER NOT NULL,
        FOREIGN KEY (group_id) REFERENCES secret_santa_groups (id),
        FOREIGN KEY (santa_id) REFERENCES users (id),
        FOREIGN KEY (recipient_id) REFERENCES users (id)
    )
    """)
    conn.commit()
    conn.close()

# Call init_db() right after creating the app
app = Flask(__name__)
# This initializes the database
init_db()  

# Rest of app configuration
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["TEMPLATES_AUTO_RELOAD"] = True
Session(app)

# Configure SQLite database
db = get_db_connection()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Show the user's Christmas list on the home page."""
    if "user_id" not in session:
        return redirect("/login")
    
    conn = get_db_connection()
    cur = conn.cursor()
    items = cur.execute("SELECT id, item FROM items WHERE user_id = ?", 
                       (session["user_id"],)).fetchall()
    conn.close()
    return render_template("index.html", items=items)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user."""

    # If the user submitted the form via POST
    if request.method == "POST":

        # Ensure username and password were submitted
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect("/register")

        # Ensure username does not already exist, then insert new user into users
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                (username, generate_password_hash(password)))
            conn.commit()
            flash("Successfully registered!", "success")
        except sqlite3.IntegrityError:
            flash("Username already exists", "error")
        finally:
            conn.close()

        # Redirect user to login form
        return redirect("/login")

    # If the user is accessing the page via GET
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in an existing user."""

    # If the user submitted the form via POST
    if request.method == "POST":
        username = request.form.get("username")

        # Ensure username was submitted
        if not username:
            flash("Username required!", "error")
            return redirect("/login")

        # Query database for username
        conn = get_db_connection()
        cur = conn.cursor()
        user = cur.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()
        conn.close()

        # Ensure username exists and password is correct
        if len(user) != 1 or not check_password_hash(
            user[0]["hash"], request.form.get("password")
        ):
            flash("Invalid username and/or password!", "error")
            return redirect("/login")

        session["user_id"] = user[0]["id"]
        flash("Ho ho ho! Welcome back! 🎅", "success")
        return redirect("/")

    # If the user is accessing the page via GET
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log out the current user."""
    session.clear()
    flash("Logged out!", "success")
    return redirect("/")


@app.route("/add", methods=["GET", "POST"])
def add():
    """Add an item to the Christmas list."""
    if "user_id" not in session:
        return redirect("/login")

    # If the user submitted the form via POST
    if request.method == "POST":
        item = request.form.get("name")

        # Validate the input
        if not item:
            flash("Invalid input! Please try again.", "error")
            return redirect("/add")

        # Insert the item into the database
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO items (user_id, item) VALUES (?, ?)",
            (session["user_id"], item))
        conn.commit()
        conn.close()
        flash("Added to your wishlist! ✨", "success")
        return redirect("/")

    # If the user is accessing the page via GET
    return render_template("add.html")


@app.route("/lookup", methods=["GET", "POST"])
def lookup():
    """Look up another user's Christmas list."""
    if "user_id" not in session:
        return redirect("/login")

    # If the user submitted the form via POST
    if request.method == "POST":
        username = request.form.get("username")
        
        if not username:
            flash("Please enter a username!", "error")
            return redirect("/lookup")
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        # First find the user
        user = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        
        # Ensure the user exists
        if not user:
            flash("User not found!", "error")
            return redirect("/lookup")
            
        # Get items from database
        items = cur.execute("SELECT item FROM items WHERE user_id = ?", (user['id'],)).fetchall()
        
        # Ensure the user has items on their list
        if not items:
            flash("This user's list is empty!", "error")
            return redirect("/lookup")
        
        # Close the connection and render the lookup results page
        conn.close()
        return render_template("lookup_result.html", items=items, username=username)

    # If the user is accessing the page via GET
    return render_template("lookup.html")


@app.route("/secret_santa", methods=['GET', 'POST'])
def secret_santa():
    """Allow user to create a new Secret Santa group and see their assignments."""
    
    # Ensure the user is logged in
    if "user_id" not in session:
        return redirect("/login")
        
    # Get the user's username
    conn = get_db_connection()
    cur = conn.cursor()
    user = cur.execute("SELECT username FROM users WHERE id = ?", 
                      (session["user_id"],)).fetchone()
    
    # If the user submitted the form via POST
    if request.method == 'POST':
        group_name = request.form.get("group_name")
        price_limit = request.form.get("price_limit")
        exchange_date = request.form.get("exchange_date")
        participants = request.form.getlist("participants[]")
        
        # Validate participants
        if len(participants) < 2:
            flash("You need at least two participants!", "error")
            return redirect("/secret_santa")
        
        # Check if all participants exist
        participant_ids = []
        for username in participants:
            participant = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if not participant:
                flash(f"User {username} does not exist!", "error")
                return redirect("/secret_santa")
            participant_ids.append(participant['id'])
        
        # Create the Secret Santa group
        cur.execute("INSERT INTO secret_santa_groups (group_name, price_limit, exchange_date, created_by) VALUES (?, ?, ?, ?)",
                    (group_name, price_limit, exchange_date, session["user_id"]))
        group_id = cur.lastrowid
        
        # Shuffle and assign Secret Santas
        import random
        random.shuffle(participant_ids)
        assignments = [(participant_ids[i], participant_ids[(i + 1) % len(participant_ids)]) for i in range(len(participant_ids))]
        
        # Store assignments in a table
        for santa_id, recipient_id in assignments:
            cur.execute("INSERT INTO secret_santa_assignments (group_id, santa_id, recipient_id) VALUES (?, ?, ?)",
                        (group_id, santa_id, recipient_id))
        
        # Commit the changes and close the connection
        conn.commit()
        flash("Secret Santa group created successfully!", "success")
        return redirect("/secret_santa")
    
    # If the user is accessing the page via GET (or was redirected from POST)
    # Get assignments for display
    assignments = cur.execute("""
        SELECT 
            sg.group_name,
            sg.price_limit,
            sg.exchange_date,
            u.username as recipient_name
        FROM secret_santa_assignments sa
        JOIN secret_santa_groups sg ON sa.group_id = sg.id
        JOIN users u ON sa.recipient_id = u.id
        WHERE sa.santa_id = ?
        ORDER BY sg.exchange_date ASC
    """, (session["user_id"],)).fetchall()
    
    # Close the connection and render the Secret Santa page
    conn.close()
    return render_template('secret_santa.html', 
                         username=user['username'], 
                         assignments=assignments)


@app.route("/delete_item/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    """Delete an item from the user's Christmas list."""
    if "user_id" not in session:
        return redirect("/login")
        
    try:
        conn = get_db_connection()
        
        # First, verify the item exists and belongs to the user
        item = conn.execute("SELECT * FROM items WHERE id = ? AND user_id = ?", 
                          (item_id, session["user_id"])).fetchone()
        
        # If the item exists and belongs to the user, delete it
        if item:
            conn.execute("DELETE FROM items WHERE id = ? AND user_id = ?", 
                        (item_id, session["user_id"]))
            conn.commit()
            flash("Item deleted successfully!", "success")
        else:
            flash("Item not found or you don't have permission to delete it.", "error")
            
        conn.close()
        
    except Exception as e:
        flash("Error deleting item.", "error")
    
    # Redirect the user back to the home page
    return redirect("/")


# Run the app
if __name__ == "__main__":
    app.run()
