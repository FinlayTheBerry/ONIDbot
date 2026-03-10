#!/usr/bin/python3
import json
import requests
import sys

TOKEN = None
def GetToken():
	CLIENT_ID = "RSnRfTuLQNPrd8QeHg6CC72cCSOB1JfN"
	CLIENT_SECRET = "AOLOLydsRXZfHMyC"
	global TOKEN
	if TOKEN == None:
		response = requests.post("https://api.oregonstate.edu/oauth2/token", data={"grant_type": "client_credentials"}, auth=(CLIENT_ID, CLIENT_SECRET))
		response.raise_for_status()
		TOKEN = response.json()["access_token"]
	return TOKEN

def API_ByOnid(onid):
	headers = { "Authorization": f"Bearer {GetToken()}", "Accept": "application/json" }
	response = requests.get(f"https://api.oregonstate.edu/v2/directory?filter[onid]={onid}", headers=headers)
	response.raise_for_status()
	return response.json()
def API_ByOsuuid(osuuid):
	headers = { "Authorization": f"Bearer {GetToken()}", "Accept": "application/json" }
	response = requests.get(f"https://api.oregonstate.edu/v2/directory/{osuuid}", headers=headers)
	response.raise_for_status()
	return response.json()

def ByOnid(args):
	if len(args) != 1:
		print("Action byonid takes one arg.")
		print("ACTION: osuapi byonid onid")
		return 1
	print(json.dumps(API_ByOnid(args[0]), indent=4))
	return 0
def ByOsuuid(args):
	if len(args) != 1:
		print("Action byosuuid takes one arg.")
		print("ACTION: osuapi byosuuid osuuid")
		return 1
	print(json.dumps(API_ByOsuuid(args[0]), indent=4))
	return 0
def Help(args):
	print("USAGE: osuapi [action] (arguments...)")
	print()
	print("ACTION: osuapi --help")
	print("ACTION: osuapi byonid onid")
	print("ACTION: osuapi byosuuid osuuid")
	return 0

def Main():
	if len(sys.argv) < 2:
		print(f"No action provided. Try osuapi --help")
		return 1

	action = sys.argv[1]
	args = sys.argv[2:]
	if action == "--help":
		return Help(args)
	elif action == "byonid":
		return ByOnid(args)
	elif action == "byosuuid":
		return ByOsuuid(args)
	else:
		print(f"Unknown action {action}. Try osuapi --help")
		return 1
sys.exit(Main())