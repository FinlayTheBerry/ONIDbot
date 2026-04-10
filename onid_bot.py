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
import time

# Bot authentication url:
# https://discord.com/oauth2/authorize?client_id={CLIENTID}

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
def IO_AppendFile(filePath, contents, binary=False):
    filePath = IO_RealPath(filePath)
    with open(filePath, "ab" if binary else "a", encoding=None if binary else "utf-8") as f:
        f.write(contents)
def IO_SerializeJson(obj, compact=False):
    return json.dumps(obj, indent=None if compact else 4)
def IO_DeserializeJson(jsonString):
    return json.loads(jsonString)
def IO_GetEpoch():
    return time.time() + time.localtime().tm_gmtoff
def IO_FormatEpoch(epoch):
    timestamp = datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc)
    return timestamp.strftime("%I:%M%p %m/%d").lower()
# endregion

# region Logs
def Log_Generic(message, log_type, ansi_color):
    padding = " " * (8 - len(log_type)) if len(log_type) < 8 else ""
    formatted_message = f"{log_type}{padding}({IO_FormatEpoch(IO_GetEpoch())} {int(IO_GetEpoch())}): {message}"
    print(f"\033[{ansi_color}m{formatted_message}\033[0m", flush=True)
    log_path = os.path.join(IO_GetScriptDir(), "log.txt")
    IO_AppendFile(log_path, f"{formatted_message}\n")
def Log_Info(message):
    Log_Generic(message, "Info", "37")
def Log_Warning(message):
    Log_Generic(message, "Warning", "33")
def Log_Error(message):
    Log_Generic(message, "ERROR", "31")
def Log_Exception(ex):
    tb = ex.__traceback__
    while tb is not None:
        if IO_RealPath(tb.tb_frame.f_code.co_filename) == IO_RealPath(__file__):
            message = repr(ex)
            funcname = "<module>" if tb.tb_frame.f_code.co_name == "<module>" else tb.tb_frame.f_code.co_name + "()"
            lineno = tb.tb_lineno
            line = IO_ReadFile(tb.tb_frame.f_code.co_filename).splitlines()[lineno - 1].strip()
            Log_Generic(f"{message} in {funcname} line {lineno}: {line}", "PY_EX", "31")
            return
        tb = tb.tb_next
    Log_Generic(f"{repr(ex)} at unknown location", "PY_EX", "31")
# endregion

# region Environment
ENV = None
def Env_Load():
    global ENV
    env_path = os.path.join(IO_GetScriptDir(), "environment.json")
    if os.stat(env_path).st_mode != 33152:
        raise Exception("Insecure permissions on environment.json. Try chmod 600 environment.json")
    ENV = IO_DeserializeJson(IO_ReadFile(env_path))
Env_Load()
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
    IO_WriteFile(backup_path, IO_ReadFile(db_path))
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
DB_Load()
# endregion

# region OSU API
def OSU_LookupOnidName(onid_email):
    # Get a token
    response = requests.post("https://api.oregonstate.edu/oauth2/token", data={"grant_type": "client_credentials"}, auth=(ENV["osu_api_id"], ENV["osu_api_secret"]))
    response.raise_for_status()
    token = response.json()["access_token"]

    # Send a request
    headers = { "Authorization": f"Bearer {token}", "Accept": "application/json" }
    response = requests.get(f"https://api.oregonstate.edu/v2/directory?filter[emailAddress]={onid_email}", headers=headers)
    response.raise_for_status()
    data = response.json()["data"]

    # Return output or None
    if len(data) == 1:
        output = f"{data[0]['attributes']['firstName']} {data[0]['attributes']['lastName']}"
        Log_Info(f"OSU directory lookup for \"{onid_email}\" returned \"{output}\".")
        return output
    else:
        Log_Warning(f"OSU directory lookup for \"{onid_email}\" returned no data.")
        return None
# endregion

