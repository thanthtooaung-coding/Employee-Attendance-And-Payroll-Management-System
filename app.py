import os
import datetime
import re
import io
import csv

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for, send_file
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from helpers import apology, login_required, generate_readable_password, role_required, send_email, usd

from math import ceil
from datetime import date, timedelta
from io import BytesIO


# Configure application
app = Flask(__name__)
app.config.from_object(Config)

# Custom filter
app.jinja_env.filters["usd"] = usd

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

        user = rows[0]
        session["user_id"] = rows[0]["id"]

        # Fetch role title
        role_row = db.execute("SELECT title FROM role WHERE id = ?", user["role_id"])
        role_title = role_row[0]["title"] if role_row else "Unknown Role"

        team_row = db.execute("SELECT id, name, department_id FROM team WHERE id = ?", user["team_id"])

        if team_row:
            team_id = team_row[0]["id"]
            team_name = team_row[0]["name"]
            department_id = team_row[0]["department_id"]

            department_row = db.execute("SELECT name FROM department WHERE id = ?", department_id)
            department_name = department_row[0]["name"] if department_row else "Unknown Department"
        else:
            team_id = "Unknown Team"
            team_name = "Unknown Team"
            department_name = "Unknown Department"

        position_row = db.execute("SELECT name FROM position WHERE id = ?", user["position_id"])
        position_name = position_row[0]["name"] if position_row else "Unknown Position"

        # Store user's name and role in session for later use
        session["user_name"] = f"{user['first_name']} {user['last_name']}"
        session["user_role"] = role_title
        session["user_email"] = user["email"]
        session["employee_id"] = user["id"]
        session["team"] = team_name
        session["department"] = department_name
        session["position"] = position_name

        # Redirect user to home page or profile page based on their roles
        if session.get('user_role') == "Admin":
            return redirect("/")
        else:
            return redirect("/profile")

    return render_template("login.html", title="Login")

