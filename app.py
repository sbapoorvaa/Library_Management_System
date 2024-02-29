from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3
import requests

app = Flask(__name__)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

CORS(app, supports_credentials=True)

app.secret_key = "my_key"
# Function to authenticate user credentials

def authenticate_user(username, password):
    conn = sqlite3.connect('testDB.db')
    c = conn.cursor()
    c.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    # print(user)
    conn.close()
    return user

def authorized_student_page():
    # print(session)
    if 'privileges' in session:
        privileges = session['privileges']
        if privileges >= 1:
            return True
        else:
            return False
    else:
        # 'privileges' key is not found in the session, user is not authenticated
        return False
    
@app.route('/librarian-privilege', methods=['GET'])
def privilege_return():
    if authorized_librarian_page():
        return jsonify({'privilege' : 'librarian'})
    else:
        return jsonify({'privilege': 'student'})
    

def authorized_librarian_page():
    if 'privileges' in session:
        privileges = session.get('privileges', 0)
        print(privileges)
        # print(privileges==2)
        if privileges == 2:
            return True
        else:
            return False
    else:
        return False

def exists_in_db(username):
    conn = sqlite3.connect('testDB.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM Users WHERE username=?', (username, ))
    res = cur.fetchall()
    if len(res)>=1:
        return True
    else:
        return False

# Function to fetch book details from external API (e.g., Open Library)
def fetch_book_details(book_title):
    base_url = 'http://openlibrary.org/search.json'
    params = {'title': book_title}
    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        data = response.json()
        if 'docs' in data and len(data['docs']) > 0:
            first_doc = data['docs'][0]
            author_name = first_doc.get('author_name', ['Author name not available'])[0]
            description = first_doc.get('description', 'Description not available')
            isbn = first_doc.get('isbn', ['ISBN not available'])[0]

            book_details = {
                'title': first_doc['title'],
                'author': author_name,
                'description': description,
                'isbn': isbn
            }

            return book_details
        else:
            return {'error': 'No results found for this book title'}
    else:
        return {'error': 'Failed to fetch search results'}


# Route for user login
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = authenticate_user(username, password)
    if user:
        print(user)
        privileges = user[6]
        session['username'] = username
        session['privileges'] = privileges
        print(privileges)
        session.permanent_session_lifetime = True
        
        if privileges == 1:
            response = jsonify({'message': 'student'})
            response.headers.add('Access-Control-Expose-Headers', 'Set-Cookie')
            
            return response, 200
        elif privileges == 2:
            response = jsonify({'message': 'librarian'})
            response.headers.add('Access-Control-Expose-Headers', 'Set-Cookie')
            return response, 200
    else:
        if exists_in_db(username):
            return jsonify({'message' : 'wrong password'}), 200
        return jsonify({'message': 'Bad'}), 401



@app.route('/book-details', methods=['GET'])
def get_book_details():
    if(not authorized_student_page):
        return jsonify({'message': 'unauthorized'})
    book_title = request.args.get('title')
    if book_title:
        external_book_details = fetch_book_details(book_title)  # Fetch details from external API

        if 'isbn' in external_book_details:
            isbn = external_book_details['isbn']
            open_library_api_url = f'https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=details'
            open_library_response = requests.get(open_library_api_url)
            
            if open_library_response.status_code == 200:
                open_library_data = open_library_response.json()
                book_info = open_library_data.get(f'ISBN:{isbn}', {})
                description = book_info.get('details', {}).get('description', 'Description not available')

                # Append API values with local book details
                external_book_details['description'] = description
                
                # Fetch local book details
                local_book_data = fetch_local_details(book_title)

                external_book_details['local_book_data'] = local_book_data

                return jsonify(external_book_details)
            else:
                return jsonify({'error': 'Failed to fetch additional book details from external API'}), 500
        else:
            return jsonify({'error': 'No book details found for the given title'}), 404
    else:
        return jsonify({'error': 'Book title parameter is missing'}), 400

def fetch_local_details(book_title):
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE Title LIKE ?", (f"%{book_title}%",))
    books = cursor.fetchall()
    conn.close()

    return books[0]

