#!/usr/bin/env python

# import discord
import base64
import json
import os
import requests
import asyncio
from datetime import datetime, timezone
import time
import discord
import sys
import secrets

# Bot authentication url:
# https://discord.com/oauth2/authorize?client_id={CLIENTID}

InitTasks = []

# region File IO
async def IO_RealPath(filePath):
    return os.path.realpath(os.path.expanduser(filePath))
async def IO_GetScriptDir():
    return os.path.dirname(await IO_RealPath(__file__))
async def IO_WriteFile(filePath, contents, binary=False):
    filePath = await IO_RealPath(filePath)
    with open(filePath, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(contents)
async def IO_ReadFile(filePath, defaultContents=None, binary=False):
    filePath = await IO_RealPath(filePath)
    if defaultContents != None and not os.path.exists(filePath):
        return defaultContents
    with open(filePath, "rb" if binary else "r", encoding=None if binary else "utf-8") as f:
        return f.read()
async def IO_SerializeJson(obj, compact=False):
    return json.dumps(obj, indent=None if compact else 4)
async def IO_DeserializeJson(jsonString):
    return json.loads(jsonString)
async def IO_GetEpoch():
    return int(time.time()) + time.localtime().tm_gmtoff
async def IO_GetTime():
    epoch = await IO_GetEpoch()
    timestamp = datetime.fromtimestamp(epoch, tz=timezone.utc)
    return timestamp.strftime("%I:%M%p %m/%d").lower()
# endregion

# region Environment
ENV = None
async def Env_Load():
    global ENV
    env_path = os.path.join(await IO_GetScriptDir(), "environment.json")
    ENV = await IO_DeserializeJson(await IO_ReadFile(env_path))
asyncio.run(Env_Load())
# endregion

# region Logs
async def Log_Generic(message, log_type, ansi_color):
    padding = " " * (8 - len(log_type)) if len(log_type) < 8 else ""
    formatted_message = f"{log_type}{padding}({await IO_GetTime()} {await IO_GetEpoch()}): {message}"
    print(f"\033[{ansi_color}m{formatted_message}\033[0m", flush=True)
    log_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "log.txt")
    log_contents = ""
    if os.path.exists(log_path):
        log_contents = await IO_ReadFile(log_path)
    await IO_WriteFile(log_path, log_contents + f"{formatted_message}\n")
async def Log_Info(message):
    await Log_Generic(message, "Info", "37")
async def Log_Warning(message):
    await Log_Generic(message, "Warning", "33")
async def Log_Error(message):
    await Log_Generic(message, "ERROR", "31")
async def Log_Exception(ex):
    tb = ex.__traceback__
    while tb is not None:
        if os.path.realpath(tb.tb_frame.f_code.co_filename) == os.path.realpath(__file__):
            message = str(ex)
            funcname = "<module>" if tb.tb_frame.f_code.co_name == "<module>" else tb.tb_frame.f_code.co_name + "()"
            lineno = tb.tb_lineno
            line = await IO_ReadFile(tb.tb_frame.f_code.co_filename).splitlines()[lineno - 1].strip()
            await Log_Generic(f"{message} in {funcname} line {lineno}: {line}", "ERROR", "31")
            return
        tb = tb.tb_next
    await Log_Generic(f"{str(ex)} at unknown location", "ERROR", "31")
# endregion

# Working with the main user database.
DB = None
async def DB_Load():
    global DB
    db_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "database.json")
    if os.path.isfile(db_path):
        DB = await IO_DeserializeJson(IO_ReadFile(db_path))
    else:
        DB = {}
        await DB_Save()
async def DB_Save():
    db_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "database.json")
    await IO_WriteFile(db_path, await IO_SerializeJson(DB))
    backups_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "backups")
    if not os.path.isdir(backups_dir_path):
        os.mkdir(backups_dir_path)
        await Log_Warning(f"{backups_dir_path} did not exist so it was created.")
    latest_backup_time = 0
    for backup_path in os.listdir(backups_dir_path):
        if not os.path.isfile(backup_path):
            await Log_Warning(f"{backup_path} is not a file.")
            continue
        try:
            backup_time = int(os.path.splitext(backup_path)[0])
        except:
            await Log_Warning(f"{backup_path} is not a valid file name.")
            continue
        if backup_time > latest_backup_time:
            latest_backup_time = backup_time
    if await IO_GetEpoch() - latest_backup_time > 24 * 60 * 60:
        backup_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"backups/{await IO_GetEpoch()}.json")
        await IO_WriteFile(backup_path, await IO_ReadFile(db_path))
        await Log_Info(f"Backed up database.json to {backup_path}.")
