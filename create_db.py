import psycopg2
import hashlib

conn = psycopg2.connect(
    dbname="pechenka", user="postgres", password="0000",
    host="localhost", port="5432"
)
conn.autocommit = True
cur = conn.cursor()

# 1. Сначала снимаем старое ограничение
cur.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;")

# 2. Потом приводим роли существующих пользователей к списку из ТЗ
cur.execute("UPDATE users SET role = 'Менеджер' WHERE login = 'manager';")
cur.execute("UPDATE users SET role = 'Администратор цеха' WHERE login = 'admin';")

# 3. И только теперь навешиваем новое ограничение
cur.execute("""
ALTER TABLE users ADD CONSTRAINT users_role_check
CHECK (role IN ('Менеджер', 'Администратор цеха', 'Кладовщик',
                'Системный администратор', 'Директор'));
""")


def add_user(login, password, full_name, role):
    # создаём, если ещё нет; пароль — сразу хешем
    cur.execute("SELECT 1 FROM users WHERE login = %s;", (login,))
    if cur.fetchone():
        cur.execute("UPDATE users SET password = %s, role = %s WHERE login = %s;",
                    (hashlib.sha256(password.encode()).hexdigest(), role, login))
    else:
        cur.execute(
            "INSERT INTO users (login, password, full_name, role) VALUES (%s, %s, %s, %s);",
            (login, hashlib.sha256(password.encode()).hexdigest(), full_name, role)
        )

add_user("admin",     "admin123",     "Иванов Иван Иванович",     "Администратор цеха")
add_user("manager",   "manager123",   "Петрова Анна Сергеевна",   "Менеджер")
add_user("keeper",    "keeper123",    "Смирнов Олег Валерьевич",  "Кладовщик")
add_user("sysadmin",  "sysadmin123",  "Кузнецов Денис Игоревич",  "Системный администратор")
add_user("director",  "director123",  "Орлова Елена Викторовна",  "Директор")

print("Роли приведены к ТЗ: 5 пользователей готовы")

cur.close()
conn.close()
