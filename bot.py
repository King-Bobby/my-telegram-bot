import telebot
import random
import requests
import os
import feedparser
from telebot import types, apihelper
from dotenv import load_dotenv
from database import setup_database, save_group, get_group_info, save_mention, count_message, get_message_count

apihelper.ENABLE_MIDDLEWARE = True

load_dotenv()

#My Bots Unique Token and keys 
BOT_TOKEN = os.getenv("BOT_TOKEN")

print(f"BOT_TOKEN loaded: {'Yes' if BOT_TOKEN else 'MISSING'}")

#create the bot
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
setup_database()

@bot.middleware_handler(update_types=["message"])
def count_all_messages(bot_instance, message):
    if not message.chat:
        return
    
    is_group = message.chat.type in ["group", "supergroup"]
    chat_type = "group" if is_group else "private"
    chat_name = message.chat.title if is_group else message.from_user.first_name

    count_message(message.chat.id, chat_type, chat_name)

def build_main_menu():
    # InlineKeyboardMarkup is the container that holds all buttons
    keyboard = types.InlineKeyboardMarkup()

    # callback_data is the label the code receives when clicked
    btn_weather = types.InlineKeyboardButton("Weather", callback_data="weather_menu")
    btn_news = types.InlineKeyboardButton("News", callback_data="news_menu")
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

#Coordinates for each city in our menu
CITY_COORDINATES = {
    "Lagos": {"lat": 6.5244, "lon": 3.3792, "country": "Nigeria"},
    "Abuja": {"lat": 9.0765, "lon": 7.3986, "country": "Nigeria"},
    "Jos": {"lat": 9.8965, "lon": 8.8583, "country": "Nigeria"},
    "London": {"lat": 51.5074, "lon": -0.1278, "country": "United Kingdom"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "country": "United States"},
    "Dubai": {"lat": 25.2048, "lon": 55.2708, "country": "United Arab Emirates"},
}

# Fetch real weather from OpenWeatherMap API
def get_weather(city):
    print(f"DE")
    try:
        #Get coordinates for the requested city
        coords = CITY_COORDINATES.get(city)
        if not coords:
            return f"X City '{city}' not found in our list."
        
        lat = coords["lat"]
        lon = coords["lon"]
        country = coords["country"]

        #Build the Open-Meteo API Url
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current_weather=true"
            f"&hourly=relative_humidity_2m,apparent_temperature,precipitation_probability"
            f"&timezone=auto"
            f"&forecast_days=1"
        )
        response = requests.get(url, timeout=10)
        data = response.json()

        #Extract current weather values 
        current = data["current_weather"]
        temp = current["temperature"]
        wind_speed = current["windspeed"]
        weather_code = current["weathercode"]

        #Get the first hourly valuesfor humidity and feels-like
        # Open-Meteo returns hourly arrays - index[0] is the current hour
        humidity = data["hourly"]["relative_humidity_2m"][0]
        feels_like = data["hourly"]["apparent_temperature"][0]
        rain_chance = data["hourly"]["precipitation_probability"][0]

        #WMO Weather code tells us the condition
        def decode_weather(code):
            if code == 0:                    return "Clear Sky"
            elif code in [1, 2]:             return "Partly Cloudy"
            elif code == 3:                  return "Overcast"
            elif code in [45, 48]:           return "Foggy"
            elif code in [51, 53, 55]:       return "Drizzle"
            elif code in [61, 63, 65]:       return "Rainy"
            elif code in [71, 73, 75]:       return "Snowy"
            elif code in [80, 81, 82]:       return "Rain Showers"
            elif code in [95, 96, 99]:       return "Thunderstorm"
            else:                            return "Unknown"
        description = decode_weather(weather_code)

        return (
            f" Weather in {city}, {country}\n\n"
            f" Temperature: {temp} Celsius\n"
            f" Feels like: {feels_like} Celsius\n"
            f" Condition: {description}\n"
            f" Humidity: {humidity}%\n"
            f" Wind Speed: {wind_speed} km/h\n"
            f" Rain Chance: {rain_chance}%"
        )
    except Exception as e:
        return f" Weather error: {str(e)}"

NEWS_FEEDS = {
    "general": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "sports": "https://feeds.bbci.co.uk/sport/rss.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "health": "https://feeds.bbci.co.uk/news/health/rss.xml",
    "entertainment": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
}
#Fetch real News using RSS Feeds
def get_news(category="general"):
    try:
        feed_url =  NEWS_FEEDS.get(category, NEWS_FEEDS["general"])
        # feed parser reads and parses the RSS feed
        feed = feedparser.parse(feed_url)
        
        #Check if any articles were sent back
        if not feed.entries:
            return f"No articles found right now. Please try again later."
        
        #Get source name from the feed itself
        source = feed.feed.get("title", "News Feed")
        message = f" *Top {category.title()} Headlines*\n"
        message += f" Source: {source}\n\n"

        #Show only first five articles
        for i, entry in enumerate(feed.entries[:5], start=1):
            title = entry.get("title", "No title")
            #Clean up the title by removing anything after "-"
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
            message += f"*{i}.* {title}\n\n"
        message += "_Updated just now_"
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

# /admin command
@bot.message_handler(commands=["admin"])
def show_admin(message):
    #This command only makes sense in a group
    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "This command only works inside a group.")
        return
    group_info = get_group_info(message.chat.id)

    if not group_info:
        bot.reply_to(message, "No admin information saved for this group yet.\n\n This happens if the bot was added befor the database was set up.")
        return
    
    bot.reply_to(
        message,
        f"*Group Info*\n\n"
        f"*Group Name:* {group_info['group_name']}\n\n"
        f"*Bot Added By:*\n"
        f"Name: {group_info['added_by_name']}\n"
        f"Username: @{group_info['added_by_username']}\n\n"
        f"*Date Added:* {group_info['date_added']}",
        parse_mode="Markdown"
    )