# region COE SMTP
def SMTP_SendEmail(to, subject, body, body_html):
    SMTP_SERVER = "mail.engr.oregonstate.edu"
    SMTP_PORT = 465

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{ENV['email_username']}@oregonstate.edu"
    msg["To"] = to
    msg.set_content(body)
    msg.add_alternative(body_html, subtype="html")

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp_server:
        smtp_server.login(ENV["email_username"], ENV["email_password"])
        smtp_server.send_message(msg)

    Log_Info(f"Sent email to \"{to}\" with subject \"{subject}\".")
def SMTP_SendCode(to, code):
    subject = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "subject.txt")).replace("##CODE##", code)
    body = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "email.txt")).replace("##CODE##", code)
    body_html = IO_ReadFile(os.path.join(IO_GetScriptDir(), "email", "email.html")).replace("##CODE##", code)
    SMTP_SendEmail(to, subject, body, body_html)
# endregion

# region Discord
discord_client = discord.Client(intents=discord.Intents.default())
discord_command_tree = discord.app_commands.CommandTree(discord_client)
DISCORD_APP_OWNER_ID = None
async def guild_verify(interaction: discord.Interaction, already_verified):
    onid_email = DB[interaction.user.id]["onid_email"]
    onid_name = DB[interaction.user.id]["onid_name"]

    verified_role = None
    for guild_role in interaction.guild.roles:
        if guild_role.name == "ONID-Verified":
            verified_role = guild_role
            break

    if verified_role == None:
        Log_Warning(f"Verified @{interaction.user.name} <@{interaction.user.id}> as \"{onid_name}\" {onid_email} on \"{interaction.guild.name}\" {interaction.guild.id} but failed to assign ONID-Verified role because it does not exist.")
        if already_verified:
            await interaction.followup.send(f"You are already verified however this server doesn't have an \"ONID-Verified\" role to give you. Please reach out to the server administrators to create this role.", ephemeral=True)
        else:
            await interaction.followup.send(f"You have been successfully verified however this server doesn't have an \"ONID-Verified\" role to give you. Please reach out to the server administrators to create this role.", ephemeral=True)
        return

    try:
        await interaction.user.add_roles(verified_role)
    except discord.errors.Forbidden as ex:
        Log_Warning(f"Failed to assign ONID-Verified role to @{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} due to insufficient permissions.")
        if already_verified:
            await interaction.followup.send(f"You are already verified however {discord_client.user.mention} doesn't have permission to assign you the ONID-Verified role. Please reach out to the server administrators to grant {discord_client.user.mention} this permission.", ephemeral=True)
        else:
            await interaction.followup.send(f"You have been successfully verified however {discord_client.user.mention} doesn't have permission to assign you the ONID-Verified role. Please reach out to the server administrators to grant {discord_client.user.mention} this permission.", ephemeral=True)
        return

    try:
        await interaction.user.edit(nick=onid_name)
    except discord.errors.Forbidden as ex:
        Log_Warning(f"Failed to nick @{interaction.user.name} <@{interaction.user.id}> to \"{onid_name}\" {onid_email} on \"{interaction.guild.name}\" {interaction.guild.id} due to insufficient permissions.")

    Log_Info(f"Verified @{interaction.user.name} <@{interaction.user.id}> as \"{onid_name}\" {onid_email} on \"{interaction.guild.name}\" {interaction.guild.id}.")
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
            already_verified = interaction.user.id in DB and interaction.user.id != DISCORD_APP_OWNER_ID
            Log_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} pressed enter onid button and {'is' if already_verified else 'is not'} already verified.")
            if already_verified:
                await interaction.response.defer(ephemeral=True)
                await guild_verify(interaction, already_verified=True)
            else:
                await interaction.response.send_modal(OnidInputModal())
        except Exception as ex:
            Log_Exception(ex)
            raise ex

class OnidInputModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Enter OSU Email", custom_id="onid_input_modal", timeout=None)
    onid_input = discord.ui.TextInput(label="Enter your @oregonstate.edu email address:", placeholder="onid@oregonstate.edu", required=True, custom_id="onid_text_input")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            Log_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} submitted onid input \"{self.onid_input.value}\".")
            if interaction.user.id in DB and interaction.user.id != DISCORD_APP_OWNER_ID:
                Log_Error(f"Refusing to submit OnidInputModal because @{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} is already verified.")
                return # Hard bail and fail interaction
            await interaction.response.defer(ephemeral=True)
            onid_email = str(self.onid_input.value).strip().lower()
            if not onid_email.endswith("@oregonstate.edu") or len(onid_email) <= len("@oregonstate.edu"):
                Log_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} submitted invalid onid input \"{self.onid_input.value}\".")
                await interaction.followup.send(f"The ONID you entered doesn't look quite right. Please try again.", ephemeral=True)
                return
            onid_name = OSU_LookupOnidName(onid_email)
            if onid_name == None:
                Log_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} submitted invalid onid input \"{self.onid_input.value}\".")
                await interaction.followup.send(f"The ONID you entered doesn't look quite right. Please try again.", ephemeral=True)
                return
            code = "ABC123"
            Log_Info(f"Created code {code} for @{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} for \"{onid_name}\" {onid_email}")
            SMTP_SendCode(onid_email, code)
            await interaction.followup.send(f"A verification code has been sent to **{onid_email}**.\n\nCodes can take up to 5 minutes to arive. Check your **SPAM** folder before requesting a new code.", ephemeral=True)
        except Exception as ex:
            Log_Exception(ex)
            raise ex

"""
            Log_Info(f"@{interaction.user.name} <@{interaction.user.id}> on \"{interaction.guild.name}\" {interaction.guild.id} has been verified as \"{request['onid_name']}\" {request['onid_email']} in DB.")
            DB[interaction.user.id] = { "onid_email": request["onid_email"], "onid_name": request["onid_name"], "notes": "" }
            DB_Save()
"""

@discord_client.event
async def on_ready():
    global DISCORD_APP_OWNER_ID
    try:
        DISCORD_APP_OWNER_ID = discord_client.application.owner.id
        await discord_command_tree.sync()
        discord_client.add_view(GetVerifiedView())
        await discord_client.change_presence(activity=discord.CustomActivity("Verifying ONID email addresses..."), status=discord.Status.online)
        Log_Info(f"Online as {discord_client.user}")
    except Exception as ex:
        Log_Exception(ex)
        raise ex
@discord_client.event
async def on_guild_join(guild: discord.Guild):
    Log_Info(f"ONIDbot was added to a new guild \"{guild.name}\" {guild.id}.")
@discord_command_tree.command(name="post_verification_buttons", description="Posts the verification buttons to the current channel.")
async def post_verification_buttons(interaction: discord.Interaction):
    try:
        Log_Info(f"<@{interaction.user.id}> ran post_verification_buttons.")
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("You need the administrator permission in this server to run this command.")
            return
        try:
            await interaction.channel.send("", view=GetVerifiedView())
        except discord.errors.Forbidden as ex:
                Log_Info(f"Failed to post verification buttons on \"{interaction.guild.name}\" {interaction.guild.id} due to insufficient permissions.")
                await interaction.followup.send(f"{discord_client.user.mention} does not have permission to post messages in this channel and therefore could not post the verification buttons.", ephemeral=True)
                return
        await interaction.followup.send("Done!")
    except Exception as ex:
        Log_Exception(ex)
        raise ex
@discord_command_tree.command(name="get_verification_info", description="Prints weather a given Discord account is ONID verified.")
async def get_verification_info(interaction: discord.Interaction, user: discord.User):
    try:
        Log_Info(f"<@{interaction.user.id}> ran get_verification_info on <@{user.id}>.")
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.id in DB:
            await interaction.followup.send("You must be verified by ONIDbot to run this command.", ephemeral=True)
            return
        if user.id in DB:
            await interaction.followup.send(f"{user.mention} is verified as \"{DB[user.id]['onid_name']}\" {DB[user.id]['onid_email']}.", ephemeral=True)
        else:
            await interaction.followup.send(f"{user.mention} is not verified.", ephemeral=True)
    except Exception as ex:
        Log_Exception(ex)
        raise ex
# endregion

# region Main
def Main():
    try:
        discord_client.run(ENV["discord_token"])
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as ex:
        Log_Exception(ex)
        sys.exit(1)
Main()
# endregion
