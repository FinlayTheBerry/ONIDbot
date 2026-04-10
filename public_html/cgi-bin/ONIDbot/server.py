#!/usr/bin/python

import asyncio

async def handle_client(reader, writer):
    try:
        code = (await reader.read(1024)).decode("utf-8")
        await asyncio.sleep(2.0)
        response = "{ \"success\": true, \"message\": \"You have been verified with <strong>ONIDbot</strong>. You can safely close this window and return to Discord.\" }"
        writer.write(response.encode("utf-8"))
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()
async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 12345)
    print("Serving on 0.0.0.0:12345...")
    async with server:
        await server.serve_forever()
asyncio.run(main())