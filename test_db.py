import psycopg2

# подключаемся к служебной базе postgres
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="0000",
    host="localhost",
    port="5432"
)
conn.autocommit = True
cur = conn.cursor()

# создаём рабочую базу (если ещё не создана)
try:
    cur.execute("CREATE DATABASE pechenka;")
    print("База pechenka создана")
except psycopg2.errors.DuplicateDatabase:
    print("База pechenka уже существует")

cur.close()
conn.close()

