#!/usr/bin/python

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
    fd = os.open(filePath, os.O_WRONLY)
    with open(fd, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def IO_AppendFile(filePath, contents, binary=False):
    filePath = IO_RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_APPEND)
    with open(fd, "ab" if binary else "a", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def CreateFile(filePath, contents, mode=0o600, binary=False):
    filePath = IO_RealPath(filePath)
    fd = os.open(filePath, os.O_WRONLY | os.O_CREAT, mode)
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
    padding = " " * (8 - len(log_type)) if len(log_type) < 8 else ""
    formatted_message = f"{log_type}{padding}({IO_FormatEpoch(IO_GetEpoch())} {int(IO_GetEpoch())}): {message}"
    print(f"\033[{ansi_color}m{formatted_message}\033[0m", flush=True)
    log_path = os.path.join(IO_GetScriptDir(), "log.txt")
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
# endregion

# region Environment
ENV = None
def ENV_Load():
    global ENV
    env_path = os.path.join(IO_GetScriptDir(), "environment.json")
    if os.stat(env_path).st_mode != 33152:
        raise Exception("Insecure permissions on environment.json. Try chmod 600 environment.json")
    ENV = IO_DeserializeJson(IO_ReadFile(env_path))
# endregion

# region Database
DB = None
def DB_Load():
    global DB
    db_path = os.path.join(IO_GetScriptDir(), "database.json")
    if os.stat(db_path).st_mode != 33152:
        raise Exception("Insecure permissions on database.json. Try chmod 600 database.json")
    DB = IO_DeserializeJson(IO_ReadFile(db_path))
    DB = { int(key): value for key, value in DB.items() }
def DB_Backup():
    db_path = os.path.join(IO_GetScriptDir(), "database.json")
    backup_file_name = f"backups/{int(IO_GetEpoch())}.json"
    backup_path = os.path.join(IO_GetScriptDir(), backup_file_name)
    if os.stat(db_path).st_mode != 33152:
        raise Exception("Insecure permissions on database.json. Try chmod 600 database.json")
    IO_WriteFile(backup_path, IO_ReadFile(db_path))
    LOG_Info(f"Backup: database.json -> {backup_file_name}")
def DB_Save():
    db_path = os.path.join(IO_GetScriptDir(), "database.json")
    IO_WriteFile(db_path, IO_SerializeJson(DB))
    backups_dir_path = os.path.join(IO_GetScriptDir(), "backups")
    latest_backup_time = 0
    for backup_path in os.listdir(backups_dir_path):
        if not os.path.isfile(os.path.join(backups_dir_path, backup_path)):
            raise Exception(f"{backup_path} is not a file.")
        backup_time = int(os.path.splitext(backup_path)[0])
        if backup_time > latest_backup_time:
            latest_backup_time = backup_time
    if int(IO_GetEpoch()) - latest_backup_time > 24 * 60 * 60:
        DB_Backup()
# endregion

# region OSU API
def OSU_LookupOnidName(onid_email):
    # Get a token
    response = requests.post("https://api.oregonstate.edu/oauth2/token", data={"grant_type": "client_credentials"}, auth=(ENV['osu_api_id'], ENV['osu_api_secret']))
    response.raise_for_status()
    token = response.json()['access_token']

    # Send a request
    headers = { "Authorization": f"Bearer {token}", "Accept": "application/json" }
    response = requests.get(f"https://api.oregonstate.edu/v2/directory?filter[emailAddress]={onid_email}", headers=headers)
    response.raise_for_status()
    data = response.json()['data']

    # Return output or None
    if len(data) == 1:
        output = f"{data[0]['attributes']['firstName']} {data[0]['attributes']['lastName']}"
        LOG_Info(f"OSU Directory: \"{onid_email}\" -> \"{output}\".")
        return output
    else:
        LOG_Warning(f"OSU Directory: \"{onid_email}\" -> NO DATA.")
        return None
# endregion

# region COE SMTP
def SMTP_SendEmail(to, subject, body, body_html):
    SMTP_SERVER = "mail.engr.oregonstate.edu"
    SMTP_PORT = 465

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"{ENV['email_username']}@oregonstate.edu"
    msg['To'] = to
    msg.set_content(body)
    msg.add_alternative(body_html, subtype="html")

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp_server:
        smtp_server.login(ENV['email_username'], ENV['email_password'])
        smtp_server.send_message(msg)

    LOG_Info(f"Email: \"{subject}\" to \"{to}\".")
# endregion

# region Tokens And Crypto
def TOKEN_SerializeAndSign(data):
    data["timestamp"] = int(IO_GetEpoch())
    payload = IO_SerializeJson(data, compact=True).encode("utf-8")
    del data["timestamp"]
    nonce = secrets.token_bytes(16)
    b64_nonce = base64.urlsafe_b64encode(nonce).decode("utf-8").rstrip("=")
    encryptor = Cipher(algorithms.AES(bytes.fromhex(ENV['encryption_key'])), modes.CTR(nonce)).encryptor()
    ciphertext = encryptor.update(payload) + encryptor.finalize()
    b64_ciphertext = base64.urlsafe_b64encode(ciphertext).decode("utf-8").rstrip("=")
    signature = hmac.new(bytes.fromhex(ENV['signing_key']), f"{b64_nonce}.{b64_ciphertext}".encode("utf-8"), hashlib.sha256).digest()
    b64_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{b64_nonce}.{b64_ciphertext}.{b64_signature}"
def TOKEN_DeserializeAndVerify(token):
    sections = token.split(".")
    if len(sections) != 3:
        raise Exception("Token must contain 3 sections.")
    b64_nonce = sections[0]
    b64_ciphertext = sections[1]
    b64_signature = sections[2]
    good_signature = hmac.new(bytes.fromhex(ENV['signing_key']), f"{b64_nonce}.{b64_ciphertext}".encode("utf-8"), hashlib.sha256).digest()
    b64_good_signature = base64.urlsafe_b64encode(good_signature).decode("utf-8").rstrip("=")
    if not hmac.compare_digest(b64_signature, b64_good_signature):
        raise Exception("Invalid signature.")
    nonce = base64.urlsafe_b64decode(b64_nonce.encode("utf-8") + b"============")
    ciphertext = base64.urlsafe_b64decode(b64_ciphertext.encode("utf-8") + b"=============")
    decryptor = Cipher(algorithms.AES(bytes.fromhex(ENV['encryption_key'])), modes.CTR(nonce)).decryptor()
    payload = (decryptor.update(ciphertext) + decryptor.finalize()).decode("utf-8")
    data = IO_DeserializeJson(payload)
    if int(IO_GetEpoch()) - data['timestamp'] > 60 * 15:
        raise Exception("This link has expired. Please request a new one.")
    del data["timestamp"]
    return data
# endregion

# region Discord
discord_client = discord.Client(intents=discord.Intents.default())
discord_command_tree = discord.app_commands.CommandTree(discord_client)
async def guild_verify(interaction: discord.Interaction, already_verified):
    onid_email = DB[interaction.user.id]['onid_email']
    onid_name = DB[interaction.user.id]['onid_name']

    verified_role = None
    for guild_role in interaction.guild.roles:
        if guild_role.name == "ONID-Verified":
            verified_role = guild_role
            break

    if verified_role == None:
        LOG_Warning(f"Verified @{interaction.user.name} <@{interaction.user.id}> as \"{onid_name}\" {onid_email} on \"{interaction.guild.name}\" {interaction.guild.id} but failed to assign ONID-Verified role because it does not exist.")
        if already_verified:
            await interaction.followup.send(f"You are already verified however this server doesn't have an \"ONID-Verified\" role to give you. Please reach out to the server administrators to create this role.", ephemeral=True)
        else:
            await interaction.followup.send(f"You have been successfully verified however this server doesn't have an \"ONID-Verified\" role to give you. Please reach out to the server administrators to create this role.", ephemeral=True)
        return

    try:
        await interaction.user.add_roles(verified_role)
    except discord.errors.Forbidden as ex:
        LOG_Warning(f"Failed to assign ONID-Verified role to @{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} due to insufficient permissions.")
        if already_verified:
            await interaction.followup.send(f"You are already verified however {discord_client.user.mention} doesn't have permission to assign you the ONID-Verified role. Please reach out to the server administrators to grant {discord_client.user.mention} this permission.", ephemeral=True)
        else:
            await interaction.followup.send(f"You have been successfully verified however {discord_client.user.mention} doesn't have permission to assign you the ONID-Verified role. Please reach out to the server administrators to grant {discord_client.user.mention} this permission.", ephemeral=True)
        return

    try:
        await interaction.user.edit(nick=onid_name)
    except discord.errors.Forbidden as ex:
        LOG_Warning(f"Failed to nick @{interaction.user.name} <@{interaction.user.id}> to \"{onid_name}\" {onid_email} on \"{interaction.guild.name}\" {interaction.guild.id} due to insufficient permissions.")

    LOG_Info(f"Verified @{interaction.user.name} <@{interaction.user.id}> as \"{onid_name}\" {onid_email} on \"{interaction.guild.name}\" {interaction.guild.id}.")
    if already_verified:
        await interaction.followup.send(f"You are already verified as \"{onid_name}\" {onid_email}. The ONID-Verified role has been assigned to you on this server.", ephemeral=True)
    else:
        await interaction.followup.send(f"You have successfully verified as \"{onid_name}\" {onid_email}.", ephemeral=True)
async def guild_unverify(interaction: discord.Interaction):
    verified_role = None
    for guild_role in interaction.guild.roles:
        if guild_role.name == "ONID-Verified":
            verified_role = guild_role
            break

    if verified_role == None:
        await interaction.followup.send(f"This server doesn't have an \"ONID-Verified\" role.", ephemeral=True)

    try:
        await interaction.user.remove_roles(verified_role)
    except discord.errors.Forbidden as ex:
        await interaction.followup.send(f"Failed to remove ONID-Verified role due to insufficient permissions.", ephemeral=True)
        return
    await interaction.followup.send(f"Done!", ephemeral=True)

class GetVerifiedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Get Verified!", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="get_verified_button")
    async def get_verified_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            already_verified = interaction.user.id in DB and interaction.user.id != discord_client.application.owner.id
            LOG_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} pressed enter onid button and {'is' if already_verified else 'is not'} already verified.")
            if already_verified:
                await interaction.response.defer(ephemeral=True)
                await guild_verify(interaction, already_verified=True)
            else:
                await interaction.response.send_modal(OnidInputModal())
        except Exception as ex:
            LOG_Exception(ex)
            raise

class OnidInputModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Enter OSU Email", custom_id="onid_input_modal", timeout=None)
    onid_input = discord.ui.TextInput(label="Enter your @oregonstate.edu email address:", placeholder="onid@oregonstate.edu", required=True, custom_id="onid_text_input")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            LOG_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} submitted onid input \"{self.onid_input.value}\".")
            if interaction.user.id in DB and interaction.user.id != discord_client.application.owner.id:
                LOG_Error(f"Refusing to submit OnidInputModal because @{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} is already verified.")
                return # Hard bail and fail interaction
            await interaction.response.defer(ephemeral=True)
            onid_email = str(self.onid_input.value).strip().lower()
            if not onid_email.endswith("@oregonstate.edu") or len(onid_email) <= len("@oregonstate.edu"):
                LOG_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} submitted invalid onid input \"{self.onid_input.value}\".")
                await interaction.followup.send(f"The ONID you entered doesn't look quite right. Please try again.", ephemeral=True)
                return
            onid_name = OSU_LookupOnidName(onid_email)
            if onid_name == None:
                LOG_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} submitted invalid onid input \"{self.onid_input.value}\".")
                await interaction.followup.send(f"The ONID you entered doesn't look quite right. Please try again.", ephemeral=True)
                return
            token = "ABC123"
            LOG_Info(f"Created token {token} for @{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} for \"{onid_name}\" {onid_email}")
            SMTP_SendToken(onid_email, token) # TODO
            await interaction.followup.send(f"A verification link has been sent to **{onid_email}**.\n\nLinks can take up to 5 minutes to arive. Check your **SPAM** folder before requesting a new link.", ephemeral=True)
        except Exception as ex:
            LOG_Exception(ex)
            raise