@app.route("/")
@login_required
@role_required(["Admin"])
def index():
    """Dashboard"""

    # Get counts for dashboard
    division_count = db.execute("SELECT COUNT(*) as count FROM division")[0]['count']
    department_count = db.execute("SELECT COUNT(*) as count FROM department")[0]['count']
    team_count = db.execute("SELECT COUNT(*) as count FROM team")[0]['count']
    employee_count = db.execute("SELECT COUNT(*) as count FROM employee")[0]['count']
    # Get counts for last month
    division_count_last_month = db.execute("""
        SELECT COUNT(*) as count 
        FROM division 
        WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', DATE('now', '-1 month'))
    """)[0]['count']

    department_count_last_month = db.execute("""
        SELECT COUNT(*) as count 
        FROM department 
        WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', DATE('now', '-1 month'))
    """)[0]['count']

    team_count_last_month = db.execute("""
        SELECT COUNT(*) as count 
        FROM team 
        WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', DATE('now', '-1 month'))
    """)[0]['count']

    employee_count_last_month = db.execute("""
        SELECT COUNT(*) as count 
        FROM employee 
        WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', DATE('now', '-1 month'))
    """)[0]['count']

    division_change = division_count - division_count_last_month
    department_change = department_count - department_count_last_month
    team_change = team_count - team_count_last_month
    employee_change = employee_count - employee_count_last_month

    today = date.today()

    leave_count = db.execute("""
        SELECT COUNT(DISTINCT employee_id) as count 
        FROM leave_request 
        WHERE ? BETWEEN start_date AND end_date 
        AND status = 'Approved'
    """, today)[0]['count']

    total_employees = db.execute("SELECT COUNT(*) as count FROM employee")[0]['count']

    present_count = total_employees - leave_count

    pending_count = db.execute("""
        SELECT COUNT(DISTINCT employee_id) as count 
        FROM leave_request 
        WHERE ? BETWEEN start_date AND end_date 
        AND status = 'Pending'
    """, today)[0]['count']

    total_employees = present_count + leave_count + pending_count
    present_rate = (present_count / total_employees) * 100 if total_employees > 0 else 0
    leave_rate = (leave_count / total_employees) * 100 if total_employees > 0 else 0
    pending_rate = (pending_count / total_employees) * 100 if total_employees > 0 else 0
    
    first_day_of_month = date.today().replace(day=1)
    last_day_of_month = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    total_salary = db.execute("""
        WITH vacation_days AS (
            SELECT employee_id, 
                   SUM(JULIANDAY(MIN(?, end_date)) - JULIANDAY(MAX(?, start_date)) + 1) as vacation_days
            FROM leave_request
            WHERE leave_type = 'Vacation' 
              AND status = 'Approved'
              AND start_date <= ?
              AND end_date >= ?
            GROUP BY employee_id
        )
        SELECT COALESCE(SUM(
            p.salary * (1 - COALESCE(v.vacation_days, 0) * 0.001)
        ), 0) as total_salary
        FROM employee e
        JOIN position p ON e.position_id = p.id
        LEFT JOIN vacation_days v ON e.id = v.employee_id
    """, last_day_of_month, first_day_of_month, last_day_of_month, first_day_of_month)[0]['total_salary']

    from datetime import datetime

    today = datetime.today()
    # Generate the past 7 days (from 6 days ago to today)
    days_of_week = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    # Generate the corresponding day names (Monday, Tuesday, etc.)
    day_labels = [(today - timedelta(days=i)).strftime('%A') for i in range(6, -1, -1)]

    attendance_data = []
    leave_data = []

    # Loop through each day and fetch data
    for day in days_of_week:
        present_count = db.execute("""
            SELECT COUNT(*) as count
            FROM employee e
            WHERE e.id NOT IN (
                SELECT employee_id
                FROM leave_request
                WHERE ? BETWEEN start_date AND end_date
                AND status = 'Approved'
            )
        """, day)[0]['count']

        leave_count = db.execute("""
            SELECT COUNT(*) as count
            FROM leave_request
            WHERE ? BETWEEN start_date AND end_date
            AND status = 'Approved'
        """, day)[0]['count']

        attendance_data.append(present_count)
        leave_data.append(leave_count)
    
    payroll_data = []
    months = [(today.replace(day=1) - timedelta(days=30 * i)).strftime('%Y-%m') for i in range(6, 0, -1)]
    month_names = [(today.replace(day=1) - timedelta(days=30 * i)).strftime('%B') for i in range(6, 0, -1)] 

    for month in months:
        total_payroll = db.execute("""
            WITH vacation_days AS (
                SELECT employee_id, 
                    SUM(JULIANDAY(MIN(DATE(?, 'start of month', '+1 month', '-1 day'), end_date)) - 
                        JULIANDAY(MAX(DATE(?, 'start of month'), start_date)) + 1) as vacation_days
                FROM leave_request
                WHERE leave_type = 'Vacation'
                AND status = 'Approved'
                AND start_date <= DATE(?, 'start of month', '+1 month', '-1 day')
                AND end_date >= DATE(?, 'start of month')
                GROUP BY employee_id
            )
            SELECT COALESCE(SUM(
                p.salary * (1 - COALESCE(v.vacation_days, 0) * 0.001)
            ), 0) as total_salary
            FROM employee e
            JOIN position p ON e.position_id = p.id
            LEFT JOIN vacation_days v ON e.id = v.employee_id
        """, month, month, month, month)[0]['total_salary']

        payroll_data.append(total_payroll)

    recent_leave_requests = db.execute("""
        SELECT e.first_name || ' ' || e.last_name as name, 
               lr.leave_type as type, 
               (JULIANDAY(lr.end_date) - JULIANDAY(lr.start_date) + 1) as duration
        FROM leave_request lr
        JOIN employee e ON lr.employee_id = e.id
        ORDER BY lr.created_at DESC
        LIMIT 2
    """)

    first_day_of_next_month = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
    last_day_of_next_month = (first_day_of_next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    next_payroll_date = last_day_of_next_month.strftime("%B %d, %Y")

    estimated_salary = db.execute("""
        WITH vacation_days AS (
            SELECT employee_id, 
                   SUM(JULIANDAY(MIN(?, end_date)) - JULIANDAY(MAX(?, start_date)) + 1) as vacation_days
            FROM leave_request
            WHERE leave_type = 'Vacation' 
              AND status = 'Approved'
              AND start_date <= ?
              AND end_date >= ?
            GROUP BY employee_id
        )
        SELECT COALESCE(SUM(
            p.salary * (1 - COALESCE(v.vacation_days, 0) * 0.001)
        ), 0) as estimated_salary
        FROM employee e
        JOIN position p ON e.position_id = p.id
        LEFT JOIN vacation_days v ON e.id = v.employee_id
    """, last_day_of_next_month, first_day_of_next_month, last_day_of_next_month, first_day_of_next_month)[0]['estimated_salary']
    
    return render_template("index.html", 
                           title="Dashboard",
                           division_count=division_count,
                           department_count=department_count,
                           team_count=team_count,
                           employee_count=employee_count,
                           division_change=division_change,
                           department_change=department_change,
                           team_change=team_change,
                           employee_change=employee_change,
                           present_count=present_count,
                           present_rate=present_rate,
                           leave_count=leave_count,
                           leave_rate=leave_rate,
                           pending_count=pending_count,
                           pending_rate=pending_rate,
                           total_salary=total_salary,
                           day_labels=day_labels,
                           attendance_data=attendance_data,
                           leave_data=leave_data,
                           payroll_data=payroll_data,
                           recent_leave_requests=recent_leave_requests,
                           next_payroll_date=next_payroll_date,
                           estimated_salary=estimated_salary,
                           month_names=month_names)


@app.route("/division")
@login_required
@role_required(["Admin"])
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
                           items=divisions,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           current_page='division',
                           add_new_url='add_division',
                           edit_url='edit_division',
                           delete_url='delete_division')


@app.route("/division/new", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
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
@login_required
@role_required(["Admin"])
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
@login_required
@role_required(["Admin"])
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
@login_required
@role_required(["Admin"])
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
                           items=departments,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           current_page='department',
                           add_new_url='add_department',
                           edit_url='edit_department',
                           delete_url='delete_department')


@app.route("/department/new", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
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
@login_required
@role_required(["Admin"])
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
@login_required
@role_required(["Admin"])
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
    flash("Department deleted successfully.", "success")
    return redirect("/department")


@app.route("/team")
@login_required
@role_required(["Admin"])
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
                           items=teams,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           current_page='team',
                           add_new_url='add_team',
                           edit_url='edit_team',
                           delete_url='delete_team')


