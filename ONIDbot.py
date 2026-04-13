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
    fd = os.open(filePath, os.O_WRONLY)
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

# region Database
DB = None
def DB_Load():
    global DB
    db_path = os.path.join(IO_GetScriptDir(), "database.json")
    DB = IO_DeserializeJson(IO_ReadFile(db_path))
    DB = { int(key): value for key, value in DB.items() }
def DB_Backup():
    db_path = os.path.join(IO_GetScriptDir(), "database.json")
    backup_file_name = f"backups/{int(IO_GetEpoch())}.json"
    backup_path = os.path.join(IO_GetScriptDir(), backup_file_name)
    IO_CreateFile(backup_path, IO_ReadFile(db_path), 0o600)
    LOG_Info(f"DB Backup - {backup_file_name}")
def DB_Save():
    db_path = os.path.join(IO_GetScriptDir(), "database.json")
    IO_WriteFile(db_path, IO_SerializeJson(DB))
    backups_dir_path = os.path.join(IO_GetScriptDir(), "backups")
    latest_backup_time = 0
    for backup_name in os.listdir(backups_dir_path):
        backup_time = int(os.path.splitext(backup_name)[0])
        if backup_time > latest_backup_time:
            latest_backup_time = backup_time
    if int(IO_GetEpoch()) - latest_backup_time > 24 * 60 * 60:
        DB_Backup()
# endregion

# region OSU API
def OSU_LookupOnidName(onid_email, raw_data=False):
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
    if raw_data:
        LOG_Info(f"OSU API - \"{onid_email}\" - RAW DATA")
        return IO_SerializeJson(data)
    elif len(data) == 1:
        output = f"{data[0]['attributes']['firstName']} {data[0]['attributes']['lastName']}"
        LOG_Info(f"OSU API - \"{onid_email}\" - \"{output}\"")
        return output
    elif len(data) == 0:
        LOG_Warning(f"OSU API - \"{onid_email}\" - NO DATA")
        return None
    else:
        LOG_Warning(f"OSU API - \"{onid_email}\" - TOO MANY HITS")
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
    LOG_Info(f"Email - \"{to}\" - \"{subject}\"")
# endregion

# region Tokens And Crypto
def TOKEN_SerializeAndSign(data):
    data["timestamp"] = int(IO_GetEpoch())
    payload = IO_SerializeJson(data, compact=True).encode("utf-8")
    nonce = secrets.token_bytes(16)
    b64_nonce = base64.urlsafe_b64encode(nonce).decode("utf-8").rstrip("=")
    encryptor = Cipher(algorithms.AES(bytes.fromhex(ENV['encryption_key'])), modes.CTR(nonce)).encryptor()
    ciphertext = encryptor.update(payload) + encryptor.finalize()
    b64_ciphertext = base64.urlsafe_b64encode(ciphertext).decode("utf-8").rstrip("=")
    signature = hmac.new(bytes.fromhex(ENV['signing_key']), f"{b64_nonce}.{b64_ciphertext}".encode("utf-8"), hashlib.sha256).digest()
    b64_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{b64_nonce}.{b64_ciphertext}.{b64_signature}"
def TOKEN_DeserializeAndVerify(token, no_expiry=False):
    sections = token.split(".")
    if len(sections) != 3:
        LOG_Warning(f"Bad Token - Section Count - {token}")
        return None
    b64_nonce = sections[0]
    b64_ciphertext = sections[1]
    b64_signature = sections[2]
    good_signature = hmac.new(bytes.fromhex(ENV['signing_key']), f"{b64_nonce}.{b64_ciphertext}".encode("utf-8"), hashlib.sha256).digest()
    b64_good_signature = base64.urlsafe_b64encode(good_signature).decode("utf-8").rstrip("=")
    if not hmac.compare_digest(b64_signature, b64_good_signature):
        LOG_Warning(f"Bad Token - Signature - {token}")
        return None
    nonce = base64.urlsafe_b64decode(b64_nonce.encode("utf-8") + b"===")
    ciphertext = base64.urlsafe_b64decode(b64_ciphertext.encode("utf-8") + b"===")
    decryptor = Cipher(algorithms.AES(bytes.fromhex(ENV['encryption_key'])), modes.CTR(nonce)).decryptor()
    payload = (decryptor.update(ciphertext) + decryptor.finalize()).decode("utf-8")
    data = IO_DeserializeJson(payload)
    if int(IO_GetEpoch()) - data['timestamp'] > 60 * 15 and not no_expiry:
        LOG_Warning(f"Bad Token - Expired - {token}")
        return None
    return data
