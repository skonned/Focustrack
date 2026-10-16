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


def get_guest_tasks():
    """Returns tasks linked to the current guest session."""
    task_ids = session.get("guest_task_ids", [])
    if not task_ids:
        return []

    return (
        db.session.execute(
            select(Task).where(Task.id.in_(task_ids))
        )
        .scalars()
        .all()
    )

# ----------------------------- Routes start here -----------------------------


@app.route("/")
def home():
    """Default page the user sees when not in session."""
    # home page - has ability to login or signup and also contains guest mode

    # Redirects user to dashboard if logged in
    if "username" in session:
        return redirect(url_for("dashboard"))

    # Displays home page
    return render_template("home.html")


@app.route("/add_task", methods=["POST"])
def add_task():
    """Creates a new task for logged in user"""

    is_guest = "user_id" not in session and session.get("guest_mode")

    # Ensures only users that are logged or in guest mode in can create tasks
    if "user_id" not in session and not is_guest:
        return redirect(url_for("home"))

    # Retrieves title submitted through the form
    title = request.form.get("title")

    # Checks if title is not empty or only white space
    if not title or not title.split():
        tasks = (
            get_guest_tasks()
            if is_guest
            else db.session.execute(
                select(Task).where(Task.user_id == session["user_id"])
            ).scalars().all()
        )

        # Redisplays dashboard with title error message
        return render_template(
            "dashboard.html",
            username="Guest" if is_guest else session["username"],
            tasks=tasks,
            error="A title is required.",
        )

    # Retrieves the submitted due date and selected tag IDs
    due_date_value = request.form.get("due_date")
    selected_tags = request.form.getlist("tags")

    # Creates a new task object using the submitted form data
    task = Task(
        # get the form data from the request object
        title=request.form["title"],
        description=request.form["description"],
        priority_id=request.form["priority_id"],

        # Converts due date string into datetime object
        # Uses none if user doesn't give a due date
        due_date=(
            datetime.fromisoformat(due_date_value)
            if due_date_value
            else None
        ),

        # Links new task with the user
        user_id=session.get("user_id"),
    )

    # Adds new task to database session
    db.session.add(task)

    # Retrieves each selected tag from the database
    for tag_id in selected_tags:
        tag = db.session.get(Tag, int(tag_id))
        if tag:
            task.tags.append(tag)

    # Saves new task and tag relations to the database
    db.session.commit()

    if is_guest:
        task_ids = session.get("guest_task_ids", [])
        task_ids.append(task.id)
        session["guest_task_ids"] = task_ids
        return redirect(url_for("guest"))

    return redirect("/")


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    """Deletes a task by its id"""

    # Prints task ID for debugging purposes
    print(f"Deleting task {task_id}")

    task = db.session.get(Task, task_id)

    if task is None:
        return "Task not found", 404

    # Deletes task from database
    db.session.delete(task)
    # Saves the deletion
    db.session.commit()

    if session.get("guest_mode"):
        return redirect(url_for("guest"))

    return redirect("/")


@app.route("/task/<int:task_id>")
def view_task(task_id):
    """Displays details of a task"""

    # Retrieves task from database using its ID
    task = db.session.get(Task, task_id)

    # Returns 404 error if task does not exist
    if task is None:
        return "Task not found", 404

    # Retrives all priorities, sorted by ID for the dropdown
    priorities = db.session.execute(
        select(Priority).order_by(Priority.id)
    ).scalars().all()

    # Retrieves all tags, sorted alphabetically
    tags = db.session.execute(
        select(Tag).order_by(Tag.name)
    ).scalars().all()

    # Passes data to the template
    # Only allows editing if the user owns the task
    return render_template(
        "task.html",
        task=task,
        priorities=priorities,
        tags=tags,
        can_edit=(
            session.get("user_id") is not None
            and task.user_id == session.get("user_id")
        )
        or (
            session.get("guest_mode")
            and task.id in session.get("guest_task_ids", [])
        )
    )