InitTasks.append(DB_Load)

# region OSU API
async def OSU_LookupOnidName(onid_email):
    # Get a token
    response = requests.post("https://api.oregonstate.edu/oauth2/token", data={"grant_type": "client_credentials"}, auth=(ENV["osu_api_id"], ENV["osu_api_secret"]))
    response.raise_for_status()
    token = response.json()["access_token"]

    # Send a request
    headers = { "Authorization": f"Bearer {token}", "Accept": "application/json" }
    response = requests.get(f"https://api.oregonstate.edu/v2/directory?filter[emailAddress]={onid_email}", headers=headers)
    response.raise_for_status()
    data = response.json()["data"]

    # Manual Override For christj@oregonstate.edu
    if onid_email == "christj@oregonstate.edu":
        data = [ { "attributes": { "firstName": "Finlay", "lastName": "Christ" } } ]

    # Return output or None
    if len(data) == 1:
        output = f"{data[0]['attributes']['firstName']} {data[0]['attributes']['lastName']}"
        await Log_Info(f"OSU directory lookup for {onid_email} returned {output}.")
        return output
    else:
        await Log_Warning(f"OSU directory lookup for {onid_email} returned no data.")
        return None
# endregion

# region MSAuth/Outlook
# Thunderbird Client ID
MS_ClientID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
# Oregon State University Tenant ID
MS_TenantID = "ce6d05e1-3c5e-4d62-87a8-4c4a2713c113"
MS_Scopes = "offline_access https://graph.microsoft.com/Mail.Send"
MS_RefreshToken = None
async def MS_LoadRefreshToken():
    global MS_RefreshToken
    refresh_token_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "msauth_token")
    if os.path.isfile(refresh_token_path):
        MS_RefreshToken = await IO_ReadFile(refresh_token_path)
async def MS_SaveRefreshToken():
    refresh_token_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "msauth_token")
    await IO_WriteFile(refresh_token_path, MS_RefreshToken)
async def MS_DoManualAuthFlow():
    global MS_RefreshToken

    # Tenant id is required for rooted scope paths on the device code endpoint.
    device_code_request_data = { "client_id": MS_ClientID, "scope": MS_Scopes }
    device_code_request = requests.post("https://login.microsoftonline.com/" + MS_TenantID + "/oauth2/v2.0/devicecode", data=device_code_request_data)
    device_code_request.raise_for_status()
    device_code_response = device_code_request.json()
    await Log_Info(device_code_response["message"])

    start = time.time()
    while time.time() - start < int(device_code_response["expires_in"]):
        time.sleep(int(device_code_response["interval"]))
        token_request_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": MS_ClientID,
            "device_code": device_code_response["device_code"],
        }
        token_request = requests.post("https://login.microsoftonline.com/" + MS_TenantID + "/oauth2/v2.0/token", data=token_request_data)
        if token_request.ok:
            token = token_request.json()
            MS_RefreshToken = token["refresh_token"]
            await MS_SaveRefreshToken()
            return token["access_token"]
        else:
            token_request_error = token_request.json()["error"]
            if token_request_error == "authorization_pending":
                continue
            else:
                raise Exception(token_request_error)
    raise Exception("Timed out waiting for device authorization.")
async def MS_GetAccessToken():
    global MS_RefreshToken

    try:
        if MS_RefreshToken == None:
            await MS_LoadRefreshToken()

        token_request_data = {
            "grant_type": "refresh_token",
            "client_id": MS_ClientID,
            "refresh_token": MS_RefreshToken,
            "scope": MS_Scopes,
        }
        token_request = requests.post("https://login.microsoftonline.com/" + MS_TenantID + "/oauth2/v2.0/token", data=token_request_data)
        token_request.raise_for_status()
        token = token_request.json()

        MS_RefreshToken = token["refresh_token"]
        await MS_SaveRefreshToken()
        return token["access_token"]
    except:
        return await MS_DoManualAuthFlow()
