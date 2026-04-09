#!/usr/bin/python

import json
import os
from datetime import datetime, timezone
import time
import sys
import asyncio
import time
import socket
import subprocess

# region File IO
def IO_RealPath(filePath):
    return os.path.realpath(os.path.expanduser(filePath))
def IO_GetScriptDir():
    return os.path.dirname(IO_RealPath(__file__))
def IO_WriteFile(filePath, contents, binary=False):
    filePath = IO_RealPath(filePath)
    with open(filePath, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def IO_ReadFile(filePath, defaultContents=None, binary=False):
    filePath = IO_RealPath(filePath)
    if defaultContents != None and not os.path.exists(filePath):
        return defaultContents
    with open(filePath, "rb" if binary else "r", encoding=None if binary else "utf-8") as f:
        return f.read()
def IO_SerializeJson(obj, compact=False):
    return json.dumps(obj, indent=None if compact else 4)
def IO_DeserializeJson(jsonString):
    return json.loads(jsonString)
def IO_GetEpoch():
    return time.time() + time.localtime().tm_gmtoff
def IO_FormatTime(epoch):
    timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return timestamp.strftime("%I:%M%p %m/%d").lower()
# endregion

# region Launch Time Cluster
PORT = 56812
SSH_KEY_PATH = "~/.ssh/osu_ssh_private"
HOSTNAMES = [ "flip1.engr.oregonstate.edu", "flip2.engr.oregonstate.edu", "flip3.engr.oregonstate.edu", "flip4.engr.oregonstate.edu" ]
INTERVAL = 60

START_TIME = IO_GetEpoch()
SSH_KEY_PATH = IO_RealPath(SSH_KEY_PATH)
SCRIPT_PATH = IO_RealPath(__file__)
for i in range(len(HOSTNAMES)):
    HOSTNAMES[i] = { "name": HOSTNAMES[i], "ip": socket.gethostbyname(HOSTNAMES[i]) }
MY_HOSTNAME = socket.gethostname()
MY_HOSTNAME = { "name": MY_HOSTNAME, "ip": socket.gethostbyname(MY_HOSTNAME) }

IS_PRIMARY = False
DO_RESTART = True
async def StartHost(hostname):
    command = f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i \"{SSH_KEY_PATH}\" \"{hostname['ip']}\" screen -S pycluster -d -m \"{SCRIPT_PATH}\" run"
    ssh_results = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)
    if ssh_results.returncode != 0:
        print(ssh_results.stdout)
        print(command)
        raise Exception(f"Failed to restart host {hostname['name']}")
async def SendCommand(hostname, command):
    reader, writer = await asyncio.wait_for(asyncio.open_connection(hostname["ip"], PORT), timeout=2.0)
    try:
        writer.write(command.encode())
        await writer.drain()
        return 0
    finally:
        writer.close()
        await writer.wait_closed()
async def GetHostState(hostname):
    ping_results = subprocess.run([ "ping", "-c", "1", "-W", "2", hostname["ip"] ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if ping_results.returncode != 0:
        return { "status": "unreachable" }
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(hostname["ip"], PORT), timeout=2.0)
        try:
            writer.write("get_state".encode())
            await writer.drain()
            state = IO_DeserializeJson((await reader.read(256)).decode())
            return state
        finally:
            writer.close()
            await writer.wait_closed()
    except:
        return { "status": "crashed" }
async def HandleRequest(reader, writer):
    global DO_RESTART
    try:
        request = (await reader.read(256)).decode()
        if request == "get_state":
            if IS_PRIMARY:
                writer.write(IO_SerializeJson({ "status": "primary", "birth": START_TIME, "restart": DO_RESTART }, compact=True).encode())
                await writer.drain()
            else:
                writer.write(IO_SerializeJson({ "status": "running", "birth": START_TIME, "restart": DO_RESTART }, compact=True).encode())
                await writer.drain()
        elif request == "stop":
            sys.exit(0)
        elif request == "no_restart":
            DO_RESTART = False
        else:
            raise Exception(f"Invalid request {request}.")
    finally:
        writer.close()
        await writer.wait_closed()
async def Check():
    BLUE = "\033[1;34m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[1;31m"
    RESET = "\033[0m"
    for hostname in HOSTNAMES:
        state = await GetHostState(hostname)
        if state["status"] == "primary":
            print(f"{BLUE}{hostname['name']} is primary and has been running since {IO_FormatTime(state['birth'])} with restarting {'enabled' if state['restart'] else 'disabled'}.{RESET}")
        elif state["status"] == "running":
            print(f"{GREEN}{hostname['name']} is secondary and has been running since {IO_FormatTime(state['birth'])} with restarting {'enabled' if state['restart'] else 'disabled'}.{RESET}")
        elif state["status"] == "unreachable":
            print(f"{YELLOW}{hostname['name']} is unreachable.{RESET}")
        elif state["status"] == "crashed":
            print(f"{RED}{hostname['name']} has crashed!{RESET}")
        else:
            raise Exception(f"Invalid status {state['status']}.")
async def Start():
    for hostname in HOSTNAMES:
        state = await GetHostState(hostname)
        if state["status"] != "primary" and state["status"] != "running":
            print(f"Starting {hostname['name']}...")
            await StartHost(hostname)
            await asyncio.sleep(0.25)
    print("Started all hosts.")
async def Stop():
    print("Disabling automatic restart...")
    for hostname in HOSTNAMES:
        try:
            await SendCommand(hostname, "no_restart")
        except:
            pass
    await asyncio.sleep(1)
    print("Stopping cluster nodes...")
    for hostname in HOSTNAMES:
        try:
            await SendCommand(hostname, "stop")
        except:
            pass
    print("Cluster has been stopped.")
async def Run():
    global IS_PRIMARY
    server = await asyncio.start_server(HandleRequest, "0.0.0.0", PORT)
    async with server:
        print(f"Joined cluster on {MY_HOSTNAME['name']}:{PORT}...")
        while True:
            min_birth = float("inf")
            for hostname in HOSTNAMES:
                if hostname["ip"] == MY_HOSTNAME["ip"]:
                    continue
                state = await GetHostState(hostname)
                if "birth" in state and state["birth"] < min_birth:
                    min_birth = state["birth"]

            if START_TIME < min_birth:
                if not IS_PRIMARY:
                    IS_PRIMARY = True
                    print(f"{MY_HOSTNAME['name']} Taking over as primary...")
                    

            await asyncio.sleep(INTERVAL)
# endregion

# region Main
def Main():
    try:
        if len(sys.argv) == 2 and sys.argv[1] == "start":
            asyncio.run(Start())
        elif len(sys.argv) == 2 and sys.argv[1] == "stop":
            asyncio.run(Stop())
        elif len(sys.argv) == 2 and sys.argv[1] == "check":
            asyncio.run(Check())
        elif len(sys.argv) == 2 and sys.argv[1] == "run":
            asyncio.run(Run())
        else:
            raise Exception("No verb specified. Try \"pycluster start\".")
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(0)
    except SystemExit as ex:
        raise ex
    except BaseException as ex:
        print(str(ex))
        sys.exit(1)
Main()
# endregion
