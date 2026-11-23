import psycopg2

def get_connection():
    return psycopg2.connect(
        dbname="pechenka", user="postgres", password="0000",
        host="localhost", port="5432"
    )
