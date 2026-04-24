from flask import Flask, render_template
import sqlite3

DATABASE = "focustrack.db"

# intialise app
app = Flask(__name__)


@app.route("/")
def home():
    # home page - shows all current tasks, completed tasks, progress, priority and ability to create new task


if __name__ == "__main__":
    app.run(debug=True)