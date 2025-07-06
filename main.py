import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from collections import deque
import google.generativeai as genai
import asyncio
import time
import traceback

from keep_alive import keep_alive

# Load .env values
load_dotenv()
TOKEN = os.getenv('TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not TOKEN or not GOOGLE_API_KEY:
    print("[ERROR] Missing TOKEN or GOOGLE_API_KEY in environment.")
    exit(1)

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Personality for Gemini
TSUNDERE_PERSONALITY = (
    "You are Val, a tsundere AI girl who chats naturally and casually. "
    "You're playful, a little flustered, but kind. Keep replies short and realistic. "
    "Avoid sounding like a script or overly dramatic anime."
)

# History: per-server message context
guild_histories = {}
MAX_HISTORY = 5

# Cooldown: per-user to prevent spam
user_cooldowns = {}
COOLDOWN_SECONDS = 10

# Keep alive web server
keep_alive()

@bot.event
async def on_ready():
    print(f'[✅] Logged in as {bot.user} (ID: {bot.user.id})')
    streaming = discord.Streaming(
        name="Being cute? M-Me? You're dreaming..",
        url="https://www.twitch.tv/val"
    )
    await bot.change_presence(activity=streaming)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()
    if bot.user.mentioned_in(message) or "val" in content_lower:
        now = time.time()
        user_id = message.author.id
        if now - user_cooldowns.get(user_id, 0) < COOLDOWN_SECONDS:
            return
        user_cooldowns[user_id] = now

        guild_id = message.guild.id if message.guild else f"dm_{user_id}"
        if guild_id not in guild_histories:
            guild_histories[guild_id] = deque(maxlen=MAX_HISTORY)

        # Add the user's message to history
        guild_histories[guild_id].append({"author": "user", "content": message.content})

        # Format for Gemini
        messages = [{"author": "system", "content": TSUNDERE_PERSONALITY}]
        messages.extend(guild_histories[guild_id])

        try:
            model = genai.GenerativeModel(model_name="gemini-2.0-flash")
            chat = model.start_chat(history=messages)
            response = chat.send_message(message.content)
            reply = response.text.strip()

            if not reply:
                reply = "Hmph... What do you want now?"

        except Exception as e:
            print("[❌ ERROR] Gemini API failed:")
            traceback.print_exc()
            reply = "Hmph... I'm not answering that right now."

        # Add Val's reply to history
        guild_histories[guild_id].append({"author": "assistant", "content": reply})

        await message.channel.send(reply)

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
