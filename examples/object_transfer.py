# This example will show you how you can send a discord.User object to the server
# and then use all its attributes and .send() on it.

# In app.py [client which will receive the object]:

@app.route('/object')
async def object():
    user = await client.request('get_user', 'bot', 120)
    print(
        user.id,
        user.name,
        user.discriminator,
        user.avatar
    )
    await user.send(content='Hello from the server!')
    return user


# In main.py [Client which will send the object]:
import winerp

@bot.ipc.route()
async def get_user():
    return winerp.WinerpObject(bot.get_user(...), recursion_level=0, handle_functions=True, functions_list=['send'])

