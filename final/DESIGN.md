# Design Document

## Overview
Merry Giftmas! is a web application that allows users to create and manage their Christmas wishlists, look up other users' lists, and organize Secret Santa groups. The application is built using Python, Flask, SQLite, and Jinja, and designed on the frontend using HTML and CSS. This document outlines the technical design decisions behind the application.


## Authentication System
The application implements a session-based authentication system using Flask-Session. Sessions are stored server-side in the filesystem for security. The login system:
1. Hashes passwords using werkzeug.security
2. Maintains session data to track logged-in users
3. Implements a login_required decorator for protected routes (all routes except login/register)


## Route Structure
The application separates routes based on their functionality, using GET for displaying information and POST for creating/modifying data. Separating concerns between authentication, list management, and Secret Santa features prioritizes security, user experience, and maintainability while keeping the codebase clean and organized under the hood. 

### Authentication Routes
- `/register` (GET, POST)
  - GET: Displays registration form
  - POST: Validates input, hashes password, creates new user in database
  - Checks for username uniqueness before adding user to database

- `/login` (GET, POST)
  - GET: Displays login form
  - POST: Verifies credentials against database, creates session
  - Uses werkzeug.security.check_password_hash for password verification

- `/logout` (GET)
  - Clears user session
  - Redirects to login page

### List Management Routes
- `/` (GET)
  - Displays user's personal Christmas list
  - Queries database for items where user_id matches session
  - Renders items with delete options

- `/add` (GET, POST)
  - GET: Shows form to add new item
  - POST: Validates and adds item to database
  - Associates item with current user's ID

- `/delete_item/<int:item_id>` (POST)
  - Verifies item belongs to current user
  - Removes item from database
  - Returns to homepage with confirmation

- `/lookup` (GET, POST)
  - GET: Displays username search form
  - POST: Searches for and displays another user's list
  - Prevents access to non-existent users
  - Does not allow modification of another user's list

### Secret Santa Routes
- `/secret_santa` (GET, POST)
  - GET: Shows Secret Santa dashboard
    - Shows form to create new group
    - Displays all Secret Santa groups user is a part of
    - Displays user's Secret Santa assignments and group details
  - POST: Creates new Secret Santa group
    - Validates participant list
    - Generates random assignments by shuffling the list and pairing each user with the next user in the list
    - Ensures no self-assignments


## Database Design
The database schema consists of four main SQL tables. I chose to use SQLite instead of a more complex database system for simplicity and portability:

1. `users`: Stores user authentication information
   - `id`: Primary key
   - `username`: Unique identifier for login
   - `hash`: Securely hashed password using werkzeug.security

2. `items`: Stores wishlist items
   - `id`: Primary key
   - `user_id`: Foreign key referencing users
   - `item`: Text description of the wishlist item

3. `secret_santa_groups`: Manages Secret Santa group information
   - `id`: Primary key
   - `group_name`: Name of the group
   - `price_limit`: Maximum gift price
   - `exchange_date`: Date of gift exchange
   - `created_by`: Foreign key referencing users

4. `secret_santa_assignments`: Tracks Secret Santa pairings
   - `id`: Primary key
   - `group_id`: Foreign key referencing secret_santa_groups
   - `santa_id`: Foreign key referencing users (gift giver)
   - `recipient_id`: Foreign key referencing users (gift receiver)

Additional implementation details:
- Indexes are created on frequently queried columns:
  ```sql
  CREATE UNIQUE INDEX username ON users (username);
  CREATE INDEX idx_user_id ON items(user_id);
  ```
- The database connection is managed through a helper function:
  ```python
  def get_db_connection():
      conn = sqlite3.connect('christmas_list.db')
      # Allows column access by name
      conn.row_factory = sqlite3.Row  
      return conn
  ```


## Database Interaction
- Each route that interacts with the database securely:
  - Creates a new connection 
  - Implements parameterized queries for security, preventing SQL injection attacks
  - Closes connections after use


## Error Handling with Informative Messages
The application uses Flask's flash message system to provide clear feedback to users. Messages are displayed as Bootstrap alerts with appropriate styling (green for success, red for errors).

### Success messages include:
- "Registration successful!"
- "Welcome back!"
- "Logged out successfully!"
- "Item added successfully!"
- "Item deleted successfully!"
- "Secret Santa group created successfully!"

### Error messages include:
- "Must provide username"
- "Username already exists"
- "Invalid username and/or password"
- "Must provide an item"
- "User not found"
- "User has no items on their list"

Each message is:
- Displayed at the top of the page
- Styled appropriately based on message type
- Automatically cleared after the next action
- Accompanied by appropriate HTTP status codes when relevant


## Frontend Design
The frontend uses a combination of:
1. HTML with Bootstrap for responsive layout and basic styling
2. HTML with Jinja for dynamic interactions
3. Custom CSS for themed elements (Christmas colors, snowflake patterns on list items, etc.)


