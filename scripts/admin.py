from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import getpass
import sys

# Connect to MongoDB (update URI if needed)

mongohostIP = input("MongoHostIP: ")
mongodb = "mongodb://" +mongohostIP+ ":27017/"
client = MongoClient(mongodb)
db = client["scp"]
users_collection = db["users"]


# Get user input
username = input("Admin Username: ")

# Check if username already exists
existing_user = users_collection.find_one({"username": username})
if existing_user:
    print(f"❌ Admin Username '{username}' already exists. Choose a different one.")
    sys.exit(1)


email = input("Email: ")
firstname = input("First name: ")
lastname = input("Last name: ")
password = getpass.getpass("Password (hidden input): ")

# Hash the password
hashed_password = generate_password_hash(password)

# Create user document
user_doc = {
    "username": username,
    "email": email,
    "firstname": firstname,
    "lastname": lastname,
    "is_admin": True,
    "is_active": True,
    "is_super": True,
    "password": hashed_password
}

# Insert into MongoDB
result = users_collection.insert_one(user_doc)

print(f"✅ User inserted with ID: {result.inserted_id}")
