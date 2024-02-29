import sqlite3
import csv
import random
# Define the file path for the CSV file
csv_file = 'modified_file.csv'

# Define the SQLite database file path
db_file = 'testDB.db'

# Define the SQL command to create the table
create_table_sql = """
CREATE TABLE IF NOT EXISTS Books (
    Title TEXT,
    Author TEXT,
    Link TEXT,
    Bookshelf TEXT,
    Readlink TEXT,
    Imglink TEXT,
    Quantity INTEGER
);
"""

# Define the SQL command to insert data into the table
insert_data_sql = """
INSERT INTO Books (Title, Author, Link, Bookshelf, Readlink, Imglink, Quantity)
VALUES (?, ?, ?, ?, ?, ?, ?);
"""

# Connect to the SQLite database
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Create the table if it doesn't exist
cursor.execute(create_table_sql)

# Read data from the CSV file and insert it into the table
with open(csv_file, 'r', newline='', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip the header row
    for row in reader:
        row = row + [random.randint(1,10)]
        cursor.execute(insert_data_sql, row)

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Data has been inserted into the SQLite database.")
