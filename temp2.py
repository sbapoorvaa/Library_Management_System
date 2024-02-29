import csv
import sqlite3
import random

def read_book_titles_from_csv(csv_file):
    book_titles = []
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  
        for row in reader:
            book_titles.append(row[0]) 
    return book_titles

def insert_dummy_comments(book_titles):
    conn = sqlite3.connect('testDB.db')
    c = conn.cursor()
    for title in book_titles:
        num_comments = random.randint(1, 2) 
        for _ in range(num_comments):
            comment = f"This is a dummy comment for the book '{title}'."
            rating = random.randint(1, 5) 
            c.execute('''INSERT INTO comments (username, title, comment, rating) 
                         VALUES (?, ?, ?, ?)''', ('dummy_user', title, comment, rating))
    conn.commit()
    conn.close()


def main():
    csv_file = 'modified_file.csv' 
    book_titles = read_book_titles_from_csv(csv_file)
    insert_dummy_comments(book_titles)
    print("Dummy comments added successfully.")

if __name__ == "__main__":
    main()
