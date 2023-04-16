# winerp
An IPC based on Websockets. Fast, Stable, and easy-to-use, for inter-communication between your processes or discord.py bots.

Documentation: https://winerp.readthedocs.io/  
Discord Server: https://discord.gg/T28F8hju9Y

### Key Features
 - **Fast** with minimum recorded response time being `< 2ms`
 - Lightweight, Stable and Easy to integrate.
 - No limitation on number of connected clients. 

## Installation
Stable:
```py
pip install -U winerp
```
Main branch (can be unstable/buggy):
```py
pip install git+https://www.github.com/BlackThunder01001/winerp
```

### Working:
This library uses a central server for communication between multiple clients. You can connect a large number of clients for sharing data, and data can be shared between any connected client.

![winerp-server-working](https://user-images.githubusercontent.com/40216575/232253783-7f5b625e-a08d-4e3d-8306-50684ea396b6.png)


1) Import the library:
```py
import winerp
```

2) Initialize winerp client:
```py
ipc = winerp.Client(tag = "my-cool-app", port=8080)
```

3) Start the ipc:
```py
await ipc.start()
# or
asyncio.create_task(ipc.start())
```

- Registering endpoints:
```py
@ipc.endpoint
async def route_name(caller, user_name):
    return f"Hello {user_name}"
```

- Calling an endpoint from another client:
```py
user_name = await ipc.call(endpoint="fetch_user_name", from_client="another-cool-bot", user_id = 123)
```

- Or:
```
another_cool_bot = ipc.get_client(tag = "another-cool-bot") //reusable object
...
user_name = await another_cool_bot.call(endpoint="fetch_user_name", user_id = 123)
```

- Sending *information* type data to other clients:
```py
data = [1, 2, 3, 4]
await ipc.broadcast(data, destinations=["another-cool-bot"])
```

## Example Usage:

Start the server on terminal using `$ winerp --port 8080`. You can also start the server using `winerp.Server`
