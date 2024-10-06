import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

from math import ceil

# Configure application
app = Flask(__name__)

app.config['PROJECT_NAME'] = "VinnTrack"

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///attendance_management_system.db")


if __name__ == "__main__":
    app.run(debug=True)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.template_filter('format_breadcrumb')
def format_breadcrumb(path):
    """Function for formatting breadcrumb"""
    
    segments = path.strip('/').split('/')    
    formatted_segments = ' / '.join(segment.capitalize() for segment in segments)
    return formatted_segments or 'Dashboard'


@app.errorhandler(404)
def page_not_found(e):
    """Handler for PageNotFound Exception"""

    return apology("Page not found", 404)


import re
from flask import flash

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    session.clear()
    
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email:
            flash("Please provide an email address.", "danger")
            return render_template("login.html", title="Login", project_name=app.config['PROJECT_NAME'])
        
        elif not password:
            flash("Please provide a password.", "danger")
            return render_template("login.html", title="Login", project_name=app.config['PROJECT_NAME'])
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("Invalid email format. Please enter a valid email address.", "danger")
            return render_template("login.html", title="Login", project_name=app.config['PROJECT_NAME'])

        rows = db.execute("SELECT * FROM employee WHERE email = ?", email)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            flash("Invalid email and/or password. Please try again.", "danger")
            return render_template("login.html", title="Login", project_name=app.config['PROJECT_NAME'])

        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    return render_template("login.html", title="Login", project_name=app.config['PROJECT_NAME'])

@app.route("/")
# @login_required
def index():
    return render_template("index.html", title="Dashboard", project_name=app.config['PROJECT_NAME'])


@app.route("/division")
# @login_required
def division():
    """Division List with Pagination"""

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    total_divisions = db.execute("SELECT COUNT(*) as count FROM division")[0]['count']

    total_pages = ceil(total_divisions / per_page)

    # Get paginated divisions
    offset = (page - 1) * per_page
    divisions = db.execute("""
        SELECT 
            d.id, 
            d.name, 
            (SELECT COUNT(*) FROM department WHERE division_id = d.id) AS department_count,
            (SELECT COUNT(*) FROM department dep 
             JOIN team t ON dep.id = t.department_id 
             WHERE dep.division_id = d.id) AS team_count,
            COUNT(DISTINCT e.id) AS employee_count
        FROM division d
        LEFT JOIN department dep ON d.id = dep.division_id
        LEFT JOIN team t ON dep.id = t.department_id
        LEFT JOIN employee e ON t.id = e.team_id
        GROUP BY d.id
        ORDER BY d.id
        LIMIT ? OFFSET ?
    """, per_page, offset)

    return render_template("division.html", 
                           title="Division", 
                           project_name=app.config['PROJECT_NAME'], 
                           divisions=divisions,
                           page=page,
                           total_pages=total_pages)


@app.route("/division/new", methods=["GET", "POST"])
def add_division():
    """Add new division"""

    if request.method == "POST":
        division_name = request.form.get("division_name")
        
        # Input validation
        if not division_name:
            flash("Division name is required.", "danger")
            return render_template("add_division.html", title="Add Division", project_name=app.config['PROJECT_NAME'])
        
        # Check if the division name already exists
        existing_division = db.execute("SELECT * FROM division WHERE name = ?", division_name)
        if existing_division:
            flash("Division name already exists.", "danger")
            return render_template("add_division.html", title="Add Division", project_name=app.config['PROJECT_NAME'])
        
        db.execute("INSERT INTO division (name) VALUES (?)", division_name)
        flash("Division added successfully.", "success")
        return redirect("/division")
    
    return render_template("add_division.html", title="Add Division", project_name=app.config['PROJECT_NAME'])


@app.route("/division/edit/<int:division_id>", methods=["GET", "POST"])
def edit_division(division_id):
    """Edit division"""
    division = db.execute("SELECT * FROM division WHERE id = ?", division_id)
    
    if not division:
        flash("Division not found.", "danger")
        return redirect("/division")
    
    if request.method == "POST":
        new_division_name = request.form.get("division_name")

        # Input validation
        if not new_division_name:
            flash("Division name is required.", "danger")
            return render_template("edit_division.html", title="Edit Division", project_name=app.config['PROJECT_NAME'], division=division[0])
        
        # Check if the new division name already exists (excluding the current division)
        existing_division = db.execute("SELECT * FROM division WHERE name = ? AND id != ?", new_division_name, division_id)
        if existing_division:
            flash("Division name already exists.", "danger")
            return render_template("edit_division.html", title="Edit Division", project_name=app.config['PROJECT_NAME'], division=division[0])
        
        # Update the division name
        db.execute("UPDATE division SET name = ? WHERE id = ?", new_division_name, division_id)
        flash("Division updated successfully.", "success")
        return redirect("/division")
    
    return render_template("edit_division.html", title="Edit Division", project_name=app.config['PROJECT_NAME'], division=division[0])


@app.route("/division/delete/<int:division_id>", methods=["POST"])
def delete_division(division_id):
    """Delete division"""
    division = db.execute("SELECT * FROM division WHERE id = ?", division_id)
    
    if not division:
        flash("Division not found.", "danger")
        return redirect("/division")
    
    # Check if the division has any associated departments
    associated_departments = db.execute("SELECT COUNT(*) as count FROM department WHERE division_id = ?", division_id)[0]['count']
    
    if associated_departments > 0:
        flash("Cannot delete division. It has associated departments.", "danger")
        return redirect("/division")
    
    # Delete the division
    db.execute("DELETE FROM division WHERE id = ?", division_id)
    flash("Division deleted successfully.", "success")
    return redirect("/division")


@app.route("/department")
# @login_required
def department():
    return render_template("department.html", title="Department", project_name=app.config['PROJECT_NAME'])


@app.route("/team")
# @login_required
def team():
    return render_template("team.html", title="Team", project_name=app.config['PROJECT_NAME'])


@app.route("/employee")
# @login_required
def employee():
    return render_template("employee.html", title="Employee", project_name=app.config['PROJECT_NAME'])


@app.route("/role")
# @login_required
def role():
    return render_template("role.html", title="Role", project_name=app.config['PROJECT_NAME'])


@app.route("/leave")
# @login_required
def leave():
    return render_template("leave.html", title="Leave", project_name=app.config['PROJECT_NAME'])


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", title="Profile", project_name=app.config['PROJECT_NAME'])


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", title="Settings", project_name=app.config['PROJECT_NAME'])

@app.route("/sign_out")
def sign_out():
    """Log user out"""

    session.clear()

    return redirect("/")