# endregion

# region Discord
discord_client = discord.Client(intents=discord.Intents.default())
discord_command_tree = discord.app_commands.CommandTree(discord_client)

@discord_client.event
async def on_ready(): 
    try:
        await discord_command_tree.sync()
        discord_client.add_view(GetVerifiedView())
        await discord_client.change_presence(activity=discord.CustomActivity("🛡️ Verifying OSU Students..."), status=discord.Status.online)
        LOG_Info(f"Bot Online - {socket.gethostname()} - {LOG_FormatUser(discord_client.user)}")
    except Exception as ex:
        LOG_Exception(ex)
        raise
@discord_client.event
async def on_guild_join(guild: discord.Guild): 
    LOG_Info(f"Join Guild - {LOG_FormatGuild(guild)}")

class GetVerifiedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Get Verified!", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="get_verified_button")
    async def DIS_GetVerifiedButton(self, interaction: discord.Interaction, button: discord.ui.Button): 
        try:
            already_verified = interaction.user.id in DB and interaction.user.id != discord_client.application.owner.id
            if already_verified:
                await interaction.response.defer(ephemeral=True)
                LOG_Info(f"Get Verified - Refreshing Verification - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
                error = await DIS_Verify(interaction.user.id, interaction.guild.id, DB[interaction.user.id]['onid_email'], DB[interaction.user.id]['onid_name'])
                if error == None:
                    await interaction.followup.send("You are already verified with ONIDbot and have been given the ONID-Verified role on this server.", ephemeral=True)
                else:
                    await interaction.followup.send(f"An error occured. Please DM @finlaytheberry if the issue persists. Error details: {error}", ephemeral=True)
            else:
                LOG_Info(f"Get Verified - Sending Modal - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
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
            await interaction.response.defer(ephemeral=True)
            already_verified = interaction.user.id in DB and interaction.user.id != discord_client.application.owner.id
            if already_verified:
                LOG_Info(f"Onid Input - Refreshing Verification - \"{self.onid_input.value}\" - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
                error = await DIS_Verify(interaction.user.id, interaction.guild.id, DB[interaction.user.id]['onid_email'], DB[interaction.user.id]['onid_name'])
                if error == None:
                    await interaction.followup.send("You are already verified with ONIDbot and have been given the ONID-Verified role on this server.", ephemeral=True)
                else:
                    await interaction.followup.send(f"An error occured. Please DM @finlaytheberry if the issue persists. Error details: {error}", ephemeral=True)
            else:
                onid_email = str(self.onid_input.value).strip().lower()
                if not onid_email.endswith("@oregonstate.edu"):
                    LOG_Info(f"Onid Input - Bad Format - \"{self.onid_input.value}\" - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
                    await interaction.followup.send(f"The email address you entered must end with @oregonstate.edu. Please try again.", ephemeral=True)
                    return
                onid_name = OSU_LookupOnidName(onid_email)
                if onid_name == None:
                    LOG_Info(f"Onid Input - No Directory - \"{self.onid_input.value}\" - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
                    await interaction.followup.send(f"The email address you entered could not be found in the OSU Directory. Please try again.", ephemeral=True)
                    return
                LOG_Info(f"Onid Input - Sending Email - \"{self.onid_input.value}\" - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
                data = { "discord_guild_id": interaction.guild.id, "discord_user_id": interaction.user.id, "onid_email": onid_email, "onid_name": onid_name }
                token = TOKEN_SerializeAndSign(data)
                LOG_Info(f"Token Create - {token} - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
                subject = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "subject.txt")).replace("##TOKEN##", token)
                body = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "email.txt")).replace("##TOKEN##", token)
                body_html = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "email.html")).replace("##TOKEN##", token)
                SMTP_SendEmail(onid_email, subject, body, body_html)
                await interaction.followup.send(f"A verification link has been sent to **{onid_email}**.\n\nLinks can take up to 5 minutes to arive. Check your **SPAM** folder before requesting a new link.", ephemeral=True)
        except Exception as ex:
            LOG_Exception(ex)
            raise

@discord_command_tree.command(name="post_verification_button", description="Posts the verification button in the current channel.")
async def DIS_PostVerificationButton(interaction: discord.Interaction): 
    try:
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            LOG_Info(f"Post Button - No Admin - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
            await interaction.followup.send("You need the administrator permission on this server to run this command.")
            return
        try:
            await interaction.channel.send("", view=GetVerifiedView())
        except discord.errors.Forbidden as ex:
            LOG_Info(f"Post Button - No Permission - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
            await interaction.followup.send(f"{discord_client.user.mention} does not have permission to post messages in this channel and therefore could not post the verification buttons.", ephemeral=True)
            return
        LOG_Info(f"Post Button - Done! - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
        await interaction.followup.send("Done!")
    except Exception as ex:
        LOG_Exception(ex)
        raise
@discord_command_tree.command(name="get_verification_info", description="Prints all the information ONIDbot has about a given Discord user.")
async def DIS_GetVerificationInfo(interaction: discord.Interaction, user: discord.User): 
    try:
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.id in DB:
            LOG_Info(f"Get Info - Not Verified - {LOG_FormatUser(interaction.user)} - {LOG_FormatUser(user)} - {LOG_FormatGuild(interaction.guild)}")
            await interaction.followup.send("You must be verified by ONIDbot to run this command.", ephemeral=True)
            return
        if user.id in DB:
            LOG_Info(f"Get Info - Done! (yes) - {LOG_FormatUser(interaction.user)} - {LOG_FormatUser(user)} - {LOG_FormatGuild(interaction.guild)}")
            await interaction.followup.send(f"{user.mention} is verified as \"{DB[user.id]['onid_name']}\" {DB[user.id]['onid_email']}.", ephemeral=True)
        else:
            LOG_Info(f"Get Info - Done! (no) - {LOG_FormatUser(interaction.user)} - {LOG_FormatUser(user)} - {LOG_FormatGuild(interaction.guild)}")
            await interaction.followup.send(f"{user.mention} is not verified.", ephemeral=True)
    except Exception as ex:
        LOG_Exception(ex)
        raise
@discord_command_tree.command(name="debug_verification", description="Used to debug ONIDbot. Restricted to ONIDbot developers only.")
async def DIS_DebugVerification(interaction: discord.Interaction, command: str):
    try:
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id != discord_client.application.owner.id:
            LOG_Info(f"Debug - Not Owner - {LOG_FormatUser(interaction.user)} - {LOG_FormatGuild(interaction.guild)}")
            await interaction.followup.send("You must be an ONIDbot developer to run this command.", ephemeral=True)
            return

        try:
            command = command.split(" ", maxsplit=1)
            verb = command[0].lower()
            args = None
            if len(command) > 1:
                args = command[1]

            if verb == "token_info":
                data = TOKEN_DeserializeAndVerify(args, ignore_expiration=True)
                await interaction.followup.send(IO_SerializeJson(data), ephemeral=True)
            elif verb == "dis_get_guild":
                discord_guild = await discord_client.fetch_guild(int(args))
                await interaction.followup.send(LOG_FormatGuild(discord_guild), ephemeral=True)
            elif verb == "dis_get_channel":
                discord_channel = await discord_client.fetch_channel(int(args))
                await interaction.followup.send(LOG_FormatChannel(discord_channel), ephemeral=True)
            elif verb == "dis_get_user":
                discord_user = await discord_client.fetch_user(int(args))
                await interaction.followup.send(LOG_FormatUser(discord_user), ephemeral=True)
            elif verb == "dis_rm_message":
                discord_channel_id, discord_message_id = args.split(" ")
                discord_channel = await discord_client.fetch_channel(int(discord_channel_id))
                discord_message = await discord_channel.fetch_message(int(discord_message_id))
                await discord_message.delete()
                await interaction.followup.send("Done!", ephemeral=True)
            elif verb == "dis_post_button":
                discord_channel = await discord_client.fetch_channel(int(args))
                await discord_channel.send("", view=GetVerifiedView())
                await interaction.followup.send("Done!", ephemeral=True)
            elif verb == "dis_post_instructions":
                discord_channel = await discord_client.fetch_channel(int(args))
                message = f"Welcome to the {discord_channel.guild.name} Discord server!\n\n:shield: To gain access to the rest of the server, you must **verify** your status as an OSU student.\n\n:one: Enter your **@oregonstate.edu** email address and wait for a confirmation email.\n:two: Next, click the provided link and the rest of the server will be **unlocked** for you.\n\n:interrobang: If you need help, feel free to DM me (<@{discord_client.application.owner.id}>) anytime."
                await discord_channel.send(message)
                await interaction.followup.send("Done!", ephemeral=True)
            elif verb == "osu_api_lookup":
                data = OSU_LookupOnidName(args, raw_data=True)
                await interaction.followup.send(data, ephemeral=True)
            elif verb == "env_reload":
                ENV_Load()
                await interaction.followup.send("Done!", ephemeral=True)
            elif verb == "db_get":
                await interaction.followup.send(IO_SerializeJson(DB[int(args)]), ephemeral=True)
            elif verb == "db_reload":
                DB_Load()
                await interaction.followup.send("Done!", ephemeral=True)
            elif verb == "db_save":
                DB_Save()
                await interaction.followup.send("Done!", ephemeral=True)
            elif verb == "db_backup":
                DB_Backup()
                await interaction.followup.send("Done!", ephemeral=True)
            else:
                raise Exception(f"Unknown verb {verb}.")
        except Exception as ex:
            await interaction.followup.send(repr(ex), ephemeral=True)
    except Exception as ex:
        LOG_Exception(ex)
        raise

async def DIS_Verify(discord_user_id, discord_guild_id, onid_email, onid_name): 
    if not discord_user_id in DB:
        DB[discord_user_id] = { "onid_email": onid_email, "onid_name": onid_name, "notes": "" }
        DB_Save()

    discord_guild = discord_client.get_guild(discord_guild_id)
    if discord_guild is None:
        discord_guild = await discord_client.fetch_guild(discord_guild_id)
    if discord_guild is None:
        LOG_Warning(f"Guild Lookup - {discord_guild_id}")
        return "Failed to lookup guild from token data."

    discord_user = discord_guild.get_member(discord_user_id)
    if discord_user is None:
        discord_user = await discord_guild.fetch_member(discord_user_id)
    if discord_user is None:
        LOG_Warning(f"User Lookup - {discord_user_id} - {LOG_FormatGuild(discord_guild)}")
        return "Failed to lookup user from token data."

    verified_role = None
    for guild_role in discord_guild.roles:
        if guild_role.name == "ONID-Verified":
            verified_role = guild_role
            break
    if verified_role == None:
        LOG_Warning(f"Missing Role - {LOG_FormatUser(discord_user)} - {LOG_FormatGuild(discord_guild)}")
        return "ONID-Verified role does not exist."
    
    try:
        await discord_user.add_roles(verified_role)
    except discord.errors.Forbidden as ex:
        LOG_Warning(f"Missing Perms - Manage Roles - {LOG_FormatUser(discord_user)} - {LOG_FormatGuild(discord_guild)}")
        return "Failed to assign ONID-Verified role due to missing permissions."
    
    try:
        await discord_user.edit(nick=DB[discord_user_id]['onid_name'])
    except discord.errors.Forbidden as ex:
        LOG_Warning(f"Missing Perms - Manage Nicknames - {LOG_FormatUser(discord_user)} - {LOG_FormatGuild(discord_guild)}")
        # Non-fatal

    return None
# endregion

# region API Server
async def API_HandleClient(reader, writer):
    try:
        try:
            token = (await asyncio.wait_for(reader.readline(), timeout=2.0)).decode("utf-8").rstrip("\n")
            LOG_Info(f"API Incoming - {token}")

            error = None
            try:
                data = TOKEN_DeserializeAndVerify(token)
                if data is None:
                    error = "The link may have expired or is invalid. Please try requesting a new link from ONIDbot."
                else:
                    error = await DIS_Verify(data['discord_user_id'], data['discord_guild_id'], data['onid_email'], data['onid_name'])
            except Exception as ex:
                error = str(ex)

            writer.write(IO_SerializeJson({ "success": False if error else True, "message": error }, compact=True).encode("utf-8"))
            await asyncio.wait_for(writer.drain(), timeout=2.0)
        finally:
            writer.close()
            await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
    except Exception as ex:
        LOG_Exception(ex)
async def API_RunServer():
    server = await asyncio.start_server(API_HandleClient, "0.0.0.0", ENV['api_port'])
    LOG_Info(f"API Online - {socket.gethostname()}:{ENV['api_port']}.")
    async with server:
        await server.serve_forever()
# endregion

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