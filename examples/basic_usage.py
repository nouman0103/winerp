import winerp
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
client = winerp.Client(local_name = "some-random-bot", port=8080)

@bot.command()
async def request(ctx):
    # Fetching data from a client named "another-bot" using route "get_some_data"
    data = await bot.ipc.request("get_some_data", source = "another-bot")
    await ctx.send(data)


@client.route()
async def get_formatted_data(user_id = None):
    return f"<@{user_id}>"


@client.event
async def on_winerp_ready():
    print("Winerp Client is ready for connections")

# This can be different for different libraries
# If you are using newer version of discord.py
# refer to examples/discordpy_usage.py for usage
# in our github repository: https://github.com/BlackThunder01001/winerp
bot.loop.create_task(client.start())
bot.run("TOKEN")
