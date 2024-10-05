import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

app.config['PROJECT_NAME'] = "VinnTrack"

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


if __name__ == "__main__":
    app.run(debug=True)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    return render_template("index.html", title="Dashboard", project_name=app.config['PROJECT_NAME'])


@app.route("/division")
def division():
    return render_template("division.html", title="Division", project_name=app.config['PROJECT_NAME'])


@app.route("/department")
def department():
    return render_template("department.html", title="Department", project_name=app.config['PROJECT_NAME'])


@app.route("/team")
def team():
    return render_template("team.html", title="Team", project_name=app.config['PROJECT_NAME'])


@app.route("/employee")
def employee():
    return render_template("employee.html", title="Employee", project_name=app.config['PROJECT_NAME'])


@app.route("/role")
def role():
    return render_template("role.html", title="Role", project_name=app.config['PROJECT_NAME'])


@app.route("/leave")
def leave():
    return render_template("leave.html", title="Leave", project_name=app.config['PROJECT_NAME'])


@app.route("/profile")
def profile():
    return render_template("profile.html", title="Profile", project_name=app.config['PROJECT_NAME'])


@app.route("/settings")
def settings():
    # return render_template("settings.html", title="Settings", project_name=app.config['PROJECT_NAME'])
    return apology("TODO", 403, title="Settings", project_name=app.config['PROJECT_NAME'])

@app.route("/sign_out")
def sign_out():
    return apology("TODO", 403, title="Sign Out", project_name=app.config['PROJECT_NAME'])