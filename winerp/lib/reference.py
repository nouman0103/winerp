class ClientReference:
    def __init__(self, tag, ipc):
        self.tag = tag
        self.ipc = ipc
    
    async def call(self, endpoint, timeout = 60, **kwargs):
        return await self.ipc.call(endpoint, self.tag, timeout, **kwargs)
    
    async def ping(self):
        return await self.ipc.ping(self.tag)
    