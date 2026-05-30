import telebot
import random
import requests
import os
from telebot import types
from dotenv import load_dotenv

load_dotenv()

#My Bots Unique Token and keys
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
# testing
print(f"BOT_TOKEN loaded: {'Yes' if BOT_TOKEN else 'MISSING'}")
print(f"WEATHER_API_KEY loaded: {'Yes' if WEATHER_API_KEY else 'MISSING'}")
print(f"NEWS_API_KEY loaded: {'Yes' if NEWS_API_KEY else 'MISSING'}")

#create the bot
bot = telebot.TeleBot(BOT_TOKEN)

def build_main_menu():
    # InlineKeyboardMarkup is the container that holds all buttons
    keyboard = types.InlineKeyboardMarkup()

    # callback_data is the label the code receives when clicked
    btn_weather = types.InlineKeyboardButton("Weather", callback_data="weather")
    btn_news = types.InlineKeyboardButton("News", callback_data="news")
    btn_joke = types.InlineKeyboardButton("Random Joke", callback_data="joke")
    btn_about = types.InlineKeyboardButton("About", callback_data="about")
    btn_help = types.InlineKeyboardButton("Help", callback_data="help")

    # .add() places buttons into the keyboard
    keyboard.add(btn_weather, btn_news)
    keyboard.add(btn_joke)
    keyboard.add(btn_about, btn_help)

    return keyboard

# This is to help users return to the menu
def build_back_button():
    keyboard = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("Back to Menu", callback_data="main_menu")
    keyboard.add(btn_back)
    return keyboard

# Weather city selection keyboard
def build_weather_cities():
    keyboard = types.InlineKeyboardMarkup()
    cities = [
        ("Lagos", "weather_Lagos"),
        ("Abuja", "weather_Abuja"),
        ("Jos", "weather_Jos"),
        ("London", "weather_London"),
        ("New York", "weather_New York"),
        ("Dubai", "weather_Dubai"),
    ]
    row = []
    for city_name, callback in cities:
        btn = types.InlineKeyboardButton(city_name, callback_data=callback)
        row.append(btn)
        if len(row) == 2:
            keyboard.add(*row)
            row = []
    if row:                        #if there is a left over button, add it
        keyboard.add(*row)
    
    # Back button at the button
    keyboard.add(types.InlineKeyboardButton("Back to Menu", callback_data="main_menu"))
    return keyboard

# News category selection keyboard
def build_news_categories():
    keyboard = types.InlineKeyboardMarkup()
    categories = [
        ("Business", "news_business"),
        ("Technology", "news_technology"),
        ("Sports", "news_sports"),
        ("Health", "news_health"),
        ("Entertainment", "news_entertainment"),
        ("General", "news_general"),
    ]
    row = []
    for cat_name, callback in categories:
        btn = types.InlineKeyboardButton(cat_name, callback_data=callback)
        row.append(btn)
        if len(row) == 2:
            keyboard.add(*row)
            row = []
        if row:
            keyboard.add(*row)
        keyboard.add(types.InlineKeyboardButton("Back to Menu", callback_data="main_menu"))
        return keyboard

# Fetch real weather from OpenWeatherMap API
def get_weather(city):
    try:
        #This is the url i send my request to
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data =  response.json()

        # To check if API returned an error( city not found, etc.)
        if data.get("cod") != 200:
            return f" Weather Error: {data.get('message', 'Unknown error')}\nCode: {data.get('cod')}"

        city_name = data["name"]
        country = data["sys"]["country"]
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"].title() #e.g. Partly cloudy
        wind_speed = data["wind"]["speed"]

        return (
            f" *Weather in {city_name}, {country}*\n\n"
            f" Temperature: *{temp} Celsius*\n"
            f" Feels like: {feels_like} Celsius*\n"
            f" Condition: {description}\n"
            f" Humidity: {humidity}%\n"
            f" Wind Speed: {wind_speed} m/s"
        )
    except Exception as e:
        return f" Weather fetch failed: {str(e)}"

#Fetch real News from News API
def get_news(category="general"):
    try:
        url = (
            f"https://newsapi.org/v2/top-headlines?"
            f"category={category}&"
            f"language=en&"
            f"pageSize=5&"    #Get 5 articles
            f"apiKey={NEWS_API_KEY}"
        )
        response = requests.get(url)
        data = response.json()

        # Response if the request was not successful
        if data.get("status") != "ok":
            return f" News Error: {data.get('message', 'Unknown error')}\n Code: {data.get('code')}"
          
        articles = data.get("articles", [])
        if not articles:
            return "No news articles found for this category right now."

        #Build the news message
        message = f" *Top {category.title()} Headlines*\n\n"

        for i, article in enumerate(articles, start=1):
            title = article.get("title", "No title")
            source = article.get("source", {}).get("name", "Unknown Source")
            # Clean up titles that have source appended at the end
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
        
            message += f"*{i}.* {title}\n"
            message += f"   _{source}_\n\n"
    
        message += " _Updated just now_"
        return message
    except Exception as e:
        return f"News fetch failed: {str(e)}"