# Route for fetching all books or filtered by genre
@app.route('/view', methods=['GET'])
def fetch_books():
    # print(session)
    if(not authorized_student_page()):
        return jsonify({'message': 'unauthorized'})
    genre = request.args.get('genre') # Get the genre from query parameters
    title = request.args.get('title') # Get the title from query parameters
    author = request.args.get('author') # Get the author from query parameters
    
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    
    if genre: # If genre is specified, filter by genre
        if title: # If title is specified, filter by title and optionally by author
            if author:
                cursor.execute("SELECT * FROM books WHERE Bookshelf=? AND Title LIKE ? AND Author LIKE ?", (genre, f"%{title}%", f"%{author}%"))
            else:
                cursor.execute("SELECT * FROM books WHERE Bookshelf=? AND Title LIKE ?", (genre, f"%{title}%"))
        elif author: # If only author is specified, filter by author
            cursor.execute("SELECT * FROM books WHERE Bookshelf=? AND Author LIKE ?", (genre, f"%{author}%"))
        else: # If no title or author is specified, fetch all books for the selected genre
            cursor.execute("SELECT * FROM books WHERE Bookshelf=?", (genre,))
    else: # If genre is not specified, fetch all books
        if title: # If title is specified, filter by title and optionally by author
            if author:
                cursor.execute("SELECT * FROM books WHERE Title LIKE ? AND Author LIKE ?", (f"%{title}%", f"%{author}%"))
            else:
                cursor.execute("SELECT * FROM books WHERE Title LIKE ?", (f"%{title}%",))
        elif author: # If only author is specified, filter by author
            cursor.execute("SELECT * FROM books WHERE Author LIKE ?", (f"%{author}%",))
        else: # If no title or author is specified, fetch all books
            cursor.execute("SELECT * FROM books")

    books = cursor.fetchall()
    conn.close()
    
    return jsonify(books)

# Route to fetch all genres
@app.route('/genres', methods=['GET'])
def fetch_genres():
    # print(session)
    if(not authorized_student_page):
        return jsonify({'message': 'unauthorized'})
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Bookshelf FROM books")
    genres = [row[0] for row in cursor.fetchall()]
    conn.close()

    return jsonify(genres)
@app.route('/check-if-issued', methods=['GET'])
def check_if_issued():
    # print(session)
    if (not authorized_student_page):
        return jsonify({'message': 'unauthorized'})
    username = session.get('username')
    title = request.args.get('title')
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    # print(username , title)
    cursor.execute("SELECT * FROM Requests WHERE username LIKE ? AND book_title LIKE ? AND status < 1", (username, title))
    res = cursor.fetchall()
    if (len(res) > 0):
        conn.close()
        return jsonify({'message': 'Book has already been requested'}), 409
    
    cursor.execute("SELECT * FROM Borrowings WHERE username LIKE ? AND book_title LIKE ?", (username, title))
    res = cursor.fetchall()
    if(len(res)> 0):
        conn.close()
        return jsonify({'message' : 'The book has already been borrowed'}), 409

    cursor.execute("SELECT * FROM Requests WHERE username LIKE ?", (username,))
    res = cursor.fetchall()
    ans = len(res)
    cursor.execute("SELECT * FROM Borrowings WHERE username LIKE ?", (username,))
    res = cursor.fetchall()
    ans += len(res)
    # print(ans)
    if(ans > 5):
        # print('returning')
        conn.close()
        return jsonify({'message' : 'More that 5 books cannot be Requested/Borrowed at a time'}), 409
    
    conn.close()
    return jsonify({'message' : 'proceed'}), 200

@app.route('/request-book', methods=['GET'])
def request_book():
    # print(session)
    if (not authorized_student_page()):
        return jsonify({'message': 'unauthorized'})
    username = session.get('username')
    title = request.args.get('title')
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Requests (username, book_title, request_date, status) VALUES (?, ?, DATE('now'), 0);", (username, title))
    conn.commit()
    if cursor.rowcount > 0:
        conn.close()
        return jsonify({'message': 'Requested Successfully!'})
    else:
        conn.rollback()  
        conn.close()
        return jsonify({'message': 'Failed to request the book. Please try again.'}), 500  

@app.route('/pending-requests', methods=['GET'])
def pending_requests():
    
    if (not authorized_librarian_page()):
        return jsonify({'message': 'unauthorized'})
    
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Requests');
    pending_requests = cursor.fetchall()
    conn.close()
    return jsonify({'pendingRequests': pending_requests})

