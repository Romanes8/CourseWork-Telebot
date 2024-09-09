import random

from settings import TOKEN, DATA_BASE_NAME, USER, PASSWORD
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import psycopg2


print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = TOKEN
bot = TeleBot(token_bot, state_storage=state_storage)

global conn
with psycopg2.connect(database=DATA_BASE_NAME, user=USER, password=PASSWORD) as conn:

    known_users = [] # СПИСОК ДЛЯ ХРАНЕНИЯ CHAT.ID ПОЛЬЗОВАТЕЛЕЙ
    buttons = [] # СПИСОК КНОПОК ДЛЯ СОЗДАНИЯ КЛАВИАТУРЫ


    def show_hint(*lines):
        return '\n'.join(lines)


    def show_target(data):
        return f"{data['target_word']} -> {data['translate_word']}"


    class Command:
        ADD_WORD = 'Добавить слово ➕'
        DELETE_WORD = 'Удалить слово🔙'
        NEXT = 'Дальше ⏭'


    class MyStates(StatesGroup):
        target_word = State()
        translate_word = State()
        another_words = State()


    @bot.message_handler(commands=['start'])
    def create_cards(message):
        with conn.cursor() as cur:
            cid = message.chat.id
            if cid not in known_users:
                known_users.append(cid)
                cur.execute("""INSERT INTO users_table (user_id) VALUES(%s); 
                                                 """, (cid,));   #ЗАПИСЬ CHAT.ID ПОЛЬЗОВАТЕЛЯ В ТАБЛИЦУ users_table

                cur.execute("""SELECT id FROM users_table
                               WHERE user_id = %s
                               """, (cid,)); #ПОЛУЧЕНИЕ ID ПОЛЬЗОВАТЕЛЯ ДЛЯ ДАЛЬНЕЙШЕГО ИСПОЛЬЗОВАНИЯ В БАЗЕ ДАННЫХ
                global id
                id = tuple(cur.fetchone())[0]

                cur.execute("""INSERT INTO user_words_table (user_id, rus_word, eng_word)
                                   VALUES (%s, 'лето', 'summer'),
                                          (%s, 'весна', 'spring'),
                                          (%s, 'дом', 'hause'),
                                          (%s, 'собака', 'dog'),
                                          (%s, 'год', 'year'),
                                          (%s, 'ручка', 'pen'),
                                          (%s, 'дождь', 'rain'),
                                          (%s, 'зима', 'winter'),
                                          (%s, 'осень', 'autumn'),
                                          (%s, 'кошка', 'cat');""", (id, id, id, id, id, id, id, id, id, id)
                            ); #ЗАПИСЬ НАЧАЛЬНОГО НАБОРА СЛОВ В ТАБЛИЦУ user_words_table ДЛЯ НОВОГО ПОЛЬЗОВАТЕЛЯ

                conn.commit()
                bot.send_message(cid, "Hello, let study English...")
            else:
                pass

            markup = types.ReplyKeyboardMarkup(row_width=2)

            global buttons
            buttons = []

            cur.execute("""SELECT * FROM user_words_table
                                 WHERE user_id = %s
                                 ORDER BY RANDOM()
                                 LIMIT 1
                                 """, (id,)
                        ); #ПОЛУЧЕНИЕ ЦЕЛЕВОГО СЛОВА ИЗ ТАБЛИЦЫ user_words_table НА РУССКОМ И АНГЛИЙСКОМ ЯЗЫКАХ

            word = tuple(cur.fetchone())
            target_word = word[3] #СЛОВО НА АНГЛИЙСКОМ
            translate = word[2] #СЛОВО НА РУССКОМ

            cur.execute("""INSERT INTO user_result_table (user_id, rus_word, eng_word)
                                                VALUES (%s, %s, %s)""",
                        (id, translate, target_word)
                        ); #ЗАПИСЬ ТЕКУЩЕГО СЛОВА В ТАБЛИЦУ РЕЗУЛЬТАТОВ user_result_table

            target_word_btn = types.KeyboardButton(target_word)
            buttons.append(target_word_btn)

            cur.execute("""SELECT * FROM user_words_table
                                 WHERE user_id = %s
                                 ORDER BY RANDOM()
                                 LIMIT 3
                           """, (id,)
                        ); #ПОЛУЧЕНИЕ ТРЕХ СЛУЧАЙНЫХ НЕВЕРНЫХ ВАРИАНТА НА АНГЛИЙСКОМ ИЗ БАЗЫ ДАННЫХ
            wrong_words = tuple(cur.fetchall())
            others = [wrong_words[0][3], wrong_words[1][3], wrong_words[2][3]]
            other_words_btns = [types.KeyboardButton(word) for word in others]
            buttons.extend(other_words_btns)
            random.shuffle(buttons)
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])

            markup.add(*buttons)

            greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
            bot.send_message(message.chat.id, greeting, reply_markup=markup)
            bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['target_word'] = target_word
                data['translate_word'] = translate
                data['other_words'] = others


    # ФУНКЦИЯ ВЫЗОВА ФУНКЦИИ create_cards ПРИ НАЖАТИИ КНОПКИ "ДАЛЬШЕ"
    @bot.message_handler(func=lambda message: message.text == Command.NEXT)
    def next_cards(message):
        try:
            create_cards(message)
        except IndexError:
            print("Недостаточно слов в базе данных.")


    # ФУНКЦИЯ УДАЛЕНИЯ СЛОВА, ВЫЗЫВАЕМАЯ НАЖАТИЕМ КНОПКИ "УДАЛИТЬ СЛОВО". ЗАПРАШИВАЕТ И ПЕРЕДАЕТ СЛОВО В ФУНКЦИЮ enter_del_word
    @bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
    def delete_word(message):
        chat_id = message.chat.id
        bot.send_message(chat_id, 'Введите слово для удаления')
        bot.register_next_step_handler(message, enter_del_word)


    #ФУНКЦИЯ УДАЛЕНИЯ СЛОВА, ПОЛУЧАЕТ СЛОВО ОТ ФУНКЦИИ delete_word И УДАЛЯЕТ ИЗ ТАБЛИЦЫ user_words_table У КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ ПО ID
    def enter_del_word(message):
        chat_id = message.chat.id
        del_word = message.text
        bot.send_message(chat_id,  f'Слово "{del_word}" удалено')
        with conn.cursor() as cur:
            cur.execute("""DELETE FROM user_words_table
                                WHERE user_id = %s AND rus_word = %s
                                """, (id, del_word)
                        );


    #ФУНКЦИЯ ДОБАВЛЕНИЯ СЛОВА, ВЫЗЫВАЕМАЯ НАЖАТИЕМ КНОПКИ "ДОБАВИТЬ СЛОВО". ЗАПРАШИВАЕТ И ПЕРЕДАЕТ СЛОВО НА РУССКОМ ЯЗЫКЕ В ФУНКЦИЮ enter_rus_word
    @bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
    def add_word(message):
        chat_id = message.chat.id
        bot.send_message(chat_id, 'Введите слово на русском языке')
        bot.register_next_step_handler(message, enter_rus_word)


    #ФУНКЦИЯ ДОБАВЛЕНИЯ СЛОВА, ПРИНИМАЕТ СЛОВО НА РУССКОМ ИЗ ФУНКЦИИ add_word, ДОБАВЛЯЕТ В ТАБЛИЦУ user_words_table ДЛЯ
    #КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ ПО ID И ЗАПРАШИВАЕТ ПЕРЕВОД СЛОВА НА АНГЛИЙСКОМ ЯЗЫКЕ
    def enter_rus_word(message):
        chat_id = message.chat.id
        global ru_word
        ru_word = message.text
        bot.send_message(chat_id, f'Введите перевод слова "{ru_word}" на английском языке')
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO user_words_table (user_id, rus_word)
                                 VALUES(%s, %s);
                                 """, (id, ru_word));
        bot.register_next_step_handler(message, enter_eng_word)


    # ФУНКЦИЯ ДОБАВЛЕНИЯ СЛОВА, ПРИНИМАЕТ СЛОВО НА АНГЛИЙСКОМ ИЗ ФУНКЦИИ enter_rus_word, ДОБАВЛЯЕТ В ТАБЛИЦУ user_words_table ДЛЯ
    # КОНКРЕТНОГО ПОЛЬЗОВАТЕЛЯ ПО ID К РАНЕЕ ДОБАВЛЕННОМУ СЛОВУ НА РУССКОМ В КАЧЕСТВЕ ПЕРЕВОДА
    def enter_eng_word(message):
        chat_id = message.chat.id
        en_word = message.text
        bot.send_message(chat_id, f'Слово "{ru_word}" - "{en_word}" добавлено')
        with conn.cursor() as cur:
            cur.execute("""UPDATE user_words_table
                                 SET eng_word = %s
                                 WHERE user_id = %s AND rus_word = %s
                                 """, (en_word, id, ru_word));


    # ФУНКЦИЯ ОБРАБОТКИ ВАРИАНТА ОТВЕТА ПОЛЬЗОВАТЕЛЯ
    @bot.message_handler(func=lambda message: True, content_types=['text'])
    def message_reply(message):
        text = message.text
        markup = types.ReplyKeyboardMarkup(row_width=2)
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            target_word = data['target_word']
            if text == target_word:
                hint = show_target(data)
                hint_text = ["Отлично!❤", hint]
                next_btn = types.KeyboardButton(Command.NEXT)
                add_word_btn = types.KeyboardButton(Command.ADD_WORD)
                delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
                hint = show_hint(*hint_text)
            else:
                for btn in buttons:
                    if btn.text == text:
                        btn.text = text + '❌'
                        break
                hint = show_hint("Допущена ошибка!",
                                 f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
        markup.add(*buttons)
        bot.send_message(message.chat.id, hint, reply_markup=markup)
        with conn.cursor() as cur:
            cur.execute("""UPDATE user_result_table
                                 SET user_answer = %s
                                 WHERE user_id = %s AND eng_word = %s
                                 """, (text, id, target_word)
                        ); # ЗАПИСЬ ОВЕТА ПОЛЬЗОВАТЕЛЯ В ТАБЛИЦУ user_result_table ДЛЯ ТЕКУЩЕГО СЛОВА

    bot.add_custom_filter(custom_filters.StateFilter(bot))

    bot.infinity_polling(skip_pending=True)


















