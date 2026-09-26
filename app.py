"""Flask application for Focustrack."""

from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DATETIME, ForeignKey, select


# intialise app
app = Flask(__name__)
app.secret_key = (
    "28d2a6e444a7ad429dd240f8423417dfdffe3e0e86795832b1b42f1f27494de3"
)

# initialise db
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///focustrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Joining table for the many-to-many relationship between tasks and tags
task_tags = db.Table(
    "task_tags",
    db.Column(
        "task_id",
        db.Integer,
        db.ForeignKey("tasks.id"),
        primary_key=True,
    ),
    db.Column(
        "tag_id",
        db.Integer,
        db.ForeignKey("tags.id"),
        primary_key=True,
    ),
)


class Task(db.Model):
    """Task model with priority, due date, tags, etc."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    priority_id: Mapped[int] = mapped_column(ForeignKey("priorities.id"))
    priority: Mapped["Priority"] = relationship(back_populates="tasks")

    created_at: Mapped[DATETIME] = mapped_column(
        DATETIME,
        default=lambda: datetime.now(timezone.utc)
    )

    due_date: Mapped[DATETIME] = mapped_column(DATETIME, nullable=True)
    sessions: Mapped[list["Session"]] = relationship(back_populates="task")

    # Foreign Key
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    user: Mapped["User | None"] = relationship(back_populates="tasks")

    # Many to Many
    tags: Mapped[list["Tag"]] = relationship(
        secondary=task_tags,
        back_populates="tasks",
    )


class Priority(db.Model):
    """Task priority model, contains Low (1), Medium (2), and High (3)"""

    __tablename__ = "priorities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)

    tasks: Mapped[list["Task"]] = relationship(back_populates="priority")


class Tag(db.Model):
    """Model for tags that can assign to one or more tasks."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Many to Many
    tasks: Mapped[list["Task"]] = relationship(
        secondary=task_tags,
        back_populates="tags",
    )


class Session(db.Model):
    """Model for tracking the time of work session."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign Key
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    task: Mapped[Task] = relationship(back_populates="sessions")
    start_time: Mapped[DATETIME] = mapped_column(DATETIME)
    end_time: Mapped[DATETIME] = mapped_column(DATETIME)
    duration: Mapped[int] = mapped_column(Integer)


class User(db.Model):
    """Model for containing user information."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    tasks: Mapped[list["Task"]] = relationship(back_populates="user")

    def set_password(self, password):
        """Hash the password before saving it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the entered password is the same as the hashed password."""
        return check_password_hash(self.password_hash, password)


# ----------------------------- Routes start here -----------------------------

@app.route("/")
def home():
    """Default page the user sees when not in session."""
    # home page - has ability to login or signup and also contains guest mode
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("home.html")


@app.route("/add_task", methods=["POST"])
def add_task():
    """Creates a new task for logged in user"""
    if "user_id" not in session:
        return redirect(url_for("home"))

    title = request.form.get("title")

    if not title or not title.split():
        tasks = (
            db.session.execute(
                select(Task).where(Task.user_id == session["user_id"])
            )
            .scalars()
            .all()
        )
        return render_template(
            "dashboard.html",
            username=session["username"],
            tasks=tasks,
            error="A title is required.",
        )

    due_date_value = request.form.get("due_date")
    selected_tags = request.form.getlist("tags")

    task = Task(
        # get the form data from the request object
        title=request.form["title"],
        description=request.form["description"],
        priority_id=request.form["priority_id"],
        due_date=(
            datetime.fromisoformat(due_date_value)
            if due_date_value
            else None
        ),
        user_id=session.get("user_id"),
    )

    db.session.add(task)

    for tag_id in selected_tags:
        tag = db.session.get(Tag, int(tag_id))
        if tag:
            task.tags.append(tag)

    db.session.commit()

    return redirect("/")


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    """Deletes a task by its id"""
    print(f"Deleting task {task_id}")

    task = db.session.get(Task, task_id)

    if task is None:
        return "Task not found", 404

    db.session.delete(task)
    db.session.commit()

    return redirect("/")


@app.route("/task/<int:task_id>")
def view_task(task_id):
    """Displays details of a task"""
    task = db.session.get(Task, task_id)
    if task is None:
        return "Task not found", 404
    return render_template("task.html", task=task)


# --------------- Authentication System ------------------

# Signup route
@app.route("/signup", methods=["POST"])
def signup():
    """Creates a new account."""
    username = request.form["username"]
    password = request.form["password"]

    if len(password) < 8:
        return render_template(
            "home.html",
            error="Your password must be at least 8 characters long.",
        )

    if not username.strip() or not password.strip():
        # ^ Checks for blank spaces or empty inputs
        return render_template(
            "home.html",
            error="You cannot leave your username or password blank.",
        )

    # check if user is already in the database
    user = User.query.filter_by(username=username).first()
    if user:  # if user is true, render home page and give error message
        return render_template(
            "home.html",
            error="There is already someone with this username.",
        )

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
    """Authenticate a user and starts a session if valid."""
    # Collect info from the form
    username = request.form["username"]
    password = request.form["password"]

    if not username or not password.strip():
        # ^ Checks for blank spaces or empty inputs
        return render_template(
            "home.html",
            error="You cannot leave your username or password blank.",
        )

    # Check if info is in the database to log the user in
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session["username"] = username
        session["user_id"] = user.id
        return redirect(url_for("dashboard"))

    # Otherwise show homepage because denied
    else:
        return render_template(
            "home.html",
            error="Incorrect username or password.",
        )


# Dashboard route
@app.route("/dashboard")
def dashboard():
    """Shows dashboard for users that are logged in"""
    # dashboard page - has all tasks, info, ability to create or delete tasks
    if "user_id" not in session:  # if not logged in, return to home page
        return redirect(url_for("home"))
    tasks = (
        db.session.execute(
            select(Task).where(Task.user_id == session["user_id"])
        )
        .scalars()
        .all()
    )
    return render_template(
        "dashboard.html",
        username=session["username"],
        tasks=tasks,
    )


# Logout route
@app.route("/logout")
def logout():
    """Clear the user session and redirects them to the home page."""
    session.clear()
    return redirect(url_for("home"))
    # Redirects the user back to the home page when logged out


# Guest route, so the website does not require the user to log in to use it.
# However, the user cannot access your tasks from another device.
@app.route("/guest")
def guest():
    """Temporary guest view for users who don't want to make an account."""
    return render_template("dashboard.html", username="Guest", tasks=[])


if __name__ == "__main__":
    app.run(debug=True)
