import os
import json
import telebot
import requests
import subprocess
import speech_recognition as sr
import spacy

# CONFIG LOAD
with open('config.json') as config_file:
    config = json.load(config_file)


# ADDITIONAL FUNCTIONS
def audio_to_text(file_name):
    subprocess.run(['ffmpeg', '-i', file_name, 'voice_message.wav', '-y'])
    r = sr.Recognizer()
    with sr.AudioFile('voice_message.wav') as source:
        audio = r.record(source)
    text = r.recognize_google(audio, language='ru-RU')
    os.remove(file_name)
    os.remove('voice_message.wav')
    return text


def city_to_coordinates(city):
    params = {
        'apikey': config['yandex_geocoder'],
        'geocode': city,
        'format': 'json',
        'results': 1,
    }
    result = requests.get('https://geocode-maps.yandex.ru/1.x/', params)
    if len(result.json()['response']['GeoObjectCollection']['featureMember']):
        return result.json()['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos'].split(' ')
    else:
        return []


def coordinates_to_weather(coordinates):
    params = {
        'lon': coordinates[0],
        'lat': coordinates[1],
    }
    headers = {
        'X-Yandex-API-Key': config['yandex_weather'],
    }
    result = requests.get('https://api.weather.yandex.ru/v2/forecast/', params, headers=headers)
    return result.json()


# BOT INIT
bot = telebot.TeleBot(config['token'])


# BOT HANDLERS
@bot.message_handler(commands=['start'])
def start_message(message):
    answer = 'Привет ✌️\nСпроси какая погода в интересующем тебя городе,\nя подскажу 🙃'
    bot.send_message(message.chat.id, answer)


@bot.message_handler(content_types=['voice'])
def voice_message(message):
    try:
        file_id = message.voice.file_id
        file_path = bot.get_file(file_id).file_path
        file_data = bot.download_file(file_path)
        with open('voice_message.ogg', 'wb') as audio_file:
            audio_file.write(file_data)
        text = ''.join(audio_to_text('voice_message.ogg'))
        nlp = spacy.load('ru_core_news_lg')
        doc = nlp(text)
        try:
            coordinates = city_to_coordinates(doc.ents[0])
            if not len(coordinates):
                bot.send_message(message.chat.id, "Город не распознан 😢")
                return
        except IndexError:
            bot.send_message(message.chat.id, "Вы не назвали город")
            return
        answer = coordinates_to_weather(coordinates)
        bot.send_message(
            message.chat.id,
            f"*{answer['geo_object']['locality']['name']}:*\n\n🌡 температура............. {answer['fact']['temp']}℃\n😌 ощущается как......... {answer['fact']['feels_like']}℃\n💨 скорость ветра......... {answer['fact']['wind_speed']} м/c\n\n{answer['info']['url']}",
            parse_mode="Markdown",
        )
    except Exception as e:
        bot.send_message(message.chat.id, "Не удалось распознать речь.\nПопробуйте ещё раз... 👀")


# BOT START
print('Bot ready and listen commands...')
bot.polling()
