import bcrypt

# The script will use the password you already entered: "password123"
password_to_hash = "password123".encode('utf-8')

# Generate a hashed password
hashed_password = bcrypt.hashpw(password_to_hash, bcrypt.gensalt())

print("Copy the following hashed password and update your Streamlit secrets:")
# The decode() is important to get the string representation
print(hashed_password.decode('utf-8'))