@app.route("/team/new", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
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
        flash("Team added successfully.", "success")
        return redirect("/team")
    
    departments = db.execute("SELECT id, name FROM department ORDER BY name")
    return render_template("team/add_team.html", title="Add Team", departments=departments)


@app.route("/team/edit/<int:team_id>", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def edit_team(team_id):
    """Edit team"""

    team = db.execute("SELECT * FROM team WHERE id = ?", team_id)
    
    if not team:
        flash("Team not found.", "danger")
        return redirect("/team")
    
    if request.method == "POST":
        new_team_name = request.form.get("team_name")
        new_department_id = request.form.get("department_id")

        # Input validation
        if not new_team_name:
            flash("Team name is required.", "danger")
            return redirect(url_for("edit_team", team_id=team_id))
        
        if not new_department_id:
            flash("Department is required.", "danger")
            return redirect(url_for("edit_team", team_id=team_id))
        
        # Check if the new department exists
        existing_department = db.execute("SELECT * FROM department WHERE id = ?", new_department_id)
        if not existing_department:
            flash("Selected department does not exist.", "danger")
            return redirect(url_for("edit_team", team_id=team_id))
        
        # Check if the new team name already exists (excluding the current team)
        existing_team = db.execute("SELECT * FROM team WHERE name = ? AND id != ?", new_team_name, team_id)
        if existing_team:
            flash("Team name already exists.", "danger")
            return redirect(url_for("edit_team", team_id=team_id))
        
        # Update the team
        db.execute("UPDATE team SET name = ?, department_id = ? WHERE id = ?", new_team_name, new_department_id, team_id)
        flash("Team updated successfully.", "success")
        return redirect("/team")
    
    departments = db.execute("SELECT id, name FROM department ORDER BY name")
    return render_template("team/edit_team.html", title="Edit Team", team=team[0], departments=departments)


@app.route("/team/delete/<int:team_id>", methods=["POST"])
@login_required
@role_required(["Admin"])
def delete_team(team_id):
    """Delete team"""

    team = db.execute("SELECT * FROM team WHERE id = ?", team_id)
    
    if not team:
        flash("Team not found.", "danger")
        return redirect("/team")
    
    # Check if the team has any associated employees
    associated_teams = db.execute("SELECT COUNT(*) as count FROM employee WHERE team_id = ?", team_id)[0]['count']
    
    if associated_teams > 0:
        flash("Cannot delete team. It has associated teams.", "danger")
        return redirect("/team")
    
    # Delete the team
    db.execute("DELETE FROM team WHERE id = ?", team_id)
    flash("Team deleted successfully.", "success")
    return redirect("/team")


@app.route("/employee")
@login_required
@role_required(["Admin"])
def employee():
    """Employee List with Pagination"""
    
    page = request.args.get('page', 1, type=int)  # Current page, defaults to 1
    per_page = 5  # Number of employees to display per page

    # Get total number of employees
    total_employees = db.execute("SELECT COUNT(*) as count FROM employee")[0]['count']
    total_pages = ceil(total_employees / per_page)

    # Get paginated employees
    offset = (page - 1) * per_page
    employees = db.execute("""
        SELECT 
            e.id,
            e.first_name || ' ' || e.last_name AS full_name,
            e.email,
            t.name AS team_name,
            d.name AS department_name,
            div.name AS division_name,
            r.title AS role_name
        FROM employee e
        LEFT JOIN team t ON e.team_id = t.id
        LEFT JOIN department d ON t.department_id = d.id
        LEFT JOIN division div ON d.division_id = div.id
        LEFT JOIN role r ON e.role_id = r.id
        ORDER BY e.id
        LIMIT ? OFFSET ?
    """, per_page, offset)

    return render_template("employee/employee.html", 
                           title="Employee", 
                           items=employees, 
                           page=page, 
                           per_page=per_page, 
                           total_pages=total_pages,
                           current_page='employee',
                           add_new_url='add_employee',
                           edit_url='edit_employee',
                           delete_url='delete_employee')


@app.route("/employee/new", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def add_employee():
    """Add new employee"""
    
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        team_id = request.form.get("team_id")
        position_id = request.form.get("position_id")
        role_id = request.form.get("role_id")
        
        password = generate_readable_password()
        hash = generate_password_hash(password)

        # Input validation
        if not first_name or not last_name:
            flash("First and Last name are required.", "danger")
            return redirect("/employee/new")
        
        if not email:
            flash("Email is required.", "danger")
            return redirect("/employee/new")
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash("Invalid email format. Please enter a valid email address.", "danger")
            return redirect("/employee/new")
        
        if not team_id:
            flash("Team is required.", "danger")
            return redirect("/employee/new")
        
        if not role_id:
            flash("Role is required.", "danger")
            return redirect("/employee/new")
        
        # Check if the team exists
        existing_team = db.execute("SELECT * FROM team WHERE id = ?", team_id)
        if not existing_team:
            flash("Selected team does not exist.", "danger")
            return redirect("/employee/new")
        
        # Check if the position exists
        existing_position = db.execute("SELECT * FROM position WHERE id = ?", position_id)
        if not existing_position:
            flash("Selected position does not exist.", "danger")
            return redirect("/employee/new")
        
        # Check if the role exists
        existing_role = db.execute("SELECT * FROM role WHERE id = ?", role_id)
        if not existing_role:
            flash("Selected role does not exist.", "danger")
            return redirect("/employee/new")        
        
        # Check if email already exists
        existing_employee = db.execute("SELECT * FROM employee WHERE email = ?", email)
        if existing_employee:
            flash("An employee with this email already exists.", "danger")
            return redirect("/employee/new")
        
        # Insert the new employee into the database
        db.execute("""
            INSERT INTO employee (first_name, last_name, email, position_id, team_id, role_id, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, first_name, last_name, email, position_id, team_id, role_id, hash)

        send_email(email, password)
        
        flash(f"Employee added successfully. The generated password is: {password}", "success")
        return redirect("/employee")
    
    # Fetch teams and roles to populate the dropdowns
    teams = db.execute("SELECT id, name FROM team ORDER BY name")
    positions = db.execute("SELECT id, name FROM position ORDER BY name")
    roles = db.execute("SELECT id, title FROM role ORDER BY title")
    
    return render_template("employee/add_employee.html", 
                           title="Add Employee", 
                           teams=teams,
                           positions=positions,
                           roles=roles)


@app.route("/employee/edit/<int:employee_id>", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def edit_employee(employee_id):
    """Edit employee"""

    employee = db.execute("""
        SELECT * FROM employee WHERE id = ?
    """, employee_id)

    if not employee:
        flash("Employee not found.", "danger")
        return redirect("/employee")

    employee = employee[0]

    if request.method == "POST":
        new_first_name = request.form.get("first_name")
        new_last_name = request.form.get("last_name")
        new_email = request.form.get("email")
        new_team_id = request.form.get("team_id")
        new_role_id = request.form.get("role_id")
        new_position_id = request.form.get("position_id")

        # Input validation
        if not new_first_name or not new_last_name:
            flash("First and Last name are required.", "danger")
            return redirect(url_for("edit_employee", employee_id=employee_id))
        
        if not new_email:
            flash("Email is required.", "danger")
            return redirect(url_for("edit_employee", employee_id=employee_id))

        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, new_email):
            flash("Invalid email format. Please enter a valid email address.", "danger")
            return redirect(url_for("edit_employee", employee_id=employee_id))

        # Check if the team exists
        existing_team = db.execute("SELECT * FROM team WHERE id = ?", new_team_id)
        if not existing_team:
            flash("Selected team does not exist.", "danger")
            return redirect(url_for("edit_employee", employee_id=employee_id))
        
        # Check if the position exists
        existing_position = db.execute("SELECT * FROM position WHERE id = ?", new_position_id)
        if not existing_position:
            flash("Selected position does not exist.", "danger")
            return redirect(url_for("edit_employee", employee_id=employee_id))

        # Check if the role exists
        existing_role = db.execute("SELECT * FROM role WHERE id = ?", new_role_id)
        if not existing_role:
            flash("Selected role does not exist.", "danger")
            return redirect(url_for("edit_employee", employee_id=employee_id))

        # Check if the email already exists for another employee
        existing_employee = db.execute("SELECT * FROM employee WHERE email = ? AND id != ?", new_email, employee_id)
        if existing_employee:
            flash("An employee with this email already exists.", "danger")
            return redirect(url_for("edit_employee", employee_id=employee_id))

        # Update the employee
        db.execute("""
            UPDATE employee
            SET first_name = ?, last_name = ?, email = ?, team_id = ?, position_id = ?, role_id = ?
            WHERE id = ?
        """, new_first_name, new_last_name, new_email, new_team_id, new_position_id, new_role_id, employee_id)

        flash("Employee updated successfully.", "success")
        return redirect("/employee")

    # Fetch teams and roles to populate the dropdowns
    teams = db.execute("SELECT id, name FROM team ORDER BY name")
    roles = db.execute("SELECT id, title FROM role ORDER BY title")
    positions = db.execute("SELECT id, name FROM position ORDER BY name")

    return render_template("employee/edit_employee.html", 
                           title="Edit Employee", 
                           employee=employee, 
                           teams=teams,
                           positions=positions,
                           roles=roles)


@app.route("/employee/delete/<int:employee_id>", methods=["POST"])
@login_required
@role_required(["Admin"])
def delete_employee(employee_id):
    """Delete employee"""

    employee = db.execute("SELECT * FROM employee WHERE id = ?", employee_id)
    
    if not employee:
        flash("Employee not found.", "danger")
        return redirect("/employee")
    
    # Delete the employee
    db.execute("DELETE FROM employee WHERE id = ?", employee_id)
    
    flash("Employee deleted successfully.", "success")
    return redirect("/employee")

@app.route("/position")
@login_required
@role_required(["Admin"])
def position():
    """Position List with Pagination"""

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    total_positions = db.execute("SELECT COUNT(*) as count FROM position")[0]['count']

    total_pages = ceil(total_positions / per_page)

    # Get paginated positions
    offset = (page - 1) * per_page
    positions = db.execute("""
    SELECT 
        p.id,
        p.name,
        p.salary,
        COUNT(e.id) AS employee_count
        FROM position p
        LEFT JOIN employee e ON p.id = e.position_id
        GROUP BY p.id
        ORDER BY p.id
        LIMIT ? OFFSET ?
    """, per_page, offset)


    return render_template("position/position.html", 
                           title="Position", 
                           items=positions,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           current_page='position',
                           add_new_url='add_position',
                           edit_url='edit_position',
                           delete_url='delete_position')


@app.route("/position/new", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def add_position():    
    """Add new position"""

    if request.method == "POST":
        position_name = request.form.get("position_name")
        salary = request.form.get("salary")
        
        # Input validation
        if not position_name:
            flash("Position name is required.", "danger")
            return render_template("position/add_position.html", title="Add position")
        
        if not salary:
            flash("Salary is required.", "danger")
            return render_template("position/add_position.html", title="Add position")
        
        if not salary.isdigit() or int(salary) <= 0:
            flash("Invalid salary format.", "danger")
            return render_template("position/add_position.html", title="Add position")
        
        # Check if the position name already exists
        existing_position = db.execute("SELECT * FROM position WHERE name = ?", position_name)
        if existing_position:
            flash("Position name already exists.", "danger")
            return render_template("position/add_position.html", title="Add Position")
        
        db.execute("INSERT INTO position (name, salary) VALUES (?, ?)", position_name, salary)
        flash("Position added successfully.", "success")
        return redirect("/position")
    
    return render_template("position/add_position.html", title="Add Position")


@app.route("/position/edit/<int:position_id>", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def edit_position(position_id):
    """Edit position"""

    position = db.execute("SELECT * FROM position WHERE id = ?", position_id)
    
    if not position:
        flash("Position not found.", "danger")
        return redirect("/position")
    
    if request.method == "POST":
        new_position_name = request.form.get("position_name")
        new_salary = request.form.get("salary")

        # Input validation
        if not new_position_name:
            flash("Position name is required.", "danger")
            return redirect(url_for("edit_position", position_id=position_id))
        
        if not new_salary:
            flash("Salary is required.", "danger")
            return redirect(url_for("edit_position", position_id=position_id))
        
        if not new_salary.isdigit() or int(new_salary) <= 0:
            flash("Invalid salary format.", "danger")
            return redirect(url_for("edit_position", position_id=position_id))
        
        # Check if the new position name already exists (excluding the current position)
        existing_position = db.execute("SELECT * FROM position WHERE name = ? AND id != ?", new_position_name, position_id)
        if existing_position:
            flash("Position name already exists.", "danger")
            return redirect(url_for("edit_position", position_id=position_id))
        
        # Update the position name
        db.execute("UPDATE position SET name = ?, salary = ? WHERE id = ?", new_position_name, new_salary, position_id)
        flash("Position updated successfully.", "success")
        return redirect("/position")
    
    return render_template("position/edit_position.html", title="Edit Position", position=position[0])


@app.route("/position/delete/<int:position_id>", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def delete_position(position_id):
    """Delete position"""

    position = db.execute("SELECT * FROM position WHERE id = ?", position_id)
    
    if not position:
        flash("Position not found.", "danger")
        return redirect("/position")
    
    # Check if the position has any associated employees
    associated_positions = db.execute("SELECT COUNT(*) as count FROM employee WHERE position_id = ?", position_id)[0]['count']
    
    if associated_positions > 0:
        flash("Cannot delete position. It has associated positions.", "danger")
        return redirect("/position")
    
    # Delete the position
    db.execute("DELETE FROM position WHERE id = ?", position_id)
    flash("Position deleted successfully.", "success")
    return redirect("/position")


@app.route("/role")
@login_required
@role_required(["Admin"])
def role():
    """Role List with Pagination"""

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    total_roles = db.execute("SELECT COUNT(*) as count FROM role")[0]['count']

    total_pages = ceil(total_roles / per_page)

    # Get paginated roles
    offset = (page - 1) * per_page
    roles = db.execute("""
    SELECT 
        r.id,
        r.title,
        COUNT(e.id) AS employee_count
        FROM role r
        LEFT JOIN employee e ON r.id = e.role_id
        GROUP BY r.id
        ORDER BY r.id
        LIMIT ? OFFSET ?
    """, per_page, offset)


    return render_template("role/role.html", 
                           title="Role", 
                           items=roles,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           current_page='role',
                           add_new_url='add_role',
                           edit_url='edit_role',
                           delete_url='delete_role')


@app.route("/role/new", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def add_role():    
    """Add new role"""

    if request.method == "POST":
        role_name = request.form.get("role_name")
        
        # Input validation
        if not role_name:
            flash("Role name is required.", "danger")
            return render_template("role/add_role.html", title="Add role")
        
        # Check if the role name already exists
        existing_role = db.execute("SELECT * FROM role WHERE title = ?", role_name)
        if existing_role:
            flash("Role name already exists.", "danger")
            return render_template("role/add_role.html", title="Add Role")
        
        db.execute("INSERT INTO role (title) VALUES (?)", role_name)
        flash("Role added successfully.", "success")
        return redirect("/role")
    
    return render_template("role/add_role.html", title="Add Role")


@app.route("/role/edit/<int:role_id>", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def edit_role(role_id):
    """Edit role"""

    role = db.execute("SELECT * FROM role WHERE id = ?", role_id)
    
    if not role:
        flash("Role not found.", "danger")
        return redirect("/role")
    
    if request.method == "POST":
        new_role_name = request.form.get("role_name")

        # Input validation
        if not new_role_name:
            flash("Role name is required.", "danger")
            return redirect(url_for("edit_role", role_id=role_id))
        
        # Check if the new role name already exists (excluding the current role)
        existing_role = db.execute("SELECT * FROM role WHERE title = ? AND id != ?", new_role_name, role_id)
        if existing_role:
            flash("Role name already exists.", "danger")
            return redirect(url_for("edit_role", role_id=role_id))
        
        # Update the role name
        db.execute("UPDATE role SET title = ? WHERE id = ?", new_role_name, role_id)
        flash("Role updated successfully.", "success")
        return redirect("/role")
    
    return render_template("role/edit_role.html", title="Edit Role", role=role[0])


@app.route("/role/delete/<int:role_id>", methods=["GET", "POST"])
@login_required
@role_required(["Admin"])
def delete_role(role_id):
    """Delete role"""

    role = db.execute("SELECT * FROM role WHERE id = ?", role_id)
    
    if not role:
        flash("Role not found.", "danger")
        return redirect("/role")
    
    # Check if the role has any associated employees
    associated_roles = db.execute("SELECT COUNT(*) as count FROM employee WHERE role_id = ?", role_id)[0]['count']
    
    if associated_roles > 0:
        flash("Cannot delete role. It has associated roles.", "danger")
        return redirect("/role")
    
    # Delete the role
    db.execute("DELETE FROM role WHERE id = ?", role_id)
    flash("Role deleted successfully.", "success")
    return redirect("/role")


@app.route("/leave")
@login_required
@role_required(["Admin"])
def leave():
    """Leave List with Pagination"""

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    total_leaves = db.execute("SELECT COUNT(*) as count FROM leave_request")[0]['count']
    total_pages = ceil(total_leaves / per_page)

    offset = (page - 1) * per_page
    leaves = db.execute("""
        SELECT 
            lr.id, 
            e.first_name || ' ' || e.last_name AS employee_name,
            lr.start_date,
            lr.end_date,
            lr.leave_type,
            lr.status
        FROM leave_request lr
        JOIN employee e ON lr.employee_id = e.id
        ORDER BY lr.start_date DESC
        LIMIT ? OFFSET ?
    """, per_page, offset)

    return render_template("leave/leave.html", 
                           title="Leave Requests", 
                           items=leaves,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           current_page='leave',
                           add_new_url='add_leave',
                           edit_url='edit_leave',
                           delete_url='delete_leave')


@app.route("/leave/new", methods=["GET", "POST"])
@login_required
def add_leave():
    """Add new leave request"""
    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        leave_type = request.form.get("leave_type")
        reason = request.form.get("reason")

        if not all([employee_id, start_date, end_date, leave_type, reason]):
            flash("All fields are required.", "danger")
            return redirect(url_for("add_leave"))

        db.execute("""
            INSERT INTO leave_request (employee_id, start_date, end_date, leave_type, reason, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        """, employee_id, start_date, end_date, leave_type, reason)

        flash("Leave request submitted successfully.", "success")
        if session.get('user_role') == "Admin":
            return redirect("/leave")
        else:
            return redirect("/my_leave_requests")

    employees = db.execute("SELECT id, first_name || ' ' || last_name AS name FROM employee ORDER BY name")
    return render_template("leave/add_leave.html", title="Leave Request", employees=employees)

@app.route("/leave/edit/<int:leave_id>", methods=["GET", "POST"])
@login_required
def edit_leave(leave_id):
    """Edit leave request"""
    leave = db.execute("SELECT * FROM leave_request WHERE id = ?", leave_id)
    
    if not leave:
        flash("Leave request not found.", "danger")
        return redirect("/leave")

    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        leave_type = request.form.get("leave_type")
        reason = request.form.get("reason")
        status = request.form.get("status")

        if not all([start_date, end_date, leave_type, reason, status]):
            flash("All fields are required.", "danger")
            return redirect(url_for("edit_leave", leave_id=leave_id))

        db.execute("""
            UPDATE leave_request
            SET start_date = ?, end_date = ?, leave_type = ?, reason = ?, status = ?
            WHERE id = ?
        """, start_date, end_date, leave_type, reason, status, leave_id)

        flash("Leave request updated successfully.", "success")
        return redirect("/leave")

    employees = db.execute("SELECT id, first_name || ' ' || last_name AS name FROM employee ORDER BY name")
    return render_template("leave/edit_leave.html", title="Edit Leave Request", leave=leave[0], employees=employees)

@app.route("/leave/delete/<int:leave_id>", methods=["POST"])
@login_required
@role_required(["Admin"])
def delete_leave(leave_id):
    """Delete leave request"""
    leave = db.execute("SELECT * FROM leave_request WHERE id = ?", leave_id)
    
    if not leave:
        flash("Leave request not found.", "danger")
        return redirect("/leave")

    db.execute("DELETE FROM leave_request WHERE id = ?", leave_id)
    flash("Leave request deleted successfully.", "success")
    return redirect("/leave")


@app.route("/payroll_details")
@login_required
@role_required(["Admin"])
def payroll_details():
    """Show detailed payroll information for the next payroll cycle."""

    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    total_payrolls = db.execute("SELECT COUNT(*) as count FROM employee")[0]['count']
    
    total_pages = ceil(total_payrolls / per_page)
    offset = (page - 1) * per_page

    first_day_of_next_month = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
    last_day_of_next_month = (first_day_of_next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)       
    
    payroll_details = db.execute("""
        WITH vacation_days AS (
            SELECT employee_id, 
                   SUM(JULIANDAY(MIN(?, end_date)) - JULIANDAY(MAX(?, start_date)) + 1) as vacation_days
            FROM leave_request
            WHERE leave_type = 'Vacation' 
              AND status = 'Approved'
              AND start_date <= ?
              AND end_date >= ?
            GROUP BY employee_id
        )
        SELECT e.first_name || ' ' || e.last_name as employee_name, 
               p.name as position, 
               p.salary as base_salary, 
               COALESCE(v.vacation_days, 0) * 0.001 * p.salary as deductions,
               p.salary * (1 - COALESCE(v.vacation_days, 0) * 0.001) as final_salary
        FROM employee e
        JOIN position p ON e.position_id = p.id
        LEFT JOIN vacation_days v ON e.id = v.employee_id
        LIMIT ? OFFSET ?
    """, last_day_of_next_month, first_day_of_next_month, last_day_of_next_month, first_day_of_next_month, per_page, offset)

    # Calculate total payroll
    total_payroll = sum([payroll['final_salary'] for payroll in payroll_details])

    # Format next payroll date
    next_payroll_date = last_day_of_next_month.strftime("%B %d, %Y")

    return render_template("others/payroll_details.html",
                           title="Payroll Details", 
                           items=payroll_details, 
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           current_page='payroll_details',
                           total_payroll=total_payroll, 
                           next_payroll_date=next_payroll_date,
                           add_new_url='download_payroll',
                           edit_url='download_payroll',
                           delete_url='download_payroll')


@app.route("/download_payroll")
@login_required
@role_required(["Admin"])
def download_payroll():
    """Download payroll details as an Excel file."""

    first_day_of_next_month = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1)
    last_day_of_next_month = (first_day_of_next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)  
    
    payroll_details = db.execute("""
        WITH vacation_days AS (
            SELECT employee_id, 
                   SUM(JULIANDAY(MIN(?, end_date)) - JULIANDAY(MAX(?, start_date)) + 1) as vacation_days
            FROM leave_request
            WHERE leave_type = 'Vacation' 
              AND status = 'Approved'
              AND start_date <= ?
              AND end_date >= ?
            GROUP BY employee_id
        )
        SELECT e.first_name || ' ' || e.last_name as employee_name, 
               p.name as position, 
               p.salary as base_salary, 
               COALESCE(v.vacation_days, 0) * 0.001 * p.salary as deductions,
               p.salary * (1 - COALESCE(v.vacation_days, 0) * 0.001) as final_salary
        FROM employee e
        JOIN position p ON e.position_id = p.id
        LEFT JOIN vacation_days v ON e.id = v.employee_id
    """, last_day_of_next_month, first_day_of_next_month, last_day_of_next_month, first_day_of_next_month)

    import pandas as pd    

    df = pd.DataFrame(payroll_details)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Payroll Details')

    output.seek(0)
    
    return send_file(output, download_name='Payroll Details.xlsx', as_attachment=True)


@app.route("/generate_report")
@login_required
@role_required(["Admin"])
def generate_report():
    # Fetch payroll data for the current month

    first_day_of_month = date.today().replace(day=1)
    last_day_of_month = (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    payroll_data = db.execute("""
        WITH leave_info AS (
            SELECT 
                e.id as employee_id,
                lr.leave_type,
                SUM(JULIANDAY(MIN(?, lr.end_date)) - JULIANDAY(MAX(?, lr.start_date)) + 1) as leave_days
            FROM employee e
            LEFT JOIN leave_request lr ON e.id = lr.employee_id 
            WHERE lr.status = 'Approved'
                AND lr.start_date <= ?
                AND lr.end_date >= ?
            GROUP BY e.id, lr.leave_type
        )
        SELECT 
            e.id as employee_id,
            e.first_name || ' ' || e.last_name as employee_name,
            p.salary,
            COALESCE(SUM(CASE WHEN li.leave_type = 'Vacation' THEN li.leave_days ELSE 0 END), 0) as vacation_days,
            COALESCE(SUM(CASE WHEN li.leave_type = 'Sick' THEN li.leave_days ELSE 0 END), 0) as sick_days,
            COALESCE(SUM(CASE WHEN li.leave_type NOT IN ('Vacation', 'Sick') THEN li.leave_days ELSE 0 END), 0) as other_leave_days,
            GROUP_CONCAT(DISTINCT li.leave_type) as leave_types
        FROM employee e
        JOIN position p ON e.position_id = p.id
        LEFT JOIN leave_info li ON e.id = li.employee_id
        GROUP BY e.id
        ORDER BY e.last_name, e.first_name
    """, last_day_of_month, first_day_of_month, last_day_of_month, first_day_of_month)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee Name', 'Salary', 'Vacation Days', 'Sick Days', 'Other Leave Days', 'Leave Types'])

    for row in payroll_data:
        writer.writerow([
            row['employee_name'],
            row['salary'],
            row['vacation_days'],
            row['sick_days'],
            row['other_leave_days'],
            row['leave_types'] or 'None'
        ])
    
    output.seek(0)
    
    # Return CSV as downloadable file
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype="text/csv", 
        as_attachment=True,
        download_name=f"payroll_report_{date.today().strftime('%Y-%m-%d')}.csv"
    )


@app.route("/generate_attendance_log")
@login_required
@role_required(["Admin"])
def generate_attendance_log():
    """Generate attendance log CSV for the current month"""

    today = date.today()
    year = today.year
    month = today.month

    first_day_of_month = today.replace(day=1)
    last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    attendance_data = db.execute("""
        SELECT e.id as employee_id,
               e.first_name || ' ' || e.last_name as employee_name,
               e.created_at,
               e.updated_at,
               GROUP_CONCAT(lr.start_date || '|' || lr.end_date, ';') AS leave_periods
        FROM employee e
        LEFT JOIN leave_request lr 
        ON e.id = lr.employee_id 
        AND lr.start_date <= ? 
        AND lr.end_date >= ?
        GROUP BY e.id
        ORDER BY e.last_name, e.first_name
    """, last_day_of_month, first_day_of_month)

    output = io.StringIO()
    writer = csv.writer(output)

    header = ['#', 'Employee Name', 'Year', 'Month'] + [str(day) for day in range(1, last_day_of_month.day + 1)]
    writer.writerow(header)

    for index, row in enumerate(attendance_data):
        attendance_row = [
            index + 1,
            row['employee_name'],
            year,
            month
        ]

        attendance_days = ['Present'] * last_day_of_month.day

        if row['leave_periods']:
            leave_periods = row['leave_periods'].split(';')

            from datetime import datetime

            for period in leave_periods:
                if period:
                    start_str, end_str = period.split('|')
                    start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

                    leave_start = max(start_date.day, 1)
                    leave_end = min(end_date.day, last_day_of_month.day)
                    for day in range(leave_start, leave_end + 1):
                        attendance_days[day - 1] = 'On Leave'

        attendance_row.extend(attendance_days)
        writer.writerow(attendance_row)

    output.seek(0)

    # Return CSV as downloadable file
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"attendance_log_{year}-{month}.csv"
    )


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change password"""

    user_id = session["user_id"]

    if request.method == "POST":
        # Get the form data
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not current_password:
            return apology("missing current password", 400)

        if not new_password:
            return apology("missing new password", 400)

        if new_password != confirm_password:
            return apology("passwords don't match", 400)

        user_data = db.execute("SELECT hash FROM employee WHERE id = ?", user_id)
        if len(user_data) != 1:
            return apology("user not found", 404)

        # Check if the current password is correct
        if not check_password_hash(user_data[0]["hash"], current_password):
            return apology("current password incorrect", 400)

        new_password_hash = generate_password_hash(new_password)

        # Update the password in the database
        db.execute("UPDATE employee SET hash = ? WHERE id = ?", new_password_hash, user_id)

        # Flash a success message
        flash("Password updated successfully")

        # Redirect to the home page
        return redirect("/sign_out")

    # If method is GET, render the change_password form
    return render_template("others/change_password.html", title="Change Password")


@app.route("/profile")
@login_required
def profile():
    """Profile"""
    
    user_data = {
        "name": session.get('user_name', 'N/A'),
        "role": session.get('user_role', 'N/A'),
        "email": session.get('user_email', 'N/A'),
        "employee_id": session.get('employee_id', 'N/A'),
        "team": session.get('team', 'N/A'),
        "department": session.get('department', 'N/A'),
        "position": session.get('position', 'N/A'),
    }

    # Fetch leave days for the user
    leave_days_query = """
        SELECT COALESCE(SUM(JULIANDAY(MIN(?, end_date)) - JULIANDAY(MAX(?, start_date)) + 1), 0) as leave_days
        FROM leave_request
        WHERE employee_id = ? AND status = 'Approved'
    """
    first_day_of_month = date.today().replace(day=1)
    last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    leave_days = db.execute(leave_days_query, last_day_of_month, first_day_of_month, user_data['employee_id'])[0]['leave_days']
    
    # Fetch payroll information for the user
    payroll_query = """
        WITH vacation_days AS (
            SELECT employee_id, 
                   COALESCE(SUM(JULIANDAY(MIN(?, end_date)) - JULIANDAY(MAX(?, start_date)) + 1), 0) as vacation_days
            FROM leave_request
            WHERE employee_id = ? AND status = 'Approved'
        )
        SELECT p.salary * (1 - COALESCE(v.vacation_days, 0) * 0.001) as payroll
        FROM employee e
        JOIN position p ON e.position_id = p.id
        LEFT JOIN vacation_days v ON e.id = v.employee_id
        WHERE e.id = ?
    """
    
    
    payroll = db.execute(payroll_query, last_day_of_month, first_day_of_month, user_data['employee_id'], user_data['employee_id'])[0]['payroll']

    user_data["leave_days"] = leave_days
    user_data["payroll"] = payroll

    return render_template("others/profile.html", title="Profile", user_data=user_data)


@app.route("/my_leave_requests")
@login_required
def my_leave_requests():
    """My Leave Requests"""
    employee_id = session.get('employee_id')
    
    leave_requests = db.execute("""
        SELECT id, leave_type, start_date, end_date, status
        FROM leave_request
        WHERE employee_id = ?
        ORDER BY created_at DESC
    """, employee_id)

    return render_template("others/my_leave_requests.html", 
                           title="My Leave Requests", 
                           leave_requests=leave_requests)


@app.route("/my_attendance")
@login_required
def my_attendance():
    """My Attendance"""

    from datetime import datetime, timedelta, date
    employee_id = session.get('employee_id')    

    # Get the current date and the date 30 days ago
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    leave_requests = db.execute("""
        SELECT start_date, end_date, leave_type, status
        FROM leave_request
        WHERE employee_id = ? 
        AND (
            (start_date BETWEEN ? AND ?) 
            OR (end_date BETWEEN ? AND ?) 
            OR (start_date <= ? AND end_date >= ?)
        )
        ORDER BY start_date DESC
    """, employee_id, thirty_days_ago, today, thirty_days_ago, today, thirty_days_ago, today)

    # Convert string dates to datetime.date objects
    for leave in leave_requests:
        leave['start_date'] = datetime.strptime(leave['start_date'], '%Y-%m-%d').date()
        leave['end_date'] = datetime.strptime(leave['end_date'], '%Y-%m-%d').date()

    # Generate attendance records excluding Saturdays and Sundays
    attendance_records = []
    current_date = thirty_days_ago
    while current_date <= today:
        if current_date.weekday() not in (5, 6):
            status = "Present"
            for leave in leave_requests:
                if leave['start_date'] <= current_date <= leave['end_date']:
                    if leave['status'] == 'Approved':
                        status = f"On {leave['leave_type']} Leave"
                    elif leave['status'] == 'Pending':
                        status = f"Pending {leave['leave_type']} Leave"
                    break
            attendance_records.append({
                "date": current_date,
                "status": status
            })
        current_date += timedelta(days=1)

    return render_template("others/my_attendance.html", 
                           title="My Attendance", 
                           attendance_records=attendance_records)


@app.route("/generate_my_attendance_log")
@login_required
def generate_my_attendance_log():
    """Generate attendance log CSV for the current month for the logged-in employee"""

    from datetime import date, timedelta, datetime
    import io, csv
    from flask import send_file, flash, redirect, url_for
    
    employee_id = session.get('employee_id')
    today = date.today()
    year = today.year
    month = today.month

    # Get the first and last day of the current month
    first_day_of_month = today.replace(day=1)
    last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    employee_data = db.execute("""
        SELECT e.id as employee_id,
               e.first_name || ' ' || e.last_name as employee_name,
               GROUP_CONCAT(lr.start_date || '|' || lr.end_date || '|' || lr.status, ';') AS leave_periods
        FROM employee e
        LEFT JOIN leave_request lr 
        ON e.id = lr.employee_id 
        AND lr.start_date <= ? 
        AND lr.end_date >= ?
        WHERE e.id = ?
        GROUP BY e.id
    """, last_day_of_month, first_day_of_month, employee_id)

    if not employee_data:
        flash("Employee data not found.", "danger")
        return redirect(url_for('profile'))

    employee = employee_data[0]

    # Create CSV output
    output = io.StringIO()
    writer = csv.writer(output)

    header = ['Employee Name', 'Year', 'Month']
    days_of_month = [(first_day_of_month + timedelta(days=i)) for i in range((last_day_of_month - first_day_of_month).days + 1)]
    weekdays = [day for day in days_of_month if day.weekday() not in (5, 6)]

    header += [str(day.day) for day in weekdays]
    writer.writerow(header)

    attendance_row = [
        employee['employee_name'],
        year,
        month
    ]
    attendance_days = ['Present'] * len(weekdays)

    # Handle leave periods
    if employee['leave_periods']:
        leave_periods = employee['leave_periods'].split(';')
        for period in leave_periods:
            if period:
                start_str, end_str, status = period.split('|')
                start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_str, '%Y-%m-%d').date()

                for idx, day in enumerate(weekdays):
                    if start_date <= day <= end_date:
                        if status == 'Approved':
                            attendance_days[idx] = 'On Leave'
                        elif status == 'Pending':
                            attendance_days[idx] = 'Pending Leave'

    attendance_row.extend(attendance_days)
    writer.writerow(attendance_row)

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"attendance_log_{employee['employee_name']}_{year}-{month}.csv"
    )


@app.route("/my_payroll")
@login_required
def my_payroll():
    return apology("coming soon")


@app.route("/settings")
@login_required
def settings():
    return apology("coming soon")


@app.route("/sign_out")
def sign_out():
    """Log user out"""

    session.clear()

    return redirect("/")