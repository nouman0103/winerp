# winerp
An IPC based on Websockets. Fast, Stable, and Reliable, perfect for communication between your processes or discord.py bots.

## Installation
Stable:
```py
pip install winerp
```
Main branch (can be unstable/buggy):
```py
pip install git+https://www.github.com/BlackThunder01001/winerp
```

## Working:
This library uses a central server for communication between multiple processes. You can connect a large number of clients for sharing data, and data can be shared between any connected client.


## Example Usage:

### Server Side:
```py
import winerp

server = winerp.Server(port=8080)
server.start()
```

### Client 1 (`some-random-bot`):
```py

import discord
from discord.ext.commands import Bot

import winerp

bot = Bot(command_prefix="!", intents=discord.Intents.all())

bot.ipc = winerp.Client(local_name = "some-random-bot", loop = bot.loop, port=8080)

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

bot.loop.create_task(bot.ipc.start())
bot.run("TOKEN")
```

### Client 2 (`another-bot`)
```py
import discord
from discord.ext.commands import Bot

import winerp

bot = Bot(command_prefix="?", intents=discord.Intents.all())

bot.ipc = winerp.Client(local_name = "another-bot", loop = bot.loop, port=8080)

@bot.command()
async def format(ctx):
    # Fetching data from a client named "some-random-bot" using route "get_formatted_data"
    data = await bot.ipc.request("get_formatted_data", source = "some-random-bot", user_id = ctx.author.id)
    await ctx.send(data)


@bot.ipc.route()
async def get_some_data():
    return "You are very cool"


bot.loop.create_task(bot.ipc.start())
bot.run("TOKEN")
```

# Features

 - Fast: Minimum Response Time Recorded: `0.001s`.
 - Reliable, Stable and Easy to integrate.
 - A single hosted server can be used to serve all clients on the machine.
 - No limitation on number of connected clients.
 - Inter bot-communication possible.
 - Inter server-communication possible.

