import telebot
import schedule
import time
from threading import Thread
from datetime import datetime, timedelta

API_TOKEN = '7449813614:AAGlnrd3KiVrmUyM4VaFYu7UIFlzFfLFtGg'
ADMIN_PASSWORD = 'Yb72y'

bot = telebot.TeleBot(API_TOKEN)

admins = set()
subscribers = {}  # Используем словарь для хранения информации о пользователях
messages_to_send = {}
user_answers = {}  # Словарь для хранения ответов пользователей
user_questions = {}  # Словарь для хранения текущих вопросов для пользователей
questions_for_meetup = {}  # Словарь для хранения вопросов митапа
meetup_commands = {}  # Словарь для хранения команд для каждого митапа
command_counter = 1

# Команда для назначения администратора
@bot.message_handler(commands=['setadmin'])
def set_admin(message):
    global admins
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Использование: /setadmin пароль")
    else:
        password = args[1]
        if password == ADMIN_PASSWORD:
            if len(admins) < 4:
                admins.add(message.from_user.id)
                bot.reply_to(message, "Вы назначены администратором.")
            else:
                bot.reply_to(message, "Количество администраторов достигло максимума.")
        else:
            bot.reply_to(message, "Неверный пароль.")

# Обработчик для кнопки "Старт"
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    if user_id not in subscribers:
        bot.send_message(message.chat.id, "Введите ваш ник:")
        bot.register_next_step_handler(message, process_nickname)
    else:
        bot.reply_to(message, "Вы уже в списке получателей уведомлений.")



    

def process_nickname(message):
    user_id = message.from_user.id
    nickname = message.text
    subscribers[user_id] = nickname
    bot.reply_to(message, f"Вы добавлены в список получателей уведомлений под ником {nickname}.")

admin_steps = {}

# Шаг 1: Запрос даты и времени
def request_date_time(message):
    if message.from_user.id in admins:
        bot.send_message(message.chat.id, "Введите дату и время в формате ДД.MM ЧЧ:ММ")
        bot.register_next_step_handler(message, process_date_time)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")

# Шаг 2: Обработка даты и времени и запрос темы митапа
def process_date_time(message):
    try:
        date_time = message.text
        # Проверка формата времени
        datetime.strptime(date_time, "%d.%m %H:%M")
        admin_steps[message.from_user.id] = {'date_time': date_time}
        bot.send_message(message.chat.id, "Введите тему митапа")
        bot.register_next_step_handler(message, process_meetup_topic)
    except ValueError:
        bot.reply_to(message, "Ошибка в формате даты и времени. Попробуйте еще раз.")
        request_date_time(message)

# Шаг 3: Обработка темы митапа и запрос вопросов
def process_meetup_topic(message):
    topic = message.text
    admin_steps[message.from_user.id]['topic'] = topic
    bot.send_message(message.chat.id, "Введите вопросы для подготовки к митапу (каждый вопрос на новой строке)")
    bot.register_next_step_handler(message, process_questions)


# Шаг 4: Обработка вопросов и сохранение уведомления
def process_questions(message):
    global command_counter
    questions = message.text.split('\n')
    admin_id = message.from_user.id
    date_time = admin_steps[admin_id]['date_time']
    topic = admin_steps[admin_id]['topic']
    
    command = f"/submit{command_counter}"
    meetup_commands[command] = date_time
    command_counter += 1

    notification_text = f"Тема митапа: {topic}\nВремя митапа: {date_time}\n\nВопросы для подготовки:\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    if date_time not in messages_to_send:
        messages_to_send[date_time] = []
    messages_to_send[date_time].append(notification_text)
    questions_for_meetup[date_time] = questions
    del admin_steps[admin_id]

    bot.reply_to(message, f"Уведомление добавлено на {date_time}")

    # Отправка уведомления сразу после создания
    immediate_notification_text = f"Запланирован новый митап\n\n{notification_text}\n\nОбязательно нужно ответить на вопросы до начала митапа. Команда для ответа на вопросы: {command}"
    send_notification(date_time, immediate_notification_text, "")

    # Запланировать отправку уведомления
    schedule_notifications(date_time, notification_text, command)

# Команда для добавления уведомления
@bot.message_handler(commands=['add_meetup'])
def add_notification(message):
    if message.from_user.id in admins:
        request_date_time(message)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")

# Функция для отправки уведомлений
def send_notification(date_time, notification_text, extra_message):
    for user_id in subscribers:
        bot.send_message(user_id, notification_text + extra_message)

# Добавляем новую глобальную переменную для хранения итогов митапа
meetup_summaries = {}   

def schedule_notifications(date_time, notification_text, command):
    global command_counter

    meetup_time = datetime.strptime(date_time, "%d.%m %H:%M")
    adjusted_date_time = meetup_time.strftime("%d.%m %H:%M")
    
    # Уведомление за 2 часа
    two_hours_before = (meetup_time - timedelta(hours=2)).strftime("%H:%M")
    schedule.every().day.at(two_hours_before).do(send_notification, date_time=adjusted_date_time, notification_text=notification_text, extra_message=f"\n\nОбязательно нужно ответить на вопросы в ближайший 1 час 55 минут. Команда для ответа на вопросы: {command}")

    # Уведомление за 30 минут
    thirty_minutes_before = (meetup_time - timedelta(minutes=30)).strftime("%H:%M")
    schedule.every().day.at(thirty_minutes_before).do(send_notification, date_time=adjusted_date_time, notification_text=notification_text, extra_message=f"\n\nДля ответов на вопросы осталось 25 минут. Команда для ответа на вопросы: {command}")

    # Уведомление за 5 минут
    five_minutes_before = (meetup_time - timedelta(minutes=5)).strftime("%H:%M")
    schedule.every().day.at(five_minutes_before).do(send_final_notification, date_time=adjusted_date_time, notification_text=notification_text)

    # Уведомление о начале митапа
    schedule.every().day.at(meetup_time.strftime("%H:%M")).do(send_meetup_start_notification, date_time=adjusted_date_time)

    # Уведомление об итогах митапа через 10 минут после начала
    ten_minutes_after = (meetup_time + timedelta(minutes=10)).strftime("%H:%M")
    summary_command = f"/itogy{command_counter}"
    meetup_commands[summary_command] = adjusted_date_time
    schedule.every().day.at(ten_minutes_after).do(send_summary_request, date_time=adjusted_date_time, command=summary_command)

    command_counter += 1

