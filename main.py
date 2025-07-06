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

# Load .env
load_dotenv()
TOKEN = os.getenv('TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not TOKEN or not GOOGLE_API_KEY:
    print("[ERROR] Missing TOKEN or GOOGLE_API_KEY.")
    exit(1)

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Val's tsundere personality
TSUNDERE_PERSONALITY = (
    "You are Val, a tsundere AI girl who chats like a real person. "
    "You're playful, flustered, but caring deep down. Keep replies short and casual. "
    "Avoid sounding robotic or overly dramatic."
)

# Per-server memory
guild_histories = {}
MAX_HISTORY = 5

# Cooldown
user_cooldowns = {}
COOLDOWN_SECONDS = 10

# Flask server to stay alive
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

        # Store message
        guild_histories[guild_id].append({"author": "user", "content": message.content})

        # Format history correctly for Gemini
        messages = [{"role": "user", "parts": [TSUNDERE_PERSONALITY]}]

        for entry in guild_histories[guild_id]:
            role = "user" if entry["author"] == "user" else "model"
            messages.append({"role": role, "parts": [entry["content"]]})

        try:
            model = genai.GenerativeModel(model_name="gemini-2.0-flash")
            response = model.generate_content(messages)
            reply = response.text.strip()

            if not reply:
                reply = "Hmph... What do you want now?"
        except Exception as e:
            print("[❌ Gemini API ERROR]")
            traceback.print_exc()
            reply = "Hmph... I'm not answering that right now."

        # Save Val's reply
        guild_histories[guild_id].append({"author": "assistant", "content": reply})

        await message.channel.send(reply)

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
