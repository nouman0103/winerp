# To use this library with new discord.py, you need to modify some code
# This takes in account of the asyncio changes in discord.py
# aka, https://gist.github.com/Rapptz/6706e1c8f23ac27c98cee4dd985c8120

from discord.ext import commands
import winerp
import asyncio

bot = commands.Bot(...)
# create winerp client
client = winerp.Client(...)

@bot.command()
async def request(ctx):
    # Fetching data from a client named "another-bot" using route "get_some_data"
    data = await bot.ipc.request("get_some_data", source = "another-bot")
    await ctx.send(data)


@bot.ipc.route()
async def get_formatted_data(user_id = None):
    return f"<@{user_id}>"


@bot.ipc.event
async def on_winerp_ready():
    print("Winerp Client is ready for connections")

async def main():
    async with bot:
        # start the client
        bot.loop.create_task(client.start())
        await bot.start('token')

asyncio.run(main())
