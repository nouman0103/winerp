# This requires you to init the ipc client in your bot
# in the following manner:

import winerp
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
bot.ipc = winerp.Client(...)

# inside your main.py

# After that, you can do the following
# in your cog.py:

from discord.ext import commands

class MyCog(commands.Cog):
    def __init__(self, bot, ...):
        self.bot = bot
        ...

    # New async cog_load special method is automatically called
    async def cog_load(self):
        bot = self.bot

        @bot.ipc_client.route()
        async def cog_route():
            return 'Hi, I am from a cog!'

async def setup(bot):
    await bot.add_cog(MyCog(bot))