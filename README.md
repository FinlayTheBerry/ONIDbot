# WHAT IS ONIDbot?
🛡️ ONIDbot is a free and [open-source](https://github.com/FinlayTheBerry/ONIDbot) Discord bot that verifies your server's members using their [onid@oregonstate.edu](https://onid.oregonstate.edu) email addresses.  
👨‍💻 ONIDbot was developed by Finlay Christ, a Cybersecurity major and President of the OSU Rock Climbing Club.  
🗓️ ONIDbot has been protecting the OSU Rock Climbing Club's Discord server since 9/26/2025.  
📈 ONIDbot has verified over 144 students and has blocked dozens of scams.  

# WHY USE ONIDbot?
Posting your club's Discord server invite to social media is a great way to grow your community, but as soon as that link becomes public, anyone can join. Even the links you post on IdealLogic are public! OSU specifically has seen a massive increase in scammers, and these scams have real victims. ONIDbot helps keep your community safe by restricting access to non-students.  

# HOW DOES ONIDbot WORK?
ONIDbot is designed to integrate easily with your server's existing roles and permissions.  

- You post the ONIDbot verification button on your server.  
- When a new member presses that button, a popup will appear asking for their ONID email address.  
- ONIDbot will then send a 6-digit verification code to their inbox.  
- After the member inputs that code, ONIDbot searches your server for a role named "ONID-Verified" and assigns it to the newly verified member.  
- ONIDbot will also look up their ONID in the OSU directory and change their nickname on your server to their real name.  

Members who have already verified with ONIDbot on another server can instantly verify on your server with just one click. You have complete control over which permissions are given to `@everyone` and which are reserved for verified members. Using the `/get_verification_info` command, you can get the ONID email and full name of any verified member in your server.  

# ONIDbot SETUP:

### 1️⃣ Adding The Bot/Permissions:
Adding ONIDbot to your server is easy.  
Just [click here](https://discord.com/oauth2/authorize?client_id=1487624623129497641) and follow Discord's instructions to add ONIDbot to your club's server.  
ONIDbot asks for three permissions, each of which is essential for the bot to function correctly:  
- Manage Roles: Required to give members the "ONID-Verified" role after completing verification.  
- Manage Nicknames: Allows the bot to change each member's nickname to their full name after verification.  
- Send Messages: Required to post the verification buttons so members can click them.  

### 2️⃣ Roles Setup:
Next, you will need to create a role that is given to verified members.  
Go to Server Settings > Roles and press Create Role.  
Name the role exactly "ONID-Verified" and give that role the following permissions:  
View Channels, Send Messages and Create Posts, Read Message History, Connect, Speak, and Use Voice Activity.  
Then go to @everyone and press "Clear permissions" to remove all permissions.  

### 3️⃣ Get-Verified Channel Setup:
Next create a new channel called get-verified.  
Go to Edit Channel > Permissions and set the following:  
@everyone is granted View Channel, and Read Message History  
@ONIDbot is granted Send Messages  
@ONID-Verified is denied Send Messages  
Finally type "/post_verification_buttons" in the get-verified channel to post the buttons.
ONIDbot is now setup and verifying members!

# 🔒 PRIVACY STATEMENT
ONIDbot was designed by Finlay Christ and is a seperate entity from Oregon State University (OSU).  
ONIDbot runs on servers which are controlled by OSU and as such it is possible for OSU staff to access ONIDbot's data.  
ONIDbot stores the following information about you after verification: your onid email address, your full name, your Discord user ID.  
ONIDbot collects logs which contain the following: onid email addresses, full names, Discord usernames, Discord user IDs, Discord server names, Discord server IDs.  
ONIDbot asks for only the bare minimum set of permissions required to function on your server.  
ONIDbot will NEVER read messages on your server.  
You can request the deletion of your data in ONIDbot at any time by emailing [christj@oregonstate.edu](mailto:christj@oregonstate.edu).