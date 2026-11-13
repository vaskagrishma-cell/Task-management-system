
import os
import secrets
from datetime import date
from functools import wraps

from dotenv import load_dotenv

load_dotenv()

import mysql.connector
from flask import (
    Flask, abort, flash, redirect,
    render_template, request, session, url_for
)
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from database import get_db_connection, init_db


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

TASK_STATUSES = ("Pending", "In Progress", "Completed")


def login_required(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return route(*args, **kwargs)

    return wrapper


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        expected = session.get("_csrf_token")
        supplied = request.form.get("csrf_token", "")

        if not expected or not secrets.compare_digest(expected, supplied):
            abort(400, description="Invalid or missing CSRF token.")


@app.context_processor
def provide_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)

    return {"csrf_token": session["_csrf_token"]}


def parse_due_date(value):
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        return render_template("register.html")

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
        flash("Password must be at least 8 characters long.")
        return redirect(url_for("register"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (name, email, generate_password_hash(password))
        )

        connection.commit()
        user_id = cursor.lastrowid

    except mysql.connector.IntegrityError:
        connection.rollback()
        flash("An account with that email already exists.")
        return redirect(url_for("register"))

    finally:
        cursor.close()
        connection.close()

    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name

    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, name, password
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

    finally:
        cursor.close()
        connection.close()

    if user is None or not check_password_hash(user["password"], password):
        flash("Invalid email or password.")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, title, description, due_date, status
            FROM tasks
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (session["user_id"],)
        )

        tasks = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "dashboard.html",
        tasks=tasks,
        user_name=session.get("user_name", ""),
        today=date.today()
    )


@app.route("/tasks", methods=["POST"])
@login_required
def add_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip() or None
    due_date_value = request.form.get("due_date", "")
    due_date = parse_due_date(due_date_value)

    if not title or len(title) > 200:
        flash("Please enter a valid task title.")
        return redirect(url_for("dashboard"))

    if due_date_value and due_date is None:
        flash("Please enter a valid due date.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO tasks
            (user_id, title, description, due_date)
            VALUES (%s, %s, %s, %s)
            """,
            (
                session["user_id"],
                title,
                description,
                due_date
            )
        )

        connection.commit()

    finally:
        cursor.close()
        connection.close()

    flash("Task added successfully.")

    return redirect(url_for("dashboard"))


@app.route("/tasks/<int:task_id>/update", methods=["POST"])
@login_required
def update_task(task_id):
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip() or None
    due_date_value = request.form.get("due_date", "")
    due_date = parse_due_date(due_date_value)
    status = request.form.get("status", "")

    if not title or len(title) > 200:
        flash("Please enter a valid task title.")
        return redirect(url_for("dashboard"))

    if due_date_value and due_date is None:
        flash("Please enter a valid due date.")
        return redirect(url_for("dashboard"))

    if status not in TASK_STATUSES:
        flash("Please select a valid task status.")
        return redirect(url_for("dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            UPDATE tasks
            SET title = %s,
                description = %s,
                due_date = %s,
                status = %s
            WHERE id = %s AND user_id = %s
            """,
            (
                title,
                description,
                due_date,
                status,
                task_id,
                session["user_id"]
            )
        )

        connection.commit()

        if cursor.rowcount == 0:
            cursor.execute(
                """
                SELECT id FROM tasks
                WHERE id = %s AND user_id = %s
                """,
                (task_id, session["user_id"])
            )

            flash(
                "Task updated." if cursor.fetchone()
                else "Task not found."
            )
        else:
            flash("Task updated successfully.")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("dashboard"))


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM tasks
            WHERE id = %s AND user_id = %s
            """,
            (task_id, session["user_id"])
        )

        connection.commit()

        if cursor.rowcount == 0:
            flash("Task not found.")
        else:
            flash("Task deleted successfully.")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
