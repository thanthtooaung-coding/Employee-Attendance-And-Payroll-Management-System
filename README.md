# Employee Attendance and Payroll Management System

## Overview

This web-based Employee Attendance and Payroll Management System is designed to help organizations efficiently manage their workforce's attendance, payroll, and division structure. The system provides a dashboard view of key statistics and a user-friendly interface for handling employee records, attendance tracking, and payroll processing.

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Setup Instructions](#setup-instructions)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [License](#license)
- [Contributing](#contributing)
- [Contact](#contact)

## Features

### Dashboard Overview

- Displays total counts of divisions, departments, teams, and employees.
- Monthly comparison of employee data.
- Next payroll date estimation with a clear format, e.g., November 30, 2024.

### Division CRUD Operations

- Manage divisions through create, read, update, and delete functionalities.
- Includes an intuitive division table with a search box and an 'Add New' button.

### Department CRUD Operations

- Create, view, edit, and delete departments within divisions.
- Associate departments with specific divisions for better organization.

### Team CRUD Operations

- Manage teams within departments.
- Create, update, view, and delete team information.

### Position CRUD Operations

- Define and manage various positions within the organization.
- Set salary ranges for each position.

### Role CRUD Operations

- Create and manage user roles with specific permissions.
- Assign roles to employees for access control.

### Employee Management

- Add, update, and delete employee records.
- Assign employees to departments, teams, and positions.
- Track attendance and payroll information.

### Attendance Tracking

- Record attendance with timestamps.
- Generate reports based on attendance data.
- View attendance history for individual employees or teams.

### Payroll Processing

- Automatic calculation of monthly payroll based on employee positions and attendance.
- Generate payroll reports for the current and upcoming months.
- Handle salary deductions and bonuses.

### Password Generation & Security

- Uses `generate_password_hash` from `werkzeug.security` to securely hash user passwords after sending a readable version to users.

## Technology Stack

- Backend: Flask (Python)
- Frontend: HTML5, CSS3, JavaScript (with optional libraries for enhanced UI)
- Database: SQLite (with plans for integration with other databases)
- Security: Werkzeug for password hashing
- Version Control: Git, GitHub

## Technology Stack

- Backend: Flask (Python)
- Frontend: HTML5, CSS3, JavaScript (with optional libraries for enhanced UI)
- Database: SQLite (with plans for integration with other databases)
- Security: Werkzeug for password hashing
- Version Control: Git, GitHub

## Setup Instructions

To set up this project locally:

1. Clone the repository:

   ```bash
   git clone https://github.com/thanthtooaung-coding/Employee-Attendance-And-Payroll-Management-System.git
   cd Employee-Attendance-And-Payroll-Management-System
   ```

2. Create a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # For Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:

   ```bash
   flask run
   ```

5. Access the application:

   Navigate to http://127.0.0.1:5000/ in your browser.

## Project Structure

```
Employee-Attendance-And-Payroll-Management-System/
│
├── app/                    # Application code
│   ├── templates/          # HTML templates
│   ├── static/             # CSS, JavaScript files
├── app.py                  # Main file
├── config.py               # Configuration file
├── helpers.py              # Helper file
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── ...
```

## Usage

### Managing Organizational Structure

#### Divisions

- Use the "Division" tab to add, view, edit, or delete divisions within the organization.
- Utilize the search box to filter divisions quickly.

#### Departments

- Navigate to the "Departments" section to manage departments within divisions.
- Create new departments, assign them to divisions.

#### Teams

- Access the "Teams" area to create and manage teams within departments.
- Assign employees to teams.

#### Positions

- Use the "Positions" module to define various job positions in the organization.
- Set salary ranges for each position.

#### Roles

- Manage user roles and permissions in the "Roles" section.
- Create custom roles with specific access rights to different parts of the system.

### Employee Management

- Add new employees and assign them to appropriate departments, teams, and positions.
- Update employee information, including contact details, salary, and role.
- View employee profiles with their attendance and payroll history.

### Payroll and Attendance

- Track employee attendance daily using the check-in/check-out system.
- View attendance reports for individuals, teams, or departments.
- Generate payroll reports based on attendance, position, and any additional factors (overtime, bonuses, etc.).
- Estimate the payroll for the upcoming month with automatic date formatting.

### Security and User Management

- User passwords are automatically generated and sent to users in a readable format, then hashed and stored securely in the database.
- Assign roles to users to control their access to different parts of the system.

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! If you would like to contribute to the project, please follow these steps:

1. Fork the repository.
2. Create a new feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## Contact

For any inquiries or support, feel free to reach out:

- Email: thanthtooaung.coding@gmail.com
- GitHub: https://github.com/thanthtooaung-coding

##

Thank you for your interest in the Employee Attendance and Payroll Management System. We're committed to continually improving and expanding its capabilities to meet evolving organizational needs.