"""
            LOG_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} has been verified as \"{request['onid_name']}\" {request['onid_email']} in DB.")
            DB[interaction.user.id] = { "onid_email": request['onid_email'], "onid_name": request['onid_name'], "notes": "" }
            DB_Save()
"""

"""
# Create Token Stub
payload = { "timestamp": IO_GetEpoch(), "discord_user_id": discord_user_id, "discord_guild_id": discord_guild_id, "onid_email": onid_email, "onid_name": onid_name }
"""

@discord_client.event
async def on_ready():
    try:
        await discord_command_tree.sync()
        discord_client.add_view(GetVerifiedView())
        await discord_client.change_presence(activity=discord.CustomActivity("Verifying ONID email addresses..."), status=discord.Status.online)
        LOG_Info(f"{socket.gethostname()} online as User({discord_client.user.id}, \"{discord_client.user.name}\").")
    except Exception as ex:
        LOG_Exception(ex)
        raise
@discord_client.event
async def on_guild_join(guild: discord.Guild):
    LOG_Info(f"ONIDbot was added to Guild({guild.id}, \"{guild.name}\").")
@discord_command_tree.command(name="post_verification_buttons", description="Posts the verification buttons to the current channel.")
async def post_verification_buttons(interaction: discord.Interaction):
    try:
        LOG_Info(f"<@{interaction.user.id}> ran post_verification_buttons.")
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("You need the administrator permission in this server to run this command.")
            return
        try:
            await interaction.channel.send("", view=GetVerifiedView())
        except discord.errors.Forbidden as ex:
                LOG_Info(f"Failed to post verification buttons on \"{interaction.guild.name}\" {interaction.guild.id} due to insufficient permissions.")
                await interaction.followup.send(f"{discord_client.user.mention} does not have permission to post messages in this channel and therefore could not post the verification buttons.", ephemeral=True)
                return
        await interaction.followup.send("Done!")
    except Exception as ex:
        LOG_Exception(ex)
        raise