# /totalmsg command
@bot.message_handler(commands=["totalmsg"])
def show_total_messages(message):
    total =  get_message_count(message.chat.id)
    # Fomat number with commas for example 1250 becomes 1,250
    formatted = f"{total:,}"

    if message.chat.type in ["group", "supergroup"]:
        bot.reply_to(message, f"*Total Messages in this Group:* {formatted}", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"*Your Total Messages:* {formatted}", parse_mode="Markdown"
        )

# This Callback function runs everytime ANY button is clicked
@bot.callback_query_handler(func=lambda call:True)
def handle_button_click(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    #call.data contains the callback data of the button that was clicked
    # Main Menu - go back to the main menu
    if call.data == "main_menu":
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=" *Main Menu*", parse_mode="Markdown",
            reply_markup=build_main_menu()
        )
    #Weather Menu - shows city selection
    elif call.data == "weather_menu":
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=" *Select a city for the weather forecast:*",
            parse_mode="Markdown", reply_markup=build_weather_cities()
        )
    #Weather City- gets all the cities
    elif call.data.startswith("weather_") and call.data != "weather_menu":
        # Eg. Split Weather_Lagos to "weather" "Lagos" and pick the second as city name
        city = call.data.split("_", 1)[1]
        # Show a loading message while data is fetched
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f" Fetching weather for {city} ...",
            parse_mode="Markdown"
        )
        #call weather function to get real data
        weather_text = get_weather(city)
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=weather_text, reply_markup=build_back_button()
        )

    #News Menu - shows category selection
    elif call.data == "news_menu":
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=" *Select a news category:*",
            parse_mode="Markdown", reply_markup=build_news_categories()
        )
    
    #News Category - callback_data looks like "news_technology"
    elif call.data.startswith("news_"):
        category = call.data.split("_", 1)[1]
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f" Fetching *{category.title()}* news...",
            parse_mode="Markdown"
        )
        #call news function to get real data
        news_text = get_news(category)
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=news_text, parse_mode="Markdown",
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
            chat_id=chat_id, message_id=message_id,
            text=f" *Random Joke*\n\n{random.choice(jokes)}",
            parse_mode="Markdown", reply_markup=build_back_button()
        )
    # ABOUT
    elif call.data == "about":
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=(
                " *About This Bot*\n\n"
                "Built by me, your favorite python programmer :)\n\n"
                " *Tech Stack:*\n"
                "- Python 3\n"
                "- pyTelegramBotAPI\n"
                "- Open-Meteo API\n"
                "- BBC & NYTimes RSS Feeds\n\n"
            ),
            parse_mode="Markdown", reply_markup=build_back_button()
        )
    # HELP    
    elif call.data == "help":
        bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
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
            parse_mode="Markdown", reply_markup=build_back_button()
        )
    
    # "answer" the call back so telegram removes the "loading" spinner
    bot.answer_callback_query(call.id)
    
#Bot welcomes itself when added to a group
@bot.my_chat_member_handler()
def bot_added_to_group(update):
    # member or administrator meansthe bot was just added
    if update.new_chat_member.status in ["member", "administrator"]:
        chat_id = update.chat.id
        group_name = update.chat.title
        added_by = update.from_user
        full_name = f"{added_by.first_name} {added_by.last_name or ''}". strip()

        #save group info to database
        save_group(
            group_id            = chat_id,
            group_name          = group_name,
            added_by_id         = added_by.id,
            added_by_username   = added_by.username or "No username",
            added_by_name       = full_name    
        )

        bot.send_message(
            chat_id,
            f"Hello everyone! I am glad here and ready to help!\n\n"
            f"I am glad to be part of *{group_name}*.\n\n"
            f"Type /menu to see what i can do.",
            parse_mode="Markdown"
        )

#Bot Welcomes New Members into the group
@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    # Message.new_chat_members is a List incase multiple members join at once
    for new_member in message.new_chat_members:
        if new_member.id == bot.get_me().id:
            continue
        first_name = new_member.first_name
        bot.send_message(
            message.chat.id,
            f"Welcome to the group, *{first_name}*! Glad to have you here.",
            parse_mode="Markdown"
        )
#Bot says goodbye to members leaving the group
@bot.message_handler(content_types=["left_chat_member"])
def goodbye_member(message):
    first_name = message.left_chat_member.first_name
    bot.send_message(
        message.chat.id,
        f"Goodbye {first_name}, we will miss you!"
    )

# This handles any regular text message (not a command)
@bot.message_handler(func=lambda message: message.text and 
                    ("@" + bot.get_me().username).lower() in message.text.lower())
def handle_text(message):
    # Check if this a group or private chat
    is_group = message.chat.type in ["group", "supergroup"]
    group_id = message.chat.id if is_group else None
    group_name = message.chat.title if is_group else None
    #Save the mention to the database
    save_mention(
        message_id      = message.message_id,
        message_text    = message.text,
        user_id         = message.from_user.id,
        username        = message.from_user.username or "No username",
        first_name      = message.from_user.first_name,
        group_id        = group_id,
        group_name      = group_name
    )
    bot.reply_to(
        message, 
        f"Hello {message.from_user.first_name}! How can I help you?\n\n Type /menu to see what I can do."
    )

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "Please use the menu buttons to navigate!\n\n Type /menu to open it.")

#This line starts the bot and keeps it running
print("Bot is running with inline keyboards!... Press CTRL+C to stop.")
bot.infinity_polling()