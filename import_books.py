import os,csv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

file = open("books.csv")

csv_reader = csv.reader(file)

line_count = 0

for isbn, title, author, year in csv_reader:

    if line_count>0:

        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn,
                 "title": title,
                 "author": author,
                 "year": year})
        db.commit()
        print("added ",line_count,isbn,title,author,year, sep=' ')

    line_count+=1
