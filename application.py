import os
from flask import Flask, session, render_template, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("index.html", message="your search results will appear here")

@app.route("/sign_in")
def sign_in():
    return render_template("sign_in.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/search",methods=["GET"])
def search():
    if not request.args.get("book"):
        return render_template("index.html",message="err: empty search query")

    #capitalizing query and adding wild character
    query = "%" + request.args.get("book") + "%"
    query = query.title()

    results = db.execute("SELECT isbn, title, author, year FROM books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query LIMIT 20",{"query":query})

    if results.rowcount == 0:
        return render_template("index.html",message="err: no books found")

    books = results.fetchall()

    return render_template("index.html",books=books)
