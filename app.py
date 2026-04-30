# Flask
from flask import Flask, render_template

# SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy import Integer, String, ForeignKey, select

# intialise app
app = Flask(__name__)

# initialise db
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///focustrack.db"
db = SQLAlchemy(app)


# models go here
class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    progress: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String)
    created_at: Mapped[DATETIME] = mapped_column(DATETIME)
    due_date: Mapped[DATETIME] = mapped_column(DATETIME)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Foreign Key
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    task: Mapped[Task] = relationship(back_populates="sessions")
    start_time: Mapped[DATETIME] = mapped_column(DATETIME)
    end_time: Mapped[DATETIME] = mapped_column(DATETIME)
    duration: Mapped[int] = mapped_column(Integer)


# routes go here
@app.route("/")
def home():
    # home page - shows all current tasks, completed tasks, progress, priority and ability to create new task
    tasks = db.session.execute(select(Task)).scalars()
    return render_template("home.html", tasks=tasks)


@app.post("/add_item")
def add_item():
    # get the form data from the request object
    item = request.form["item_name"]

if __name__ == "__main__":
    app.run(debug=True)