def send_summary_request(date_time, command):
    for admin_id in admins:
        bot.send_message(admin_id, f"Итоги митапа: введите команду {command} для ввода итогов митапа.")

# Обработчик команды для ввода итогов митапа
@bot.message_handler(func=lambda message: message.text.startswith('/itogy'))
def handle_summary_command(message):
    command = message.text.split()[0]
    date_time = meetup_commands[command]
    
    if date_time not in meetup_summaries:
        meetup_summaries[date_time] = {}

    meetup_summaries[date_time]['admin_id'] = message.from_user.id
    meetup_summaries[date_time]['message_id'] = message.message_id

    bot.send_message(message.chat.id, f"Введите итоги митапа для {date_time}")

@bot.message_handler(func=lambda message: message.from_user.id in [s['admin_id'] for s in meetup_summaries.values()])
def save_summary(message):
    for date_time, summary in meetup_summaries.items():
        if summary['admin_id'] == message.from_user.id:
            meetup_summaries[date_time]['summary'] = message.text
            bot.send_message(message.chat.id, "Итоги митапа сохранены.")
            
            # Рассылка итогов пользователям
            topic = messages_to_send[date_time][0].split('\n')[0].split(': ')[1]
            questions = questions_for_meetup[date_time]
            summary_text = meetup_summaries[date_time]['summary']
            notification_text = (f"Итоги митапа {date_time}\n"
                                 f"Тема была: {topic}\n\n"
                                 "Были вопросы для подготовки:\n" +
                                 "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions)) +
                                 f"\n\nПодведенные итоги:\n{summary_text}")
            
            for user_id in subscribers:
                bot.send_message(user_id, notification_text)

            # Отправка уведомления в чат группы
            # group_chat_id = -1002097051620
            group_chat_id = -4116122569
            bot.send_message(group_chat_id, notification_text)

            break
def send_meetup_start_notification(date_time):
    topic = messages_to_send[date_time][0].split('\n')[0].split(': ')[1]
    for user_id in subscribers:
        bot.send_message(user_id, f"‼️Митап по теме {topic} начался‼️")

        

def send_final_notification(date_time, notification_text):
    for user_id, nickname in subscribers.items():
        if user_id not in user_answers.get(date_time, {}) and user_id not in admins:
            bot.send_message(user_id, "К сожалению, вы не соблюдаете регламент, скоро за такое вам будет начисляться штрафик :)")
        bot.send_message(user_id, f"{notification_text}\n\nМитап начнется через 5 минут.")

    # Отправить ответы админам
    for admin_id in admins:
        answers_text = []
        for uid, answers in user_answers[date_time].items():
            user_answers_text = [f"{subscribers[uid]}:"]
            questions = questions_for_meetup[date_time]
            for i, (question, answer) in enumerate(zip(questions, answers), 1):
                user_answers_text.append(f"{i}. {question}\n{answer}")
            answers_text.append("\n".join(user_answers_text))
        bot.send_message(admin_id, f"".join(answers_text))




# Команда для отправки ответов на вопросы
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/submit'))
def submit_answers(message):
    user_id = message.from_user.id
    command = message.text.split()[0]
    
    if command not in meetup_commands:
        bot.reply_to(message, "Нет запланированных митапов для отправки ответов.")
        return
    
    date_time = meetup_commands[command]

    user_questions[user_id] = {
        'date_time': date_time,
        'current_question': 0,
        'answers': []
    }

    ask_next_question(user_id)

def ask_next_question(user_id):
    date_time = user_questions[user_id]['date_time']
    questions = questions_for_meetup[date_time]
    current_question = user_questions[user_id]['current_question']

    if current_question < len(questions):
        bot.send_message(user_id, f"Вопрос {current_question + 1}: {questions[current_question]}")
        bot.register_next_step_handler_by_chat_id(user_id, process_answer)
    else:
        save_answers(user_id)

def process_answer(message):
    user_id = message.from_user.id
    answer = message.text

    user_questions[user_id]['answers'].append(answer)
    user_questions[user_id]['current_question'] += 1

    ask_next_question(user_id)

def save_answers(user_id):
    date_time = user_questions[user_id]['date_time']
    answers = user_questions[user_id]['answers']

    if date_time not in user_answers:
        user_answers[date_time] = {}
    user_answers[date_time][user_id] = answers

    del user_questions[user_id]
    bot.send_message(user_id, "Ваши ответы получены.")

def get_upcoming_meetup_time():
    now = datetime.now()
    for date_time_str in messages_to_send.keys():
        date_time = datetime.strptime(date_time_str, "%m-%d %H:%M")
        if now < date_time:
            return date_time_str
    return None

# Функция для запуска планировщика
def send_notifications():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запуск бота
def run_bot():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    notification_thread = Thread(target=send_notifications)
    notification_thread.start()
    run_bot()
