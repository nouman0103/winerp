.. winerp documentation master file, created by
   sphinx-quickstart on Wed Apr 13 21:56:45 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to winerp
==================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Introduction
~~~~~~~~~~~~
An IPC based on Websockets. Fast, Stable, and Reliable, perfect for communication between your processes or discord.py bots.

Installation
~~~~~~~~~~~~

Stable:: 
   
   $ py pip install winerp

Main branch (can be unstable/buggy)::

   pip install git+https://www.github.com/BlackThunder01001/winerp

Working
~~~~~~~~
This library uses a central server for communication between multiple processes.
You can connect a large number of clients for sharing data, and data can be shared between any connected client.

1) Import the library:

   .. code-block:: python3
      
      import winerp

2) Initialize winerp client:

.. code-block:: python3
   
   ipc_client = winerp.Client(local_name = "my-cool-app", port=8080)

3) Start the client:

.. code-block:: python3
   
   await ipc_client.start()
   # or asyncio.create_task(ipc_client.start())
   # This can be different for different libraries
   # If you are using newer version of discord.py
   # refer to examples/discordpy_usage.py for usage
   # in our github repository: https://github.com/BlackThunder01001/winerp

- Registering routes:

.. code-block:: python3

   @ipc_client.route
   async def route_name(name):
      return f"Hello {name}"


- Requesting data from another client:

.. code-block:: python3

   user_name = await ipc_client.request(route="fetch_user_name", source="another-cool-bot", user_id = 123)

- Sending *information* type data to other clients:

.. code-block:: python3

   data = [1, 2, 3, 4]
   await ipc_client.inform(data, destinations=["another-cool-bot"])


Example Usage
~~~~~~~~~~~~~~

Server Side:

.. code-block:: python3

   import winerp
   server = winerp.Server(port=8080)
   server.start()


Client 1 (`some-random-bot`):

.. code-block:: python3

   import discord
   from discord.ext.commands import Bot

   import winerp

   bot = Bot(command_prefix="!", intents=discord.Intents.all())

   bot.ipc = winerp.Client(local_name = "some-random-bot", port=8080)

   @bot.command()
   async def request(ctx):
      # Fetching data from a client named "another-bot"
      # using route "get_some_data"
      data = await bot.ipc.request(
         "get_some_data",
         source = "another-bot"
      )
      await ctx.send(data)


   @bot.ipc.route()
   async def get_formatted_data(user_id = None):
      return f"<@{user_id}>"


   @bot.ipc.event
   async def on_winerp_ready():
      print("Winerp Client is ready for connections")

   # This can be different for different libraries
   # If you are using newer version of discord.py
   # refer to examples/discordpy_usage.py for usage
   # in our github repository: https://github.com/BlackThunder01001/winerp
   bot.loop.create_task(bot.ipc.start())
   bot.run("TOKEN")

Client 2 (`another-bot`)

.. code-block:: python3

   import discord
   from discord.ext.commands import Bot

   import winerp

   bot = Bot(command_prefix="?", intents=discord.Intents.all())

   bot.ipc = winerp.Client(local_name = "another-bot", port=8080)

   @bot.command()
   async def format(ctx):
      # Fetching data from a client named "some-random-bot"
      # using route "get_formatted_data"
      data = await bot.ipc.request(
         "get_formatted_data",
         source = "some-random-bot",
         user_id = ctx.author.id
      )
      await ctx.send(data)


   @bot.ipc.route()
   async def get_some_data():
      return "You are very cool"

   # This can be different for different libraries
   # If you are using newer version of discord.py
   # refer to examples/discordpy_usage.py for usage
   # in our github repository: https://github.com/BlackThunder01001/winerp
   bot.loop.create_task(bot.ipc.start())
   bot.run("TOKEN")


Features
~~~~~~~~

 - Fast: Minimum Response Time Recorded: **< 2ms**.
 - Reliable, Stable and Easy to integrate.
 - A single hosted server can be used to serve all clients on the machine.
 - No limitation on number of connected clients.
 - Inter bot-communication possible.
 - Inter server-communication possible.


API Reference
~~~~~~~~~~~~~

Refer to this to know more about the API.

.. toctree::
  :maxdepth: 1

  api


Help and Support
~~~~~~~~~~~~~~~~

   - Join our `Discord <https://discord.gg/SpMGPkjwyT>` server for support.
   - Report bugs and feature requests at `GitHub <https://www.github.com/BlackThunder01001/winerp>`
