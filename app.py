# Flask
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
# SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DATETIME, ForeignKey, select
from datetime import datetime, timezone


# intialise app
app = Flask(__name__)
app.secret_key = "28d2a6e444a7ad429dd240f8423417dfdffe3e0e86795832b1b42f1f27494de3"

# initialise db
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///focustrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Task(db.Model):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String)
    created_at: Mapped[DATETIME] = mapped_column(DATETIME, default=lambda: datetime.now(timezone.utc))
    due_date: Mapped[DATETIME] = mapped_column(DATETIME, nullable=True)
    sessions: Mapped[list["Session"]] = relationship(back_populates="task")
    # Foreign Key
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User | None"] = relationship(back_populates="tasks")


class Session(db.Model):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Foreign Key
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    task: Mapped[Task] = relationship(back_populates="sessions")
    start_time: Mapped[DATETIME] = mapped_column(DATETIME)
    end_time: Mapped[DATETIME] = mapped_column(DATETIME)
    duration: Mapped[int] = mapped_column(Integer)


class User(db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")

    def set_password(self, password):
        # hash the password
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # check if entered password is the same as the hashed password
        return check_password_hash(self.password_hash, password)


# routes start here

@app.route("/")
def home():
    # home page - has all current tasks, completed tasks, progress, priority and ability to create new task
    if "username" in session:
        return redirect(url_for("dashboard"))
    tasks = db.session.execute(select(Task)).scalars()
    return render_template("home.html", tasks=tasks)


@app.route("/add_task", methods=["POST"])
def add_task():
    title = request.form.get("title")

    if not title or not title.split():
        return render_template("404.html", error="Title is required.")
    task = Task(
        # get the form data from the request object
        title=request.form["title"],
        description=request.form["description"],
        priority=request.form["priority"],
        user_id=session.get("user_id")
    )

    db.session.add(task)
    db.session.commit()

    return redirect("/")


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    print(f"Deleting task {id}")

    task = db.session.get(Task, id)

    if task is None:
        return "Task not found", 404

    db.session.delete(task)
    db.session.commit()

    return redirect("/")


@app.route("/task/<int:id>")
def task(id):
    task = db.session.get(Task, id)
    if task is None:
        return "Task not found", 404
    return render_template("task.html", task=task)


# Start of login system

# Signup route
@app.route("/signup", methods=["POST"])
def signup():
    username = request.form["username"]
    password = request.form["password"]
    # check if user is already in the database
    user = User.query.filter_by(username=username).first()
    if user:  # if user is true, render home page and give error message
        return render_template("home.html", error="There is already someone with this username.")
    else:  # if the user doesn't already exist:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)  # adds new user to the database
        db.session.commit()  # commits new user to the database
        session["username"] = username
        session["user_id"] = new_user.id
        return redirect(url_for("dashboard"))


# Login route
@app.route("/login", methods=["POST"])
def login():
    # Collect info from the form
    username = request.form["username"]
    password = request.form["password"]

    # Check if info is in the database to log the user in
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session["username"] = username
        session["user_id"] = user.id
        return redirect(url_for("dashboard"))

    # Otherwise show homepage because denied
    else:
        return render_template("home.html")


# Dashboard route
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        tasks = db.session.execute(select(Task)).scalars().all()
        return render_template("dashboard.html", username=session["username"], tasks=tasks)
    return redirect(url_for("home"))  # if not logged in, return to home page


# Logout route
@app.route("/logout")
def logout():
    session.pop("username", None)  # removes the user from the session
    return redirect(url_for("home"))  # redirects the user back to the home page when logged out


# Guest route, so the website does not require the user to log in to use it. However, the user cannot access your tasks from another device.
@app.route("/guest")
def guest():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)