@discord_command_tree.command(name="get_verification_info", description="Prints weather a given Discord account is ONID verified.")
async def get_verification_info(interaction: discord.Interaction, user: discord.User):
    try:
        LOG_Info(f"<@{interaction.user.id}> ran get_verification_info on <@{user.id}>.")
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.id in DB:
            await interaction.followup.send("You must be verified by ONIDbot to run this command.", ephemeral=True)
            return
        if user.id in DB:
            await interaction.followup.send(f"{user.mention} is verified as \"{DB[user.id]['onid_name']}\" {DB[user.id]['onid_email']}.", ephemeral=True)
        else:
            await interaction.followup.send(f"{user.mention} is not verified.", ephemeral=True)
    except Exception as ex:
        LOG_Exception(ex)
        raise
# endregion

# region API Server
async def API_ProcessToken(token):
    data = TOKEN_DeserializeAndVerify(token)
    return "{ \"success\": true, \"message\": \"You have been verified with ONIDbot. You can safely close this window and return to Discord. TOKEN: " + IO_SerializeJson(data) + "\" }"
async def API_HandleClient(reader, writer):
    try:
        try:
            token = (await asyncio.wait_for(reader.readline(), timeout=2.0)).decode("utf-8").rstrip("\n")
            LOG_Info(f"Incoming request with token \"{token}\".")
            response = await API_ProcessToken(token)
            writer.write(response.encode("utf-8"))
            await asyncio.wait_for(writer.drain(), timeout=2.0)
        finally:
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
    except Exception as ex:
        LOG_Exception(ex)
async def API_RunServer():
    server = await asyncio.start_server(API_HandleClient, "0.0.0.0", ENV['api_port'])
    LOG_Info(f"API Server running on {socket.gethostname()}:{ENV['api_port']}.")
    async with server:
        await server.serve_forever()
# endregion

token = ""
if os.stat(emailpath).st_mode != 33152:
    raise Exception("Insecure permissions on database.json. Try chmod 600 database.json")
subject = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "subject.txt")).replace("##TOKEN##", token)
body = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "email.txt")).replace("##TOKEN##", token)
body_html = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "email.html")).replace("##TOKEN##", token)

# region Main
async def Main():
    try:
        ENV_Load()
        DB_Load()
        await asyncio.gather(API_RunServer(), discord_client.start(ENV['discord_token']))
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as ex:
        LOG_Exception(ex)
        sys.exit(1)
asyncio.run(Main())
# endregion
