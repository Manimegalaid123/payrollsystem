from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import csv
import os
from datetime import datetime
from io import StringIO

app = Flask(__name__)
app.secret_key = "payrollsystem123"  # For flash messages

# Ensure database directory exists
os.makedirs('payroll_system', exist_ok=True)

def init_db():
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    
    # Employee table with additional fields
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                position TEXT NOT NULL,
                department TEXT,
                salary REAL NOT NULL,
                tax_rate REAL DEFAULT 0.15,
                allowances REAL DEFAULT 0
            )''')
    
    # Departments table
    c.execute('''CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )''')
    
    # Add some default departments if none exist
    c.execute("SELECT COUNT(*) FROM departments")
    if c.fetchone()[0] == 0:
        departments = ['Engineering', 'Marketing', 'HR', 'Sales', 'Finance']
        for dept in departments:
            c.execute("INSERT INTO departments (name) VALUES (?)", (dept,))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    
    # Get quick stats
    c.execute("SELECT COUNT(*) FROM employees")
    emp_count = c.fetchone()[0]
    
    c.execute("SELECT SUM(salary) FROM employees")
    total_salary = c.fetchone()[0] or 0
    
    c.execute("SELECT AVG(salary) FROM employees")
    avg_salary = c.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('index.html', 
                          emp_count=emp_count,
                          total_salary=round(total_salary, 2),
                          avg_salary=round(avg_salary, 2))

@app.route('/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        department = request.form['department']
        salary = float(request.form['salary'])
        tax_rate = float(request.form['tax_rate'])
        allowances = float(request.form['allowances'])
        
        conn = sqlite3.connect('payroll_system/database.db')
        c = conn.cursor()
        c.execute("INSERT INTO employees (name, position, department, salary, tax_rate, allowances) VALUES (?, ?, ?, ?, ?, ?)", 
                 (name, position, department, salary, tax_rate, allowances))
        conn.commit()
        conn.close()
        
        flash('Employee added successfully!', 'success')
        return redirect('/view')
    
    # Get departments for dropdown
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    c.execute("SELECT name FROM departments")
    departments = [dept[0] for dept in c.fetchall()]
    conn.close()
    
    return render_template('add_employee.html', departments=departments)

@app.route('/view')
def view_employees():
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM employees")
    employees = c.fetchall()
    conn.close()
    return render_template('view_employees.html', employees=employees)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        department = request.form['department']
        salary = float(request.form['salary'])
        tax_rate = float(request.form['tax_rate']) / 100  # Convert percentage to decimal
        allowances = float(request.form['allowances'])
        
        # Get the department name from the department ID
        if department:
            c.execute("SELECT name FROM departments WHERE id=?", (department,))
            dept_result = c.fetchone()
            if dept_result:
                department = dept_result[0]
        
        c.execute("UPDATE employees SET name=?, position=?, department=?, salary=?, tax_rate=?, allowances=? WHERE id=?", 
                 (name, position, department, salary, tax_rate, allowances, id))
        conn.commit()
        
        flash('Employee updated successfully!', 'success')
        return redirect('/view')
    
    # Get employee data
    c.execute("SELECT * FROM employees WHERE id=?", (id,))
    employee = c.fetchone()
    
    # Get departments for dropdown
    c.execute("SELECT id, name FROM departments")
    departments = c.fetchall()
    
    # Find the department ID for the current employee's department
    selected_dept_id = None
    if employee[3]:  # If employee has a department
        c.execute("SELECT id FROM departments WHERE name=?", (employee[3],))
        dept_result = c.fetchone()
        if dept_result:
            selected_dept_id = dept_result[0]
    
    conn.close()
    
    return render_template('edit_employee.html', 
                          employee=employee, 
                          departments=departments,
                          selected_dept_id=selected_dept_id)


@app.route('/delete/<int:id>')
def delete_employee(id):
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    c.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()
    
    flash('Employee deleted successfully!', 'warning')
    return redirect('/view')

@app.route('/payroll')
def calculate_payroll():
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    c.execute("SELECT id, name, department, salary, tax_rate, allowances FROM employees")
    employees = c.fetchall()
    conn.close()
    
    payroll_data = []
    total_gross = 0
    total_tax = 0
    total_net = 0
    
    for emp in employees:
        emp_id, name, department, salary, tax_rate, allowances = emp
        gross_pay = salary
        tax_amount = gross_pay * tax_rate
        net_pay = gross_pay - tax_amount + allowances
        
        payroll_data.append({
            'id': emp_id,
            'name': name,
            'department': department,
            'gross_pay': gross_pay,
            'tax_amount': tax_amount,
            'allowances': allowances,
            'net_pay': net_pay
        })
        
        total_gross += gross_pay
        total_tax += tax_amount
        total_net += net_pay
    
    summary = {
        'total_gross': total_gross,
        'total_tax': total_tax,
        'total_net': total_net
    }
    
    return render_template('calculate_payroll.html', 
                          payroll=payroll_data, 
                          summary=summary)

@app.route('/departments', methods=['GET', 'POST'])
def manage_departments():
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        department_name = request.form['department_name']
        c.execute("INSERT INTO departments (name) VALUES (?)", (department_name,))
        conn.commit()
        flash('Department added successfully!', 'success')
    
    c.execute("SELECT * FROM departments")
    departments = c.fetchall()
    
    # Get count of employees by department
    dept_counts = {}
    for dept in departments:
        c.execute("SELECT COUNT(*) FROM employees WHERE department=?", (dept[1],))
        dept_counts[dept[0]] = c.fetchone()[0]
    
    conn.close()
    
    return render_template('departments.html', 
                          departments=departments, 
                          dept_counts=dept_counts)

@app.route('/delete_department/<int:id>')
def delete_department(id):
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    
    # Get department name
    c.execute("SELECT name FROM departments WHERE id=?", (id,))
    dept_name = c.fetchone()[0]
    
    # Check if department is in use
    c.execute("SELECT COUNT(*) FROM employees WHERE department=?", (dept_name,))
    if c.fetchone()[0] > 0:
        flash('Cannot delete department that has employees!', 'danger')
    else:
        c.execute("DELETE FROM departments WHERE id=?", (id,))
        conn.commit()
        flash('Department deleted successfully!', 'warning')
    
    conn.close()
    return redirect('/departments')

@app.route('/export_payroll')
def export_payroll():
    try:
        # Ensure static directory exists
        os.makedirs('static', exist_ok=True)
        
        conn = sqlite3.connect('payroll_system/database.db')
        c = conn.cursor()
        c.execute("SELECT id, name, department, salary, tax_rate, allowances FROM employees")
        employees = c.fetchall()
        conn.close()
        
        # Full path to the export file - use absolute path to avoid any directory issues
        export_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'payroll_export.csv')
        
        # Open the file directly and write to it
        with open(export_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['ID', 'Name', 'Department', 'Gross Pay', 'Tax Amount', 'Allowances', 'Net Pay'])
            
            # Write data rows
            for emp in employees:
                emp_id, name, department, salary, tax_rate, allowances = emp
                gross_pay = salary
                tax_amount = gross_pay * tax_rate
                net_pay = gross_pay - tax_amount + allowances
                
                writer.writerow([
                    emp_id, name, department, 
                    f"{gross_pay:.2f}", f"{tax_amount:.2f}", 
                    f"{allowances:.2f}", f"{net_pay:.2f}"
                ])
        
        # Verify file exists and has content
        if os.path.exists(export_path) and os.path.getsize(export_path) > 0:
            flash('Payroll data exported successfully! <a href="/static/payroll_export.csv" download>Download CSV</a>', 'success')
        else:
            flash('Error creating export file. Please try again.', 'danger')
            
        return redirect('/payroll')
        
    except Exception as e:
        flash(f'Export error: {str(e)}', 'danger')
        return redirect('/payroll')
    

@app.route('/department_report')
def department_report():
    conn = sqlite3.connect('payroll_system/database.db')
    c = conn.cursor()
    
    # Get all departments
    c.execute("SELECT name FROM departments")
    departments = [dept[0] for dept in c.fetchall()]
    
    dept_data = {}
    for dept in departments:
        # Get employee count
        c.execute("SELECT COUNT(*) FROM employees WHERE department=?", (dept,))
        emp_count = c.fetchone()[0]
        
        # Get salary stats
        c.execute("SELECT SUM(salary), AVG(salary), MIN(salary), MAX(salary) FROM employees WHERE department=?", (dept,))
        salary_data = c.fetchone()
        
        if emp_count > 0:
            dept_data[dept] = {
                'count': emp_count,
                'total_salary': salary_data[0],
                'avg_salary': round(salary_data[1], 2),
                'min_salary': salary_data[2],
                'max_salary': salary_data[3]
            }
    
    conn.close()
    
    return render_template('department_report.html', dept_data=dept_data)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)