import sqlite3
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash

auth_bp = Blueprint('auth', __name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'campus_transport.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

@auth_bp.route('/login/student', methods=['GET', 'POST'])
def login_student():
    if session.get('role') == 'STUDENT':
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        password = request.form.get('password', '').strip()

        if not student_id or not password:
            flash('Student ID and Password are required.', 'danger')
            return render_template('login_student.html')

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, student_id, name, password FROM students WHERE student_id = ?;", (student_id,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row or not check_password_hash(row[3], password):
            flash('Invalid Student ID or Password.', 'danger')
            return render_template('login_student.html')

        session.clear()
        session['user_id'] = row[0]
        session['student_id'] = row[1]
        session['display_name'] = row[2]
        session['role'] = 'STUDENT'

        return redirect(url_for('student.dashboard'))

    return render_template('login_student.html')

@auth_bp.route('/login/driver', methods=['GET', 'POST'])
def login_driver():
    if session.get('role') == 'DRIVER':
        return redirect(url_for('driver.dashboard'))

    if request.method == 'POST':
        driver_id = request.form.get('driver_id', '').strip()
        password = request.form.get('password', '').strip()

        if not driver_id or not password:
            flash('Driver Login ID and Password are required.', 'danger')
            return render_template('login_driver.html')

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, driver_id, name, password FROM drivers WHERE driver_id = ?;", (driver_id,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row or not check_password_hash(row[3], password):
            flash('Invalid Driver Login ID or Password.', 'danger')
            return render_template('login_driver.html')

        session.clear()
        session['user_id'] = row[0]
        session['driver_id'] = row[1]
        session['display_name'] = row[2]
        session['role'] = 'DRIVER'

        return redirect(url_for('driver.dashboard'))

    return render_template('login_driver.html')

@auth_bp.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if session.get('role') == 'ADMIN':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        admin_id = request.form.get('admin_id', '').strip()
        password = request.form.get('password', '').strip()

        if not admin_id or not password:
            flash('Admin ID and Password are required.', 'danger')
            return render_template('login_admin.html')

        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, admin_id, name, password FROM admins WHERE admin_id = ?;", (admin_id,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row or not check_password_hash(row[3], password):
            flash('Invalid Admin ID or Password.', 'danger')
            return render_template('login_admin.html')

        session.clear()
        session['user_id'] = row[0]
        session['admin_id'] = row[1]
        session['display_name'] = row[2]
        session['role'] = 'ADMIN'

        return redirect(url_for('admin.dashboard'))

    return render_template('login_admin.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have logged out successfully.', 'info')
    return redirect(url_for('index'))