async def MS_EmailFromToken(access_token):
    token_body = access_token.split(".")[1]
    token_body += "=" * (-len(token_body) % 4)
    token_json = base64.urlsafe_b64decode(token_body).decode("utf-8")
    token_object = json.loads(token_json)
    return token_object["upn"]
async def MS_SendEmail(to, subject, body):
    access_token = await MS_GetAccessToken()
    from_address = await MS_EmailFromToken(access_token)
    headers = { "Authorization": f"Bearer {access_token}", "Accept": "application/json", "Content-type": "application/json" }
    request = {
        "message": {
            "subject": subject,
            "body": { "contentType": "HTML", "content": body },
            "toRecipients": [ { "emailAddress": { "address": to } } ]
        },
        "saveToSentItems": "false"
    }
    response = requests.post(f"https://graph.microsoft.com/v1.0/users/{from_address}/sendMail", json=request, headers=headers)
    response.raise_for_status()
async def hi():
    email = (await IO_ReadFile("./email/email.html")).replace("##CODE##", str(123456))
    await MS_SendEmail("christj@oregonstate.edu", f"{123456} - ONIDBot Verification Code", email)
asyncio.run(hi())
# InitTasks.append(MS_LoadRefreshToken)
# endregion

codes = {}
async def GetRandomCode():
    while True:
        rand_int = int.from_bytes(secrets.token_bytes(3)) & 0x0FFFFF
        if rand_int > 999999:
            continue
        return f"{rand_int:06d}"

# region Discord
discord_client = None
discord_command_tree = None
class ButtonsView(discord.ui.View):
    async def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Get Verification Code!", style=discord.ButtonStyle.primary, emoji="\U00000031\U0000fe0f\U000020e3", custom_id="get_code_button")
    async def get_code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(OnidInputModal())
        except BaseException as ex:
            Log_Exception(ex)
    @discord.ui.button(label="Enter Verification Code!", style=discord.ButtonStyle.primary, emoji="\U00000032\U0000fe0f\U000020e3", custom_id="enter_code_button")
    async def enter_code_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(CodeInputModal())
        except BaseException as ex:
            Log_Exception(ex)
class OnidInputModal(discord.ui.Modal):
    async def __init__(self):
        super().__init__(title="ONID Email Address", custom_id="onid_input_modal", timeout=None)
    onid_input = discord.ui.TextInput(label="Enter your ONID email address:", placeholder="onid@oregonstate.edu", required=True, custom_id="onid_text_input")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            onid_email = str(self.onid_input.value).strip().lower()
            if not onid_email.endswith("@oregonstate.edu") or len(onid_email) <= len("@oregonstate.edu"):
                await interaction.followup.send(f"The ONID you entered doesn't look quite right. Please try again.", ephemeral=True, wait=True)
                return
            onid_name = await OSU_LookupOnidNameAsync(onid_email)
            if onid_name == None:
                await interaction.followup.send(f"The ONID you entered doesn't look quite right. Please try again.", ephemeral=True, wait=True)
                return            
            code = GetRandomCode()
            codes[interaction.user.id] = { "time": IO_GetEpoch(), "code": code, "onid_email": onid_email, "onid_name": onid_name }
            Log_Info(f"Created code {code} for {interaction.user.mention} {interaction.user.id} on {interaction.guild.name} {interaction.guild.id} for {onid_name} {onid_email}")
            
            await discord_client.application.owner.send(f"{discord_client.application.owner.mention} YO MAMA SO FAT")

            email = IO_ReadFile("./email/email.html").replace("##CODE##", str(code))
            await MS_SendEmailAsync(onid_email, f"{code} - ONIDBot Verification Code", email)
            await interaction.followup.send(f"A verification code has been sent to {onid_email}.\n\nPlease allow up to 15 minutes for the code to arive, and **check spam.**", ephemeral=True, wait=True)
        except BaseException as ex:
            Log_Exception(ex)
