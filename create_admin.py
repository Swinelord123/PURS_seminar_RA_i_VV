from werkzeug.security import generate_password_hash
import pymysql, cryptography

DB_HOST = "localhost"
DB_USER = "esp32_app"
DB_PASS = "strong-db-password"
DB_NAME = "esp32_db"

username = "admin"
password = "admin123"   # CHANGE AFTER TESTING

hash_pw = generate_password_hash(password)

con = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME
)

with con.cursor() as cur:
    cur.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (username, hash_pw)
    )
    con.commit()

con.close()

print("Admin user created")