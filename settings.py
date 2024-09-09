import psycopg2


TOKEN = "  "         #ВВЕДИТЕ TOKEN ВАШЕГО ТЕЛЕГРАМ БОТА
DATA_BASE_NAME = " " #ВВЕДИТЕ ИМЯ БАЗЫ ДАННЫХ
USER = " "           #ВВЕДИТЕ ИМЯ ПОЛЬЗОВАТЕЛЯ БАЗЫ ДАННЫХ
PASSWORD = " "       #ВВЕДИТЕ ПАРОЛЬ ПОЛЬЗОВАТЕЛЯ БАЗЫ ДАННЫХ

#СОЗДАНИЕ ТАБЛИЦ users_table, user_words_table, user_result_table
with psycopg2.connect(database=DATA_BASE_NAME, user=USER, password=PASSWORD) as conn:
    with conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS users_table
                            (id SERIAL PRIMARY KEY,
                            user_id BIGINT NULL
                            );"""
                    );

        cur.execute("""CREATE TABLE IF NOT EXISTS user_words_table
                                (id SERIAL PRIMARY KEY,
                                user_id INT NOT NULL REFERENCES users_table(id),
                                rus_word VARCHAR(30) NULL,
                                eng_word VARCHAR(30) NULL
                                );"""
                    );

        cur.execute("""CREATE TABLE IF NOT EXISTS user_result_table
                                (id SERIAL PRIMARY KEY,
                                user_id INT NOT NULL REFERENCES users_table(id),
                                rus_word VARCHAR(30) NULL,
                                eng_word VARCHAR(30) NULL,
                                user_answer VARCHAR(30) NULL
                                );"""
                    );
        conn.commit()