class CodeInputModal(discord.ui.Modal):
    async def __init__(self):
        super().__init__(title="Verification Code", custom_id="code_input_modal", timeout=None)
    onid_input = discord.ui.TextInput(label="Enter your verification code:", placeholder="123456", required=True, custom_id="code_text_input")
    async def on_submit(self, interaction: discord.Interaction):
        try:
            code = str(self.onid_input.value).strip()

            if not len(code) == 6 or not code.isdigit():
                await interaction.response.send_message(f"The code you entered doesn't look quite right. Please try again.", ephemeral=True)
                return

            # TODO finish this
            code_obj = Code_ParseAndVerify(code)
            discord_id = code_obj["discord_id"]
            onid_email = code_obj["onid_email"]

            if not WatchDogInGoodStanding(discord_id):
                return f"TOO MANY REQUESTS! Please wait 24 hours."
            WatchDogPunish(discord_id)

            DB_Set(discord_id, onid_email)

            discord_server_obj = discord_client.get_guild(ENV["discord_server_id"])
            if discord_server_obj is None:
                discord_server_obj = await discord_client.fetch_guild(ENV["discord_server_id"])

            discord_user_obj = discord_server_obj.get_member(discord_id)
            if discord_user_obj is None:
                discord_user_obj = await discord_server_obj.fetch_member(discord_id)

            await discord_user_obj.add_roles(discord_verified_role)
            await discord_user_obj.remove_roles(discord_unverified_role)
            onid_name = await OSU_LookupOnidNameAsync(onid_email)
            if onid_name == None:
                print(f"Failed to lookup onid name for {onid_email}.")
            else:
                try:
                    await discord_user_obj.edit(nick=onid_name)
                except:
                    print(f"Failed to nick {discord_id}.")

            return f"Success your Discord account (@{discord_user_obj.name}) has been linked with your ONID email ({onid_email}).<br />You may now close this tab and return to Discord."
        except BaseException as ex:
            Log_Exception(ex)
async def DC_InitClient():
    global discord_client
    global discord_command_tree
    discord_intents = discord.Intents.default()
    discord_intents.members = True
    discord_client = discord.Client(intents=discord_intents)
    discord_command_tree = discord.app_commands.CommandTree(discord_client)
    @discord_client.event
    async def on_ready():
        try:
            for init_task in InitTasks:
                init_task()
            await discord_command_tree.sync()
            discord_client.add_view(ButtonsView())
            await discord_client.change_presence(activity=discord.CustomActivity("Verifying ONID email addresses..."), status=discord.Status.online)
            Log_Info(f"Online as {discord_client.user}")
        except BaseException as ex:
            Log_Exception(ex)
    @discord_client.event
    async def on_member_join(member):
        try:
            # TODO finish this
            pass
        except BaseException as ex:
            Log_Exception(ex)
    @discord_command_tree.command(name="post_verification_buttons", description="Posts the get verified button to the current channel.")
    async def instructions(interaction: discord.Interaction):
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need the administrator permission to run this command.", ephemeral=True)
                return
            await interaction.channel.send("", view=ButtonsView())
            await interaction.response.send_message("Done!", ephemeral=True)
        except BaseException as ex:
            Log_Exception(ex)
    @discord_command_tree.command(name="get_verification_info", description="Posts a bunch of debug information on a target user just for you.")
    async def get_user_info(interaction: discord.Interaction, user: discord.Member):
        try:
            if not interaction.user.is_verified:
                await interaction.response.send_message("You must be verified by ONIDBot to run this command.", ephemeral=True)
                return
            user_id = str(user.id)
            user_mention = user.mention
            verified_role = any([ role.id == discord_verified_role.id for role in user.roles ])
            unverified_role = any([ role.id == discord_unverified_role.id for role in user.roles ])
            onid_email = DB_Get(user_id)
            onid_name = None if onid_email == None else await OSU_LookupOnidNameAsync(onid_email)
            watchdog_requests = WatchDogQuery(user_id)
            await interaction.response.send_message(f"User: {user_mention}\nUser ID: {user_id}\nVerified Role: {verified_role}\nUnverified Role: {unverified_role}\nONID: {onid_email}\nONID Name: {onid_name}\nWatchDog Requests: {watchdog_requests}", ephemeral=True)
        except BaseException as ex:
            Log_Exception(ex)
InitTasks.append(DC_InitClient)
# endregion

# region Main
async def Main():
    try:
        discord_client.run(ENV["discord_token"])
        return 0
    except BaseException as ex:
        Log_Exception(ex)
        return 1
sys.exit(Main())
# endregion