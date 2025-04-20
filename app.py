from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# ------------------- Flask-Login Setup -------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# ------------------- User Class -------------------
class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

# ------------------- Database -------------------
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user:
        return User(id=user['id'], email=user['email'])
    return None

# ------------------- Routes -------------------

@app.route('/')
def home():
    return redirect(url_for('login'))

# --- Signup ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        conn = get_db()
        conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            login_user(User(id=user['id'], email=user['email']))
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid email or password."
    return render_template('login.html', error=error)

# --- Logout ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_email=current_user.email)

# --- Profile ---
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db()
    user = conn.execute("SELECT email FROM users WHERE id = ?", (current_user.id,)).fetchone()
    current_email = user['email']
    message = None

    if request.method == 'POST':
        new_email = request.form['email']
        new_password = request.form['password']
        if new_password:
            hashed_pw = generate_password_hash(new_password)
            conn.execute("UPDATE users SET email = ?, password = ? WHERE id = ?", (new_email, hashed_pw, current_user.id))
        else:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, current_user.id))
        conn.commit()
        message = "Profile updated successfully."
        current_email = new_email

    return render_template('profile.html', user_email=current_email, message=message)

# --- Expenses ---
@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    conn = get_db()
    if request.method == 'POST':
        category = request.form['category']
        amount = request.form['amount']
        description = request.form['description']
        reminder_date = request.form.get('reminder_date')
        reminder_note = request.form.get('reminder_note')
        date_now = datetime.now().strftime('%Y-%m-%d')

        conn.execute("""
            INSERT INTO expenses (
                user_id, category, amount, date, description, reminder_date, reminder_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (current_user.id, category, amount, date_now, description, reminder_date, reminder_note))
        conn.commit()

    expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC",
        (current_user.id,)
    ).fetchall()

    summary = conn.execute(
        "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category",
        (current_user.id,)
    ).fetchall()

    labels = [row['category'] for row in summary]
    values = [row['total'] for row in summary]

    return render_template('expenses.html', expenses=expenses, labels=labels, values=values)

# --- Diary ---
@app.route('/diary', methods=['GET', 'POST'])
@login_required
def diary():
    conn = get_db()
    if request.method == 'POST':
        entry = request.form['entry']
        today = date.today().isoformat()
        conn.execute("INSERT INTO diary (user_id, date, entry) VALUES (?, ?, ?)", (current_user.id, today, entry))
        conn.commit()

    entries = conn.execute(
        "SELECT * FROM diary WHERE user_id = ? ORDER BY date DESC",
        (current_user.id,)
    ).fetchall()

    return render_template('diary.html', entries=entries)

# --- Weather ---
@app.route('/weather', methods=['GET', 'POST'])
@login_required
def weather():
    weather_data = None
    error = None
    if request.method == 'POST':
        city = request.form['city'].strip()
        api_key = 'cf0c67531764fc3fac7328157d5ec2ee'
        url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'

        try:
            response = requests.get(url)
            if response.status_code == 200:
                weather_data = response.json()
            else:
                error = f"Could not retrieve weather for '{city}'."
        except Exception as e:
            error = f"An error occurred: {str(e)}"

    return render_template('weather.html', weather=weather_data, error=error)

# ------------------- Run App -------------------
if __name__ == '__main__':
    app.run(debug=True)
