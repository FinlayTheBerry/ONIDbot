# What is ONIDbot?
ONIDbot is a free and [open source](https://github.com/FinlayTheBerry/onid_bot) Discord bot which can be added to any server for free.  
It was developed by me (Finlay Christ). I'm a cybersecurity major at Oregon State University.  
ONIDbot is designed to collect and verify the @OregonState.edu email addresses of your server's members.  
You have full control over which permissions are granted to everyone and which require ONID verification.  

# Why do I even need ONIDbot?
As soon as a Discord server invite link gets posted on social media that server becomes a public space.  
People from around the world can join regardless of student status or intentions.  
Even the links you post on IdealLogic are public!  
While banning a single account is easy, creating alt accounts to bypass a ban is equally easy.  
With ONIDbot you can hold users accountable for their actions by requiring their ONID email which is linked to their full name and student records.  

# Addinging The Bot/Permissions:
Adding ONIDbot to your server is easy.  
Just [click here](https://discord.com/oauth2/authorize?client_id=1344219132027076629) and follow Discord's instructions to add ONIDbot to your club's server.  
ONIDbot asks for 3 permissions, each of which is essential for the bot to function correctly.  
Manage Roles is required in order to give members the ONID-Verified role after completing verification.  
Manage Nicknames is optional and allows the bot to change each member's nickname to their full name after verification.  
Send Messages is required to post the verification buttons on your server so members can click them.  

# Roles Setup:
Next you will need to create a role which is given to verified members.  
Go to Server Settings > Roles and press Create Role.  
Name the role exactly "ONID-Verified" and give that role the following permissions:  
View Channels, Send Messages and Create Posts, Read Message History, Connect, Speak, Use Voice Activity.  
Then go to @everyone and press "Clear permissions" to remove all permissions.  

# Get Verified Channel Setup:
Next create a new channel called get-verified.  
Go to Edit Channel > Permissions and set the following:  
@everyone is granted View Channel, and Read Message History  
@ONIDbot is granted Send Messages  
@ONID-Verified is denied Send Messages  
Finally run "/post_verification_buttons" to post buttons in the get-verified channel.  

# Final Checks
Setup should be complete but I recommend going through the verification process on an alt account.  
To ensure you have access to everything you need and don't have access to anything you shouldn't.  