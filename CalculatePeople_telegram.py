import os
import telebot
import psycopg2
import CalculatePeople_telegram_function as bot_f

TOKEN = '7067388213:AAEWGOHb1uOzmlOzczYbKYx8_D5IG57W6rs'

bot = telebot.TeleBot(TOKEN)
# какие команды отслеживать будем

@bot.message_handler(commands=['start'])
def start(message):
    sOut = 'Для выполнения команд введите в поле символ:\n'
    sOut += '? - справка\n'
    sOut += 'sp - список об-тов наблюдения\n'
    sOut += '* - последние фото со всех объектов\n'
    sOut += 'id объекта (число) - информация по объекту'
    bot.send_message(message.chat.id, sOut, parse_mode='html')


# отслеживаем ввод пользователя
@bot.message_handler()
def get_user_text(message):
    bot_f.insert_user_into_spisok(message)
    if message.text == '?':
        sOut = 'Для выполнения команд введите в поле символ:\n'
        sOut += '? - справка\n'
        sOut += 'sp - список об-тов наблюдения\n'
        sOut += '* - последние фото со всех объектов\n'
        sOut += 'id объекта (число) - информация по объекту'
    elif message.text.lower() in ['sp', 'spisok', 'сп', 'список']:
        # выводим список объектов
        sOut = bot_f.get_spisok_kamer()
    elif message.text.lower() in ['*', 'all', 'все', 'всё']:
        # выводим полный список фото
        bot_f.get_photos_kamer(bot, message)
        return
    elif bot_f.is_number(message.text):
        # выводим определённый объет
        bot_f.get_photos_kamer(bot, message)
        return
    else:
        sOut = '/start'
    bot.send_message(message.chat.id, sOut, parse_mode='html')


# Передаём команду в бот
bot.polling(none_stop=True)

