import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from collections import deque
import google.generativeai as genai

from keep_alive import keep_alive

load_dotenv()

TOKEN = os.getenv('TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

TSUNDERE_PERSONALITY = (
    "You are Val, a tsundere AI girl who talks casually and naturally. "
    "You are playful, slightly flustered but friendly. "
    "Your responses are short, engaging, and feel like a real person chatting. "
    "Avoid being overly scripted or repetitive."
)

# Memory: last 5 messages per guild for context
guild_histories = {}
MAX_HISTORY = 5

keep_alive()  # start Flask webserver for uptime monitoring

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    streaming_activity = discord.Streaming(
        name="Being cute? M-Me? You're dreaming..",
        url="https://www.twitch.tv/val"
    )
    await bot.change_presence(activity=streaming_activity)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    if bot.user.mentioned_in(message) or "val" in content_lower:
        guild_id = message.guild.id if message.guild else f"dm_{message.author.id}"

        if guild_id not in guild_histories:
            guild_histories[guild_id] = deque(maxlen=MAX_HISTORY)

        # Add user message to history
        guild_histories[guild_id].append({"author": "user", "content": message.content})

        # Build prompt for Gemini API
        messages = [{"author": "system", "content": TSUNDERE_PERSONALITY}]
        messages.extend(guild_histories[guild_id])
        messages.append({"author": "user", "content": message.content})

        try:
            response = genai.chat.create(
                model="gemini-2.0-flash",
                messages=messages,
                temperature=0.7,
                max_tokens=150,
            )
            reply = response.choices[0].message.content.strip()
            if not reply:
                reply = "Hmph... What do you want now?"
        except Exception as e:
            print(f"Gemini API error: {e}")
            reply = "Hmph... I'm not answering that right now."

        # Add Val's reply to history
        guild_histories[guild_id].append({"author": "assistant", "content": reply})

        await message.channel.send(reply)

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
