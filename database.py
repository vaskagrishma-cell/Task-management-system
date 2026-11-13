
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def _connection_settings():
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
    }


def get_db_connection():
    return mysql.connector.connect(
        **_connection_settings(),
        database="task_management_db"
    )


def init_db():
    connection = mysql.connector.connect(**_connection_settings())

    try:
        cursor = connection.cursor()
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS task_management_db"
        )
        cursor.close()
    finally:
        connection.close()

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
