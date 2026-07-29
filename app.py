# Flask
from flask import Flask, render_template, request, redirect, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
def load_user(user_id):
    return User.get(user_id)
from werkzeug.security import generate_password_hash, check_password_hash

# SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, DATETIME, ForeignKey, select

# intialise app
app = Flask(__name__)

# initialise db
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///focustrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "test"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader

class Task(db.Model):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    progress: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String)
    created_at: Mapped[DATETIME] = mapped_column(DATETIME)
    due_date: Mapped[DATETIME] = mapped_column(DATETIME)
    sessions: Mapped[list["Session"]] = relationship(back_populates="task")


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
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String)
    password: Mapped[str] = mapped_column(String)


# routes go here
@app.route("/")
def home():
    # home page - has all current tasks, completed tasks, progress, priority and ability to create new task
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


# login stuff
@app.route("/signup", methods=["GET", "POST"])
def signup():
    user = User(
        username=request.form["username"],
        password=request.form["password"],
    )

    db.session.add(user)
    db.session.commit()
    pass


@app.route("/login", methods=["GET", "POST"])
def login():
    pass


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", name=current_user.username)


if __name__ == "__main__":
    app.run(debug=True)
