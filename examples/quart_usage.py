from quart import Quart
import winerp

app = Quart(__name__)

ipc_client = winerp.Client(
    local_name = "client-name",
    port = 6543
)

@app.while_serving
async def func():
    await ipc_client.start()
    yield

@app.route("/ping")
async def ping():
    await ipc_client.inform("Hello", [])
    return "pong"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1234)
