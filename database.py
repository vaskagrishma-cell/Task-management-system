
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().with_name(".env")
load_dotenv(ENV_FILE)

def get_db_connection():
    ca_file = os.getenv("MYSQL_SSL_CA", "").strip()
    if not ca_file:
        raise ValueError("MYSQL_SSL_CA is missing from the .env file.")

    ca_path = Path(ca_file)
    if not ca_path.is_absolute():
        ca_path = ENV_FILE.parent / ca_path
    if not ca_path.is_file():
        raise FileNotFoundError(
            f"MySQL CA certificate not found: {ca_path}. "
            "Download the CA certificate from Aiven and save it at this path."
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        port=int(os.getenv("MYSQL_PORT", "17911")),
        database=os.getenv("MYSQL_DATABASE", "defaultdb"),
        ssl_ca=str(ca_path),
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )

def init_db():
    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                due_date DATE NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        connection.commit()
        cursor.close()

    finally:
        connection.close()