# When someone sends /start, run the function below
@bot.message_handler(commands=["start"])
def send_welcome(message):
    # message.chat.id tells us who sent the message
    # message.from_user.first_name gets the user's first name
    name = message.from_user.first_name
    welcome_text = (
        f"Hello {name}! Welcome!\n\n"
        "I can fetch *real-time* weather and news for you!\n\n"
        "Please choose an option from the main menu below"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=build_main_menu())

# /menu command - lets user bring the menu back anytime
@bot.message_handler(commands=["menu"])
def show_menu(message):
    bot.send_message(message.chat.id, "*Main Menu*", parse_mode="Markdown", reply_markup=build_main_menu())

# This Callback function runs everytime ANY button is clicked
@bot.callback_query_handler(func=lambda call:True)
def handle_button_click(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    #call.data contains the callback data of the button that was clicked
        # Main Menu - go back to the main menu
    if call.data == "main_menu":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=" *Main Menu*",
            parse_mode="Markdown",
            reply_markup=build_main_menu()
        )
    #Weather Menu - shows city selection
    elif call.data == "weather_menu":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=" *Select a city for the weather forecast:*",
            parse_mode="Markdown",
            reply_markup=build_weather_cities()
        )
    #Weather City- gets all the cities
    elif call.data.startswith("weather_") and call.data != "weather_menu":
        # Eg. Split Weather_Lagos to "weather" "Lagos" and pick the second as city name
        city = call.data.split("_", 1)[1]
        # Show a loading message while data is fetched
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f" Fetching weather for *{city}* ...",
            parse_mode="Markdown"
        )
        #call weather function to get real data
        weather_text = get_weather(city)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=weather_text,
            parse_mode="Markdown",
            reply_markup=build_back_button()
        )

    #News Menu - shows category selection
    elif call.data == "news_menu":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=" *Select a news category:*",
            parse_mode="Markdown",
            reply_markup=build_news_categories()
        )
    
    #News Category - callback_data looks like "news_technology"
    elif call.data.startswith("news_"):
        category = call.data.split("_", 1)[1]
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f" Fetching *{category.title()}* news...",
            parse_mode="Markdown"
        )
        #call news function to get real data
        news_text = get_news(category)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=news_text,
            parse_mode="Markdown",
            reply_markup=build_back_button()
        )

    # Random Joke
    elif call.data == "joke":
        import random
        jokes = [
            "Why do programmers prefer dark mode?\n Because light attracts bugs!\n",
            "Why did the programmer quit his job?\n Because he didnt get arrays!\n",
            "How do you comfort a JavaScript developer?\n Null it be okay!\n",
            "Why was the python developer always calm?\n Becasue nothing ever got him hissed! ",
            "Why do Java developers wear glasses?\n Because they dont C#!",
        ]
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f" *Random Joke*\n\n{random.choice(jokes)}",
            parse_mode="Markdown",
            reply_markup=build_back_button()
        )
    # ABOUT
    elif call.data == "about":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                " *About This Bot*\n\n"
                "Built by me, your favorite python programmer :)\n\n"
                " *Tech Stack:*\n"
                ". Python 3\n"
                ". pyTelegramBotAPI\n"
                ". OpenWeatherMap API\n"
                ". NewsAPI\n\n"
            ),
            parse_mode="Markdown",
            reply_markup=build_back_button()
        )
    # HELP    
    elif call.data == "help":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                " *Help*\n\n"
                "Use the menu buttons to navigate.\n\n"
                "*Commands:*\n"
                "/start - Welcome Message\n"
                "/menu - Open Main Menu\n\n"
                "*Features:*\n"
                " Weather - Live forecast for 6 cities\n"
                " News - Top headlines in 6 categories\n"
                "Jokes - Random developer jokes"
            ),
            parse_mode="Markdown",
            reply_markup=build_back_button()
        )
    
    # "answer" the call back so telegram removes the "loading" spinner
    bot.answer_callback_query(call.id)
    

# This handles any regular text message (not a command)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "Please use the menu buttons to navigate!\n\n Type /menu to open it."),

#This line starts the bot and keeps it running
print("Bot is running with inline keyboards!... Press CTRL+C to stop.")
bot.infinity_polling()