@app.route('/approve-request', methods=['POST'])
def approve_request():
    if(not authorized_librarian_page()):
        return jsonify({'message': 'unauthorized'})
    request_id = request.args.get('request_id')
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Requests WHERE request_id = ?", (request_id,))
        request_data = cursor.fetchone()

        if not request_data:
            return jsonify({'message': 'Request not found'}), 404

        # Check if the quantity of the requested book is greater than 0
        cursor.execute("SELECT quantity FROM books WHERE Title = ?", (request_data[2],))
        quantity = cursor.fetchone()[0]
        if quantity <= 0:
            return jsonify({'message': 'Quantity of the requested book is insufficient to approve the request'}), 400

        # Reduce quantity of the book
        cursor.execute("UPDATE books SET quantity = quantity - 1 WHERE Title = ?", (request_data[2],))

        # Insert into Borrowings table
        cursor.execute("INSERT INTO Borrowings (username, book_title, date_borrowed, date_due) VALUES (?, ?, DATE('now'), DATE('now', '+7 days'))", (request_data[1], request_data[2]))
        
        # Delete from Requests table
        cursor.execute("DELETE FROM Requests WHERE request_id = ?", (request_id,))
        
        conn.commit()
        return jsonify({'message': 'Request approved successfully'}), 200

    except Exception as e:
        
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/borrowed-books', methods=['GET'])
def borrowed_books():
    if (not authorized_librarian_page()):
        return jsonify({'message': 'unauthorized'})
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Borrowings ORDER BY date_due');
    borrowed_books = cursor.fetchall()
    conn.close()
    return jsonify({'borrowedBooks': borrowed_books})

@app.route('/revoke-access', methods=['POST'])
def revoke_access():
    if (not authorized_librarian_page()):
        return jsonify({'message': 'unauthorized'})
    username = request.args.get('username')
    title = request.args.get('title')
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    try:
        # Increase the quantity of the book by 1
        cursor.execute('UPDATE books SET quantity = quantity + 1 WHERE Title = ?', (title,))
        
        # Delete the book record from Borrowings
        cursor.execute('DELETE FROM Borrowings WHERE username=? AND book_title=?', (username, title))
        
        conn.commit()
        return jsonify({'message': 'Access revoked successfully'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/username', methods=['GET'])
def get_username():
    if 'username' in session:
        user_name = session['username']
        return jsonify({'username': user_name}),200
    return jsonify({'message': 'NOTLOGGEDIN'})

@app.route('/readlink', methods=['GET'])
def read_link():
    if (not authorized_student_page()):
        return jsonify({'message': 'unauthorized'})
    title = request.args.get('title')
    # print(title)
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute('SELECT Readlink FROM books WHERE Title=?', (title,))
    val = cursor.fetchone()
    # print(val)
    conn.close()
    return jsonify({'link' : val}), 200


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    session.pop('privileges', 0)
    return jsonify({'message': 'Logged Out'}), 200

@app.route('/current-books', methods=['GET'])
def get_current_books():
    if (not authorized_student_page()):
        return jsonify({'message': 'unauthorized'})
    
    username = session.get('username')
    # print(username)
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT book_title, date_borrowed, date_due FROM Borrowings WHERE username = ?;", (username,))
    books = cursor.fetchall()
    
    conn.close()
    return jsonify({'current_books': books}),200

# Endpoint to retrieve current requests for a user
@app.route('/current-requests', methods=['GET'])
def get_current_requests():
    if (not authorized_student_page()):
        return jsonify({'message': 'unauthorized'})
    
    username = session.get('username')
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute("SELECT book_title, request_date FROM Requests WHERE username = ?;", (username,))
    requests = cursor.fetchall()
    # print(requests)
    conn.close()
    return jsonify({'current_requests': requests}),200

@app.route('/cancel-request', methods=['DELETE'])
def delete_req():
    if(not authorized_student_page()):
        return jsonify({'message': 'unauthorized'})
    try:
        username = session['username']
        title = request.args.get('title')

        # Connect to the SQLite database
        conn = sqlite3.connect('testDB.db')
        cursor = conn.cursor()
        print(username, title)
        # Execute the SQL DELETE statement to remove the request
        cursor.execute("DELETE FROM Requests WHERE username=? AND book_title=?", (username, title))
        conn.commit()

        # Close the database connection
        conn.close()

        return jsonify({'message': 'Request deleted successfully'}), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500
    
@app.route('/return-book', methods=['DELETE'])
def delete_borrowing():
    if(not authorized_student_page()):
        return jsonify({'message': 'unauthorized'})
    try:
        username = session['username']
        title = request.args.get('title')

        # Connect to the SQLite database
        conn = sqlite3.connect('testDB.db')
        cursor = conn.cursor()
        print(username, title)
        # Execute the SQL DELETE statement to remove the request
        cursor.execute("DELETE FROM Borrowings WHERE username=? AND book_title=?", (username, title))
        conn.commit()

        conn.close()
        return jsonify({'message': 'Request deleted successfully'}), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 500

@app.route('/check-authentication-user', methods=['GET'])
def check_student_auth():
    if authorized_student_page():
        return jsonify({'isAuthenticated' : True})
    else:
        return jsonify({'isAuthenticated' : False})
    
@app.route('/check-authentication-librarian', methods=['GET'])
def check_lib_auth():
    if authorized_librarian_page():
        return jsonify({'isAuthenticated' : True})
    else:
        return jsonify({'isAuthenticated' : False})


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    role = data.get('role')
    username = data.get('username')
    password = data.get('password')

    department = data.get('department')
    year = data.get('year')

    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return jsonify({'error': 'Username already exists'}), 400
    
    if role == 'student':
        cursor.execute("INSERT INTO users (role, username, password, department, year, privileges) VALUES (?, ?, ?, ?, ?, ?)",
                       (role, username, password, department, year, 1))
        privilege = 1
    elif role == 'librarian':
        temp = "-"
        cursor.execute("INSERT INTO users (role, username, password, department, year, privileges) VALUES (?, ?, ?, ?, ?, ?)",
                       (role, username, password, temp, temp, 2))
        privilege = 2
    else:
        conn.close()
        return jsonify({'error': 'Invalid role'}), 400

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()

    return jsonify({'message': 'User registered successfully', 'privilege': privilege}), 201

@app.route('/post-comment', methods=['POST'])
def post_comment():
    if not authorized_student_page:
        return jsonify({"UNAUTHORIZED"})
    conn = sqlite3.connect('testDB.db')
    c = conn.cursor()
    data = request.json
    print(data)
    username = session['username']
    title = data.get('title')
    comment = data.get('comment')
    rating = data.get('rating')
    print(username)
    c.execute('INSERT INTO comments (username, title, comment, rating) VALUES (?, ?, ?, ?)', (username, title, comment, rating))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Comment posted successfully'})

# Route to get comments by title
@app.route('/get-comments', methods=['GET'])
def get_comments():
    if not authorized_student_page:
        return jsonify({"error": "UNAUTHORIZED"}), 401
    
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "Title parameter is missing"}), 400

    try:
        conn = sqlite3.connect('testDB.db')
        c = conn.cursor()
        c.execute('SELECT * FROM comments WHERE title = ?', (title,))
        comments = c.fetchall()
        conn.close()
        return jsonify({'comments': comments}), 200
    except sqlite3.Error as e:
        print("SQLite error:", e)
        return jsonify({'error': 'An error occurred while accessing the database'}), 500


