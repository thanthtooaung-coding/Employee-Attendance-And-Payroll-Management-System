import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

from math import ceil
import datetime

# Configure application
app = Flask(__name__)

app.config['PROJECT_NAME'] = "VinnTrack"

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///attendance_management_system.db")


@app.context_processor
def inject_globals():
    """Inject global variables for all templates"""
    current_year = datetime.datetime.now().year
    return {
        'current_year': current_year,
        'project_name': app.config['PROJECT_NAME']
    }


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
            return render_template("login.html", title="Login")
        
        elif not password:
            flash("Please provide a password.", "danger")
            return render_template("login.html", title="Login")
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("Invalid email format. Please enter a valid email address.", "danger")
            return render_template("login.html", title="Login")

        rows = db.execute("SELECT * FROM employee WHERE email = ?", email)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            flash("Invalid email and/or password. Please try again.", "danger")
            return render_template("login.html", title="Login")

        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    return render_template("login.html", title="Login")

@app.route("/")
# @login_required
def index():
    return render_template("index.html", title="Dashboard")


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

    return render_template("division/division.html", 
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
            return render_template("division/add_division.html", title="Add Division")
        
        # Check if the division name already exists
        existing_division = db.execute("SELECT * FROM division WHERE name = ?", division_name)
        if existing_division:
            flash("Division name already exists.", "danger")
            return render_template("division/add_division.html", title="Add Division")
        
        db.execute("INSERT INTO division (name) VALUES (?)", division_name)
        flash("Division added successfully.", "success")
        return redirect("/division")
    
    return render_template("division/add_division.html", title="Add Division")


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
            return redirect(url_for("edit_division", division_id=division_id))
        
        # Check if the new division name already exists (excluding the current division)
        existing_division = db.execute("SELECT * FROM division WHERE name = ? AND id != ?", new_division_name, division_id)
        if existing_division:
            flash("Division name already exists.", "danger")
            return redirect(url_for("edit_division", division_id=division_id))
        
        # Update the division name
        db.execute("UPDATE division SET name = ? WHERE id = ?", new_division_name, division_id)
        flash("Division updated successfully.", "success")
        return redirect("/division")
    
    return render_template("division/edit_division.html", title="Edit Division", division=division[0])


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
    """Department List with Pagination"""

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    total_departments = db.execute("SELECT COUNT(*) as count FROM department")[0]['count']

    total_pages = ceil(total_departments / per_page)

    # Get paginated departments
    offset = (page - 1) * per_page
    departments = db.execute("""
        SELECT 
            d.id, 
            d.name,
            div.name AS division_name,
            (SELECT COUNT(*) FROM team WHERE department_id = d.id) AS team_count,
            COUNT(DISTINCT e.id) AS employee_count
        FROM department d
        LEFT JOIN division div ON d.division_id = div.id
        LEFT JOIN team t ON d.id = t.department_id
        LEFT JOIN employee e ON t.id = e.team_id
        GROUP BY d.id
        ORDER BY d.id
        LIMIT ? OFFSET ?
    """, per_page, offset)

    return render_template("department/department.html", 
                           title="Department", 
                           project_name=app.config['PROJECT_NAME'], 
                           departments=departments,
                           page=page,
                           total_pages=total_pages)


@app.route("/department/new", methods=["GET", "POST"])
def add_department():
    """Add new department"""

    if request.method == "POST":
        department_name = request.form.get("department_name")
        division_id = request.form.get("division_id")
        
        # Input validation
        if not department_name:
            flash("Department name is required.", "danger")
            return redirect("/department/new")
        
        if not division_id:
            flash("Division is required.", "danger")
            return redirect("/department/new")
        
        # Check if the division exists
        existing_division = db.execute("SELECT * FROM division WHERE id = ?", division_id)
        if not existing_division:
            flash("Selected division does not exist.", "danger")
            return redirect("/department/new")
        
        # Check if the department name already exists
        existing_department = db.execute("SELECT * FROM department WHERE name = ?", department_name)
        if existing_department:
            flash("Department name already exists.", "danger")
            return redirect("/department/new")
        
        db.execute("INSERT INTO department (name, division_id) VALUES (?, ?)", department_name, division_id)
        flash("Department added successfully.", "success")
        return redirect("/department")
    
    divisions = db.execute("SELECT id, name FROM division ORDER BY name")
    return render_template("department/add_department.html", title="Add Department", divisions=divisions)


@app.route("/department/edit/<int:department_id>", methods=["GET", "POST"])
def edit_department(department_id):
    """Edit department"""

    department = db.execute("SELECT * FROM department WHERE id = ?", department_id)
    
    if not department:
        flash("Department not found.", "danger")
        return redirect("/department")
    
    if request.method == "POST":
        new_department_name = request.form.get("department_name")
        new_division_id = request.form.get("division_id")

        # Input validation
        if not new_department_name:
            flash("Department name is required.", "danger")
            return redirect(url_for("edit_department", department_id=department_id))
        
        if not new_division_id:
            flash("Division is required.", "danger")
            return redirect(url_for("edit_department", department_id=department_id))
        
        # Check if the new division exists
        existing_division = db.execute("SELECT * FROM division WHERE id = ?", new_division_id)
        if not existing_division:
            flash("Selected division does not exist.", "danger")
            return redirect(url_for("edit_department", department_id=department_id))
        
        # Check if the new department name already exists (excluding the current department)
        existing_department = db.execute("SELECT * FROM department WHERE name = ? AND id != ?", new_department_name, department_id)
        if existing_department:
            flash("Department name already exists.", "danger")
            return redirect(url_for("edit_department", department_id=department_id))
        
        # Update the department
        db.execute("UPDATE department SET name = ?, division_id = ? WHERE id = ?", new_department_name, new_division_id, department_id)
        flash("Department updated successfully.", "success")
        return redirect("/department")
    
    divisions = db.execute("SELECT id, name FROM division ORDER BY name")
    return render_template("department/edit_department.html", title="Edit Department", department=department[0], divisions=divisions)


@app.route("/department/delete/<int:department_id>", methods=["POST"])
def delete_department(department_id):
    """Delete department"""

    department = db.execute("SELECT * FROM department WHERE id = ?", department_id)
    
    if not department:
        flash("Department not found.", "danger")
        return redirect("/department")
    
    # Check if the department has any associated teams
    associated_departments = db.execute("SELECT COUNT(*) as count FROM team WHERE department_id = ?", department_id)[0]['count']
    
    if associated_departments > 0:
        flash("Cannot delete department. It has associated departments.", "danger")
        return redirect("/department")
    
    # Delete the department
    db.execute("DELETE FROM department WHERE id = ?", department_id)
    flash("department deleted successfully.", "success")
    return redirect("/department")


@app.route("/team")
# @login_required
def team():
    """Team List with Pagination"""

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    # Get total number of teams
    total_teams = db.execute("SELECT COUNT(*) as count FROM team")[0]['count']

    # Calculate total pages
    total_pages = ceil(total_teams / per_page)

    # Get paginated teams
    offset = (page - 1) * per_page
    teams = db.execute(""" 
        SELECT 
            t.id,
            t.name,
            d.id AS department_id,
            d.name AS department_name,
            div.name AS division_name,
            COUNT(e.id) AS employee_count
        FROM team t
        LEFT JOIN department d ON t.department_id = d.id
        LEFT JOIN division div ON d.division_id = div.id
        LEFT JOIN employee e ON t.id = e.team_id
        GROUP BY t.id
        ORDER BY t.id
        LIMIT ? OFFSET ?
    """, per_page, offset)

    return render_template("team/team.html", 
                           title="Team", 
                           project_name=app.config['PROJECT_NAME'], 
                           teams=teams,
                           page=page,
                           total_pages=total_pages)


@app.route("/team/new", methods=["GET", "POST"])
def add_team():
    """Add new team"""

    if request.method == "POST":
        team_name = request.form.get("team_name")
        department_id = request.form.get("department_id")
        
        # Input validation
        if not team_name:
            flash("Team name is required.", "danger")
            return redirect("/team/new")
        
        if not department_id:
            flash("Department is required.", "danger")
            return redirect("/team/new")
        
        # Check if the department exists
        existing_department = db.execute("SELECT * FROM department WHERE id = ?", department_id)
        if not existing_department:
            flash("Selected department does not exist.", "danger")
            return redirect("/team/new")
        
        # Check if the team name already exists
        existing_team = db.execute("SELECT * FROM team WHERE name = ?", team_name)
        if existing_team:
            flash("Team name already exists.", "danger")
            return redirect("/team/new")
        
        db.execute("INSERT INTO team (name, department_id) VALUES (?, ?)", team_name, department_id)
        flash("team added successfully.", "success")
        return redirect("/team")
    
    departments = db.execute("SELECT id, name FROM department ORDER BY name")
    return render_template("team/add_team.html", title="Add Team", departments=departments)


@app.route("/team/edit/<int:team_id>", methods=["GET", "POST"])
def edit_team(team_id):
    """Edit team"""

    team = db.execute("SELECT * FROM team WHERE id = ?", team_id)
    return apology("TODO")


@app.route("/team/delete/<int:team_id>", methods=["POST"])
def delete_team(team_id):
    """Delete team"""
    
    team = db.execute("SELECT * FROM team WHERE id = ?", team_id)
    return apology("TODO")


@app.route("/employee")
# @login_required
def employee():
    return render_template("employee.html", title="Employee")


@app.route("/role")
# @login_required
def role():
    return render_template("role.html", title="Role")


@app.route("/leave")
# @login_required
def leave():
    return render_template("leave.html", title="Leave")


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", title="Profile")


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", title="Settings")

@app.route("/sign_out")
def sign_out():
    """Log user out"""

    session.clear()

    return redirect("/")