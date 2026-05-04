#!/bin/python

import json
import os
import requests
import datetime
import time
import discord
import sys
import smtplib
from email.message import EmailMessage
import hmac
import hashlib
import base64
import asyncio
import socket
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Bot authentication url:
# https://discord.com/oauth2/authorize?client_id={CLIENTID}

# region File IO
def IO_RealPath(filePath):
    return os.path.realpath(os.path.expanduser(filePath))
def IO_GetScriptDir():
    return os.path.dirname(IO_RealPath(__file__))
def IO_WriteFile(filePath, contents, binary=False):
    filePath = IO_RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_TRUNC)
    with open(fd, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def IO_AppendFile(filePath, contents, binary=False):
    filePath = IO_RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_APPEND)
    with open(fd, "ab" if binary else "a", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def IO_CreateFile(filePath, contents, mode, binary=False):
    filePath = IO_RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with open(fd, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def IO_ReadFile(filePath, defaultContents=None, binary=False):
    filePath = IO_RealPath(filePath)
    try:
        with open(filePath, "rb" if binary else "r", encoding=None if binary else "utf-8") as f:
            return f.read()
    except FileNotFoundError:
        if defaultContents != None:
            return defaultContents
        else:
            raise
    if defaultContents != None and not os.path.exists(filePath):
        return defaultContents
def IO_SerializeJson(obj, compact=False):
    return json.dumps(obj, separators=(',', ':') if compact else None, indent=None if compact else 4)
def IO_DeserializeJson(jsonString):
    return json.loads(jsonString)
def IO_GetEpoch():
    return time.time()
def IO_FormatEpoch(epoch):
    timestamp = datetime.datetime.fromtimestamp(epoch)
    return timestamp.strftime("%I:%M%p %m/%d").lower()
# endregion

# region Logs
def LOG_Generic(message, log_type, ansi_color):
    formatted_message = f"{log_type} - {IO_FormatEpoch(IO_GetEpoch())} {int(IO_GetEpoch())} - {message}"
    print(f"\033[{ansi_color}m{formatted_message}\033[0m", flush=True)
    log_path = os.path.join(IO_GetScriptDir(), "log.txt")
    if not os.path.exists(log_path):
        IO_CreateFile(log_path, f"{formatted_message}\n", 0o600)
    else:
        IO_AppendFile(log_path, f"{formatted_message}\n")
def LOG_Info(message):
    LOG_Generic(message, "Info", "37")
def LOG_Warning(message):
    LOG_Generic(message, "Warning", "33")
def LOG_Error(message):
    LOG_Generic(message, "ERROR", "31")
def LOG_Exception(ex):
    tb = ex.__traceback__
    while tb is not None:
        if IO_RealPath(tb.tb_frame.f_code.co_filename) == IO_RealPath(__file__):
            message = repr(ex)
            funcname = "<module>" if tb.tb_frame.f_code.co_name == "<module>" else tb.tb_frame.f_code.co_name + "()"
            lineno = tb.tb_lineno
            line = IO_ReadFile(tb.tb_frame.f_code.co_filename).splitlines()[lineno - 1].strip()
            LOG_Generic(f"{message} in {funcname} line {lineno}: {line}", "PY_EX", "31")
            return
        tb = tb.tb_next
    LOG_Generic(f"{repr(ex)} at unknown location", "PY_EX", "31")
def LOG_FormatUser(user):
    return f"User(\"{user.display_name}\", \"{user.name}\", {user.id})"
def LOG_FormatChannel(channel):
    return f"Channel(\"{channel.name}\", {channel.id})"
def LOG_FormatGuild(guild):
    return f"Guild(\"{guild.name}\", {guild.id})"
# endregion

# region Environment
ENV = None
def ENV_Load():
    global ENV
    env_path = os.path.join(IO_GetScriptDir(), "environment.json")
    ENV = IO_DeserializeJson(IO_ReadFile(env_path))
# endregion

# region OSU API
def OSU_LookupOnidName(onid_email):
    response = requests.post("https://api.oregonstate.edu/oauth2/token", data={"grant_type": "client_credentials"}, auth=(ENV['osu_api_id'], ENV['osu_api_secret']))
    response.raise_for_status()
    token = response.json()['access_token']

    headers = { "Authorization": f"Bearer {token}", "Accept": "application/json" }
    response = requests.get(f"https://api.oregonstate.edu/v2/directory?filter[emailAddress]={onid_email}", headers=headers)
    response.raise_for_status()
    data = response.json()['data']

    # Return output or None
    if len(data) == 1:
        output = f"{data[0]['attributes']['firstName']} {data[0]['attributes']['lastName']}"
        LOG_Info(f"OSU API - \"{onid_email}\" - \"{output}\"")
        return output
    elif len(data) == 0:
        onid_username = onid_email.split("@")[0] if "@" in onid_email else onid_email

        # Send second request
        headers = { "Authorization": f"Bearer {token}", "Accept": "application/json" }
        response = requests.get(f"https://api.oregonstate.edu/v2/directory?filter[onid]={onid_username}", headers=headers)
        response.raise_for_status()
        data = response.json()['data']

        if len(data) == 1:
            output = f"{data[0]['attributes']['firstName']} {data[0]['attributes']['lastName']}"
            LOG_Info(f"OSU API - \"{onid_email}\" - \"{output}\"")
            return output
        elif len(data) == 0:
            LOG_Warning(f"OSU API - \"{onid_email}\" - NO DATA")
            return None
        else:
            LOG_Warning(f"OSU API - \"{onid_email}\" - TOO MANY HITS SECOND REQUEST")
            return None
    else:
        LOG_Warning(f"OSU API - \"{onid_email}\" - TOO MANY HITS")
        return None
# endregion

ENV_Load()
result = OSU_LookupOnidName("godsb@oregonstate.edu")