@app.route("/task/<int:task_id>/update", methods=["POST"])
def update_task(task_id):
    """Updates details for a task owned by the logged-in user."""

    # Retrives task that the user wants to update
    task = db.session.get(Task, task_id)

    # Prevents update if task does not exist, user is not logged in
    # or belongs to another user
    if task is None or not (
        (
            session.get("user_id") is not None
            and task.user_id == session["user_id"]
        )
        or (
            session.get("guest_mode")
            and task.id in session.get("guest_task_ids", [])
        )
    ):
        return "Task not found", 404

    # Retrieves submitted values and removes whitespace
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    # Retrieves submitted priority, progress, due_date values
    priority_id_value = request.form.get("priority_id", "")
    progress_value = request.form.get("progress", "")
    due_date_value = request.form.get("due_date", "")
    # Retrives all selected tag IDs
    tag_id_values = request.form.getlist("tags")

    error = None
    if not title:
        # If no title entered, display error message
        error = "A title is required."

    try:
        priority_id = int(priority_id_value)
        progress = int(progress_value)

        # Convert every tag id into an integer
        # Dict.fromkeys removes duplicate IDs while keeping original order
        tag_ids = list(dict.fromkeys(int(tag_id) for tag_id in tag_id_values))

    except ValueError:
        error = error or "Choose a valid priority, progress value, and tags."
        priority_id = None
        progress = None
        tag_ids = []

    priority = db.session.get(Priority, priority_id) if priority_id else None
    selected_tags = [db.session.get(Tag, tag_id) for tag_id in tag_ids]
    if error is None and priority is None:
        error = "Choose a valid priority."

    # Makes sure progress is between 0 and 100 percent
    if error is None and not 0 <= progress <= 100:
        error = "Progress must be between 0 and 100."

    # Checks that every submitted tag ID matches an existing tag
    if error is None and any(tag is None for tag in selected_tags):
        error = "Choose valid tags."

    due_date = None  # Displays no due date if left blank
    if due_date_value:
        try:
            # Converts the submitted date string into a datetime object
            due_date = datetime.fromisoformat(due_date_value)
        except ValueError:
            # Error if invalid date
            error = error or "Enter a valid due date."

    if error:
        priorities = db.session.execute(
            # Sorts tasks by priority
            select(Priority).order_by(Priority.id)).scalars().all()
        tags = db.session.execute(
            # Sorts tasks by tags
            select(Tag).order_by(Tag.name)).scalars().all()

        # Passes the submitted values back to the template
        # So that the user doesn't have to re-enter everything
        return render_template(
            "task.html",
            task=task,
            priorities=priorities,
            tags=tags,
            can_edit=True,
            error=error,
            form_data=request.form,
        )

    # Updates task details with valid form values
    task.title = title
    task.description = description
    task.priority = priority
    task.progress = progress
    task.due_date = due_date

    # Replace the tasks current tags with selected tags
    task.tags = selected_tags

    # Save changes to the database
    db.session.commit()

    # Basically refreshes the page so the user can see the changes
    return redirect(url_for("view_task", task_id=task.id))


# --------------- Authentication System ------------------

# Signup route
@app.route("/signup", methods=["POST"])
def signup():
    """Creates a new account."""
    username = request.form["username"]
    password = request.form["password"]

    if not username or not password.strip():
        # ^ Checks for blank spaces or empty inputs
        return render_template(
            "home.html",
            error="You cannot leave your username or password blank.",
        )

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
# However, the user cannot access their tasks when using another device.
@app.route("/guest")
def guest():
    """Temporary guest view for users who don't want to make an account."""
    session["guest_mode"] = True
    return render_template(
        "dashboard.html",
        username="Guest",
        tasks=get_guest_tasks(),
    )


if __name__ == "__main__":
    app.run(debug=True)
