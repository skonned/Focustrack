from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import Integer, String, Column

DATABASE = "focustrack.db"

# intialise app
app = Flask(__name__)
app.config["SQLALCHEMY_ENGINES"] = {"default" : "sqlite:///focustrack.db"}

db = SQLAlchemy()
db.init.app(app)

class Base(DeclarativeBase):
    pass

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)


@app.route("/")
def home():
    # home page - shows all current tasks, completed tasks, progress, priority and ability to create new task

if __name__ == "__main__":
    app.run(debug=True)