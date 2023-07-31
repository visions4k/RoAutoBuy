import discord
import os
import json
import asyncio
import requests
import datetime
from discord.ext import commands
from datetime import timedelta
from dateutil.parser import isoparse
from discord import Game

TOKEN = 'TOKEN HERE'

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='-', intents=intents)

def check_purchase_id(purchase_id):
    with open("usedbuys.txt", "r") as file:
        used_buys = file.read().splitlines()
        return purchase_id in used_buys
    
def get_user_id(username):
    url = 'https://users.roblox.com/v1/usernames/users'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        'usernames': [username],
        'excludeBannedUsers': True
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            user_data = data["data"][0]
            if "id" in user_data:
                return str(user_data["id"])
            print(user_data["id"])
    return None

@client.command()
async def purchase(ctx, *, package_name: str = None):
    guild_id = str(ctx.guild.id)
    guild_config_path = f'config/{guild_id}'

    if os.path.exists(guild_config_path):
        config_file = os.path.join(guild_config_path, 'config.json')

        if os.path.isfile(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            admin_role = config_data["admin_role"]
            purchase_channel_id = config_data["purchase_channel_id"]
            logs_channel_id = config_data["logs_channel_id"]
            package_roles = config_data["package_roles"]
            roblox_cookie = config_data["roblox_cookie"]
            currentguild = config_data["guild_id"]

    if ctx.channel.id != purchase_channel_id:
        embed_channel = discord.Embed(
            title="Wrong Channel",
            description=f"Visit <#{purchase_channel_id}>",
            color=discord.Color.blue()
        )
        channelv_message = await ctx.send(embed=embed_channel)

        async def delete_message():
            await asyncio.sleep(7)
            await ctx.message.delete()
            await channelv_message.delete()

        asyncio.create_task(delete_message())
        return

    logs_channel = client.get_channel(logs_channel_id)
    log_message = discord.Embed(
        title="Purchase Command",
        description=f"Purchase command used\nUser: `{ctx.author.name}#{ctx.author.discriminator}`\nOption: `{package.name}`",
        color=discord.Color.orange()
    )
    await logs_channel.send(embed=log_message)

    package_name_lower = package_name.lower() if package_name else None
    package = next(
        (pkg for pkg in package_roles.values() if pkg['name'].lower() == package_name_lower), None
    )

    if not package:
        available_packages = "\n".join(f"-purchase {pkg['name']}" for pkg in package_roles.values())

        embed = discord.Embed(
            title="Invalid",
            description=f"Not available. Please use one of the following packages-\n{available_packages}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    url = package["url"]
    embed_channel = discord.Embed(
        title="DM Sent",
        description=f"{ctx.author.mention} | Please check your DMs to upgrade.\nIf you did not receive a DM, make sure DMs are on.\nAny problems please make a ticket.",
        color=discord.Color.blue()
    )
    channel_message = await ctx.send(embed=embed_channel)
    await ctx.message.delete()

    async def delete_message():
        await asyncio.sleep(10)
        await channel_message.delete()

    asyncio.create_task(delete_message())

    embed = discord.Embed(
        title="Click to purchase the gamepass!",
        url=url,
        description="**YOUR INVENTORY MUST BE SET PUBLIC**\nOnce purchased - please send your **roblox username**\n\nIf you make a mistake typing the username, run the command again!\nAny other problems contact contact support.\n**+ you have 5 minutes to type in a roblox username\n+ all attempts are logged**",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Autobuy provided by RoServices!", icon_url="https://cdn.discordapp.com/attachments/1112122690086649916/1121229779430023270/RoBLX_Logo.png")
    await ctx.author.send(embed=embed)

    def check(message):
        return message.author == ctx.author and message.channel == ctx.author.dm_channel

    try:
        message = await client.wait_for("message", check=check, timeout=300)
        response = message.content.strip()

        embed = discord.Embed(
            title="Username Received!",
            description=f"**Username you typed:** {response}\nPlease wait a moment...",
            color=discord.Color.blurple()
        )
        await ctx.author.send(embed=embed)

        roblox_username = response
        await asyncio.sleep(2)

        roblox_id = get_user_id(roblox_username)
        if roblox_id is None:
            embed = discord.Embed(
                title="Username Not Found",
                description=f"**Did not find username:** {roblox_username} \nDouble-check the username, if you still have troubles, please make a ticket!",
                color=discord.Color.red()
            )
            logs_channel = client.get_channel(logs_channel_id)
            log_message = discord.Embed(
                title="Username not found",
                description=f"Username not found\nUser: `{ctx.author.name}#{ctx.author.discriminator}`\nRBX Username: `{roblox_username}`",
                color=discord.Color.red()
            )
            await logs_channel.send(embed=log_message)
            await ctx.author.send(embed=embed)
            return

        embed = discord.Embed(
            title="User Found!",
            description=f"**Username:** {roblox_username}\n**UserID:** {roblox_id}\nPlease wait a moment...",
            color=discord.Color.blurple()
        )
        await ctx.author.send(embed=embed)

        package_input = package_name.lower()
        asset_id = None  

        for package_key, package in package_roles.items():
            if package_input == package["name"].lower():
                asset_id = package["value"]
                break

        if asset_id:

            url = f"https://inventory.roblox.com/v2/assets/{asset_id}/owners?limit=10&sortOrder=Desc"

            headers = {
                "Cookie": f".ROBLOSECURITY={roblox_cookie}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.9999.999 Safari/537.36"
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                owners = data["data"]

                if owners:
                    user_found = False

                    for sale in owners[:3]: #checks 3 recent sales
                        owner = sale.get("owner")

                        if owner and "id" in owner:
                            owner_id = owner["id"]
                            if roblox_id == str(owner_id):
                                purchase_id = str(sale.get("id"))
                                if check_purchase_id(purchase_id):
                                    logs_channel = client.get_channel(logs_channel_id)
                                    notifymessage = f"<@&{admin_role}>"
                                    await logs_channel.send(notifymessage)
                                    log_message = discord.Embed(
                                        title="BYPASS DETECTED",
                                        description=f"**BYPASS DETECTED**\nDiscord User: `{ctx.author.name}#{ctx.author.discriminator}`\nUsername: `{roblox_username}`\nUserID: `{roblox_id}`\nPurchaseID: `{purchase_id}`",
                                        color=discord.Color.red()
                                    )
                                    await logs_channel.send(embed=log_message)
                                    embed = discord.Embed(
                                        title="**Bypass detected**",
                                        description=f"The purchase ID `{purchase_id}` has **already been used**. This has been logged and the staff team has been notified.\nIf a mistake occurred, please make a ticket!",
                                        color=discord.Color.red()
                                    )
                                    await ctx.author.send(embed=embed)
                                    return
                                else:
                                    with open("usedbuys.txt", "a") as file:
                                        file.write(purchase_id + "\n")
                                user_found = True
                                break 

                    if user_found:
                        guild = client.get_guild(currentguild)
                        member = await guild.fetch_member(ctx.author.id)

                        logs_channel = client.get_channel(logs_channel_id)
                        notifymessage = f"<@&{admin_role}>"
                        await logs_channel.send(notifymessage)
                        log_message = discord.Embed(
                            title="Successful Sale",
                            description=f"CHECK SALES | **Successful sale**\nDiscord User: `{ctx.author.name}#{ctx.author.discriminator}`\nRBX Username: `{roblox_username}`\nUserID: `{roblox_id}`\nPurchaseID: `{purchase_id}`",
                            color=discord.Color.green()
                        )
                        await logs_channel.send(embed=log_message)
                        guild_id = currentguild
                        guildname = client.get_guild(guild_id)
                        embed = discord.Embed(title=f"Successful sale!", color=discord.Color.green())
                        embed.add_field(name="Server:", value=f"`{guildname}`", inline=True)
                        embed.add_field(name="User:", value=f"`{ctx.author.name}#{ctx.author.discriminator}`", inline=True)
                        embed.set_footer(text="RoAutoBuy", icon_url='https://cdn.discordapp.com/attachments/1112122690086649916/1121229779430023270/RoBLX_Logo.png')
                        channelc_id = 1121536843742195764
                        channelc = client.get_channel(channelc_id)
                        await channelc.send(embed=embed)
                    
                        role_id = int(package['role_id'])
                        role = guild.get_role(role_id)
                        await member.add_roles(role)

                        embed = discord.Embed(
                            title="Sale Found!",
                            description=f"**Username:** {roblox_username}\n**UserID:** {roblox_id}\nYou should have now received the role!",
                            color=discord.Color.green()
                        )
                        await ctx.author.send(embed=embed)
                    else:
                        embed = discord.Embed(
                            title="Error",
                            description="**Inventory is private or username is wrong! Please redo the command.** \nIf you're still having troubles, please make a ticket!",
                            color=discord.Color.red()
                        )
                        logs_channel = client.get_channel(logs_channel_id)
                        log_message = discord.Embed(
                            title="Sale Not Found",
                            description=f"Username wrong / inventory private\nUser:`{ctx.author.name}#{ctx.author.discriminator}`\nRBX Username: `{roblox_username}`\nUserID: `{roblox_id}`",
                            color=discord.Color.red()
                        )
                        await logs_channel.send(embed=log_message)
                        await ctx.author.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="Error",
                        description="**Failed to fetch sales; please make a ticket!**",
                        color=discord.Color.red()
                    )
                    logs_channel = client.get_channel(logs_channel_id)
                    log_message = f"@everyone | DM VISIONS: Failed to fetch sales **{ctx.author.name}#{ctx.author.discriminator}** (Username: {roblox_username}, UserID: {roblox_id})"
                    await logs_channel.send(log_message)
                    await ctx.author.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Error",
                    description="**Failed to fetch sales; please make a ticket!**",
                    color=discord.Color.red()
                )
                logs_channel = client.get_channel(logs_channel_id)
                log_message = f"Failed to fetch sales <@&{admin_role}> | DM OWNER USER: {ctx.author.name}#{ctx.author.discriminator} (Username: {roblox_username}, UserID: {roblox_id})"
                await logs_channel.send(log_message)
                await ctx.author.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Invalid Package",
                description="The specified package is not available. Please try again.",
                color=discord.Color.red()
            )
            await ctx.author.send(embed=embed)

    except asyncio.TimeoutError:
        embed = discord.Embed(
            title="Timeout",
            description="You took too long to respond. Please run the command again.",
            color=discord.Color.red()
        )
        await ctx.author.send(embed=embed)
        logs_channel = client.get_channel(logs_channel_id)
        log_message = discord.Embed(
            title="Timeout",
            description=f"User took too long to respond\nUser: `{ctx.author.name}#{ctx.author.discriminator}`",
            color=discord.Color.orange()
        )
        await logs_channel.send(embed=log_message)
        
@client.command()
async def h(ctx):
    guild_id = str(ctx.guild.id)
    guild_config_path = f'config/{guild_id}'

    if os.path.exists(guild_config_path):
        config_file = os.path.join(guild_config_path, 'config.json')

        if os.path.isfile(config_file):
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            admin_role = config_data["admin_role"]
            purchase_channel_id = config_data["purchase_channel_id"]
            logs_channel_id = config_data["logs_channel_id"]
            package_roles = config_data["package_roles"]
            roblox_cookie = config_data["roblox_cookie"]
            currentguild = config_data["guild_id"]
            available_packages = "\n".join(f"-purchase {pkg['name']}" for pkg in package_roles.values())

        embed = discord.Embed(
            title="Click for support discord",
            url="https://discord.gg/uQDRhaxnyr",
            description=f"Configuration loaded for `{ctx.guild.name}`",
            color=discord.Color.green()
        )
        embed.add_field(name="-h", value=f"Provides this page", inline=False)
        embed.add_field(name="-info", value=f"Shows information about RoAutoBuy, and RoServices", inline=False)
        embed.add_field(name="-purchase", value=f"Sends all available packages to purchase for the server.", inline=False)
        embed.add_field(name="-purchase <package>", value=f"Sends instructions to DMs for the chosen package.", inline=False)
        embed.add_field(name="**Servers configuration settings-**", value=f"Purchase CMD Channel: <#{purchase_channel_id}>\n**All Avaliable packages-**\n{available_packages}", inline=True)
        embed.set_footer(text = "RoServices", icon_url = 'https://cdn.discordapp.com/attachments/1112122690086649916/1121229779430023270/RoBLX_Logo.png')
        await ctx.send(embed=embed)
    
    return


        
@client.command()
async def info(ctx):
    embed = discord.Embed(title="Click for RoServices!", description="**RoAutoBuy Statistics**", color=discord.Color.green())
    embed.url = "https://discord.gg/uQDRhaxnyr"
    guild_count = len(client.guilds)
    member_count = sum(guild.member_count for guild in client.guilds)
    embed.add_field(name="Server Count", value="`{}`".format(guild_count), inline=True)
    embed.add_field(name="Total Members", value="`{}`".format(member_count), inline=True)
    embed.add_field(name="Provided by", value="`RoServices`", inline=False)
    embed.add_field(name="Created by", value="`visions4k`", inline=True)
    embed.set_footer(text = "RoServices", icon_url = 'https://cdn.discordapp.com/attachments/1112122690086649916/1121229779430023270/RoBLX_Logo.png')
    await ctx.send(embed=embed)
        
        
@client.event
async def on_guild_join(guild):
    embed = discord.Embed(title=f"Invited to `{guild.name}`!", color=discord.Color.blue())
    embed.add_field(name="Guild ID:", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="Total Members:", value=f"`{guild.member_count}`", inline=True)
    embed.set_footer(text="RoServices", icon_url='https://cdn.discordapp.com/attachments/1112122690086649916/1121229779430023270/RoBLX_Logo.png')
    channel_id = LOG_CHANNEL
    channel = client.get_channel(channel_id)
    await channel.send(embed=embed)
    
    
@client.event
async def on_ready():
    client.remove_command("help")
    guild_count = len(client.guilds)
    member_count = sum(guild.member_count for guild in client.guilds)
            
    embed = discord.Embed(title=f"Restart", description="Restarted Successfully!", color=discord.Color.green())
    embed.add_field(name="Guilds:", value="`{}`".format(guild_count), inline=True)
    embed.add_field(name="Total Members:", value="`{}`".format(member_count), inline=True)
    embed.set_footer(text="RoAutoBuy", icon_url='https://cdn.discordapp.com/attachments/1112122690086649916/1121229779430023270/RoBLX_Logo.png')
            
    channelc_id = LOG_CHANNEL
    channelc = client.get_channel(channelc_id)
    await channelc.send(embed=embed)
    async def update_presence():
        while True:
            guild_count = len(client.guilds)
            member_count = sum(guild.member_count for guild in client.guilds)
            
            statuses = [
                f"{member_count} Members",
                f"{guild_count} Servers",
                "-h for help | RoServices"
            ]
            
            for status in statuses:
                await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))
                await asyncio.sleep(30)
        
    asyncio.create_task(update_presence())
    print('ready')

    

    
client.run(TOKEN)