# Define routes
@app.route('/create_book', methods=['POST'])
def create_book():
    if not authorized_librarian_page():
        return jsonify({'message':'UNAUTHORIZED'});
    data = request.json
    print(data)
    title = data.get('title')
    author = data.get('author')
    link = data.get('link')
    bookshelf = data.get('bookshelf')
    read_link = data.get('readlink')
    img_link = data.get('imglink')
    quantity = data.get('quantity')
    
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Books (Title, Author, Link, Bookshelf, Readlink, Imglink, Quantity) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (title, author, link, bookshelf, read_link, img_link, quantity))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Book created successfully'}), 201

@app.route('/update-book', methods=['PUT'])
def update_book():
    if not authorized_librarian_page():
        return jsonify({'message': 'UNAUTHORIZED'});
    data = request.json
    title = data.get('title')

    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()

    cursor.execute("UPDATE Books SET Author=?, Link=?, Bookshelf=?, Readlink=?, Imglink=?, Quantity=? WHERE Title=?",
                   (data.get('author'), data.get('link'), data.get('bookshelf'), data.get('readlink'), data.get('imglink'), data.get('quantity'), title))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Book updated successfully'}), 200

@app.route('/delete_book', methods=['DELETE'])
def delete_book():
    if not authorized_librarian_page():
        return jsonify({'message':'UNAUTHORIZED'});
    title = request.json.get('title')
    print(title)
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Books WHERE Title=?', (title,))
    res = cursor.fetchall()
    if len (res) <=0:
        conn.close()
        return jsonify({'message', 'Cannot Delete! book currently issued!'})
    cursor.execute("DELETE FROM Books WHERE Title=?", (title,))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Book deleted successfully'}), 200


@app.route('/update-fetch', methods=['GET'])
def get_for_update():
    title = request.args.get('title')
    print(title)
    conn = sqlite3.connect('testDB.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Books WHERE Title=?", (title,))
    res = cursor.fetchone()
    conn.close()
    return jsonify({'values': res}), 200
if __name__ == '__main__':
    app.run(debug=True)

