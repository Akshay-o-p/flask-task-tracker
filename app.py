from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from extensions import db, bcrypt
from models import User, Task
from datetime import date, datetime
import re

app = Flask(__name__)

app.config['SECRET_KEY'] = "mysecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)

with app.app_context():
    db.create_all()


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/") # This the starting page 
def start():
    return render_template("home.html")


EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'  # basic email pattern

@app.route("/register", methods=["GET", "POST"])   # This function is used to register a new user
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()

        # --- VALIDATIONS ---
        if not username or not email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("register"))

        if not re.match(EMAIL_REGEX, email):
            flash("Invalid email format.", "warning")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return redirect(url_for("register"))

        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("Email already registered. Try logging in.", "danger")
            return redirect(url_for("register"))

        # Check if username already exists
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash("Username already taken. Please choose another.", "danger")
            return redirect(url_for("register"))

        # --- HASH PASSWORD ---
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # --- CREATE USER ---
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])   # This function is used to login to user home
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        # Basic validation
        if not email or not password:
            flash("Please fill in all fields.", "warning")
            return redirect(url_for("login"))

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")



@app.route("/home")  # This the function for user home where the list of added task by user are shown
@login_required
def home():

    selected_date = request.args.get("date")
    selected_status = request.args.get("status")

    today = date.today()

    # Default date = today
    if selected_date:
        filter_date = date.fromisoformat(selected_date)
    else:
        filter_date = date.today()

    # BASE QUERY = tasks of that date for the current user
    query = Task.query.filter_by(
        user_id=current_user.id,
        created_at=filter_date
    )

    # If status is selected, filter by it also
    if selected_status:
        query = query.filter_by(status=selected_status)

    tasks = query.all()

    return render_template("index.html", tasks=tasks,today=today)



@app.route("/logout")   # This function is used to logout the current user
@login_required
def logout():
    logout_user()
    flash("You have Successfully logged out.", "success")
    return redirect(url_for("start"))


@app.route("/add-task-page")  # This function is used to display the page to Add a new task
@login_required
def add_task_page():
    return render_template("add_task.html")


@app.route("/add_task", methods=["POST"]) # This function is used to add a new task
@login_required
def add_task():
    task_text = request.form.get("task_text")
    description = request.form.get("description")

    # Basic validation
    if not task_text:
        flash("Task title is required", "danger")
        return redirect(url_for("add_task_page"))

    new_task = Task(
        task_text=task_text,
        description=description,
        user_id=current_user.id,   # link task to logged-in user
        status="pending"
    )

    db.session.add(new_task)
    db.session.commit()

    flash("Task added successfully!", "success")
    return redirect(url_for("home"))


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])   # This is the function to edit the task 
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Security check: user can edit only their own task
    if task.user_id != current_user.id:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        task.task_text = request.form.get("task_text")
        task.description = request.form.get("description")

        db.session.commit()
        flash("Task updated successfully!", "success")
        return redirect(url_for("home"))

    return render_template("edit.html", task=task)


@app.route("/delete/<int:task_id>", methods=["POST"]) # This is the function used to delete a task
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Prevent deleting another user's task
    if task.user_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for("home"))

    db.session.delete(task)
    db.session.commit()

    flash("Task deleted successfully!", "success")
    return redirect(url_for("home"))


@app.route("/complete/<int:task_id>", methods=["POST"])    
@login_required
def complete_task(task_id):                 # This function is used to mark a task as completed
    task = Task.query.get_or_404(task_id)

    # Ensure user only updates own tasks
    if task.user_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for("home"))

    # Toggle status
    if task.status == "pending":
        task.status = "completed"
    else:
        task.status = "pending"

    db.session.commit()

    flash("Task status updated!", "success")
    return redirect(url_for("home"))


@app.route("/reschedule/<int:task_id>", methods=["GET", "POST"])
@login_required
def reschedule(task_id):                  # This function is used to reschedule a task to another day
    task = Task.query.get_or_404(task_id)

    # User owns the task?
    if task.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for("home"))

    # POST = user submitted new date
    if request.method == "POST":
        new_date_str = request.form.get("new_date")

        try:
            new_date = date.fromisoformat(new_date_str)
            task.created_at = new_date
            db.session.commit()
            flash("Task rescheduled successfully!", "success")
            return redirect(url_for("home"))
        except:
            flash("Invalid date!", "danger")
            return redirect(url_for("reschedule", task_id=task.id))

    # GET = show reschedule page
    return render_template("reschedule.html", task=task)


if __name__ == "__main__":
    app.run(debug=True)
