import os,requests,json,datetime
from flask import Flask, session, render_template, request, flash, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt as hasher


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
    return render_template("index.html", messages="your search results will appear here")

@app.route("/sign_in",methods=['GET','POST'])
def sign_in():
    session.clear()
    if request.method == "POST":
        #check for username
        if not request.form.get("username"):
            return render_template("sign_in.html",message="err: username field is empty")
        #check for password
        if not request.form.get("password"):
            return render_template("sign_in.html",message="err: password field is empty")
        #check if username in table
        #verify password
        entry = db.execute("SELECT * FROM users WHERE username = :username",
                            {"username": request.form.get('username')}).fetchone()
        if entry == None:
            return render_template("sign_in.html",message="err: user does not exist")

        if not hasher.verify(request.form.get("password"),entry[2]):
            return render_template("sign_in.html",message="err: incorrect password")

        #assign session variables
        session['userid'] = entry[0]
        session['username'] = entry[1]

        #redirect to index
        return redirect('/')

    return render_template("sign_in.html")

@app.route("/sign_out")
def sign_out():
    session.clear()
    return redirect("/")

@app.route("/register",methods=["GET","POST"])
def register():
    session.clear()
    if request.method == "POST":
        #check for username
        if not request.form.get("username"):
            return render_template("register.html",message="err: please enter a username")

        user_exists = db.execute("SELECT * FROM users WHERE username = :username",{"username":request.form.get("username")}).fetchall()

        #check if user already exists
        if user_exists:
            return render_template("register.html",message="err: username already exists; please enter another username")

        #check if password and confirmation submitted
        if not request.form.get("password") or not request.form.get("confirmation"):
            return render_template("register.html",message="err: please make sure password and confirmation fields are not empty")

        #check if password == confirmation
        if request.form.get("password") != request.form.get("confirmation"):
            return render_template("register.html",message="err: password and confirmation mismatch")

        #insert entry and commit
        db.execute("INSERT INTO users (username,password) VALUES (:username, :password)",{"username":request.form.get("username"),"password":hasher.hash(request.form.get("password"))})
        db.commit()


        return render_template("sign_in.html",message="user successfully created")
    #for get
    return render_template("register.html",message="")

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

@app.route("/book/<isbn>",methods=["GET","POST"])
def book(isbn):
    if request.method == "GET":

        """preparing book data"""
        #get book data from books table
        info = db.execute("SELECT * FROM books WHERE isbn=:isbn",{"isbn":isbn}).fetchall()

        #initialize key
        key = os.getenv("GOODREADS_KEY")

        #read api


        query = requests.get("https://www.goodreads.com/book/review_counts.json",
                params={"key": key, "isbns": isbn})
        response = query.json()
        response = response['books'][0]
        """
        Sample Response:
        {'id': 55030, 'isbn': '0375508325',
         'isbn13': '9780375508325', 'ratings_count': 101357,
         'reviews_count': 242685, 'text_reviews_count': 2136,
          'work_ratings_count': 108939, 'work_reviews_count': 264246,
          'work_text_reviews_count': 2931, 'average_rating': '4.37'}
        """

        #append api info to book info
        info.append(response)

        """preparing book review data"""
        reviews = db.execute("SELECT content,rating,username,date FROM reviews JOIN users ON reviews.userid = users.id WHERE isbn = :isbn",{"isbn":isbn}).fetchall()
        if reviews == []:
            message = "No reviews posted for this book yet."
        else:
            message = ""
        return render_template("book.html",bookinfo=info,message=message,reviews=reviews)

    #for POST
    else:
        #check if user has already posted review
        print("post called")
        review_posted = db.execute("SELECT * FROM reviews WHERE userid = :userid AND isbn = :isbn",
        {"userid":session["userid"],"isbn":isbn}).fetchall()
        if review_posted != []:
            print("review already posted", review_posted)
            return redirect("/book/"+isbn)

        #execute and commit review
        db.execute("INSERT INTO reviews (userid, isbn, date, content, rating) VALUES (:userid, :isbn, :date, :content, :rating)",
        {"userid":session['userid'],
        "isbn":isbn,
        "date":datetime.datetime.now(),
        "content":request.form.get("comment"),
        "rating":request.form.get("rating")})
        db.commit()
        print("review posted")
        return redirect("/book/"+isbn)
