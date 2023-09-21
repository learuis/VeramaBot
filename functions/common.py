import discord
import re
import time
import requests
import os


from discord.ext.commands.cooldowns import BucketType
from functions.externalConnections import runRcon
import sqlite3

from time import strftime

from dotenv import load_dotenv

load_dotenv('data/server.env')
QUERY_URL = os.getenv('QUERY_URL')
BOT_CHANNEL = int(os.getenv('BOT_CHANNEL'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))
BOON_CHANNEL = int(os.getenv('BOON_CHANNEL'))
OWNER_USER_ID = int(os.getenv('OWNER_USER_ID'))

def custom_cooldown(ctx):
    whitelist = {'Admin', 'Moderator'}
    roles = {role.name for role in ctx.author.roles}
    if not whitelist.isdisjoint(roles):
        #if we're a special role, no cooldown assigned
        return None
    else:
        #everyone else
        return discord.app_commands.Cooldown(5, 60)

def checkChannel(ctx):
    if ctx.author.id == OWNER_USER_ID:
        return True
    execTime = time.strftime('%c')
    print(f'Command {ctx.command} executed by {ctx.author} on {execTime}')
    channelList = [BOT_CHANNEL, OUTCASTBOT_CHANNEL]
    return ctx.channel.id in channelList

def isInt(intToCheck):
    try:
        int(intToCheck)
    except ValueError:
        return False
    else:
        return True

def ununicode(string):
    output = re.sub(r'[^\x00-\x7F]', '?', string)
    output = output.replace('??', '?')
    return output

def percentage(int1, int2):
    ratio = (int1 / int2) * 100
    ratio = round(ratio)
    return ratio

def is_docker():
    path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(path) and any('docker' in line for line in open(path))
    )

def get_member_from_userid(ctx, user_id: int):
    return ctx.guild.get_member(user_id)

def get_character_id(name: str):
    response = runRcon(f'sql select id, char_name from characters where char_name = \'{name}\'')
    response.output.pop(0)

    if response.output:
        for x in response.output:
            print(x)
            match = re.findall(r'\s+\d+ | [^|]*', x)
            return match[0]
    else:
        return None

def popup_to_player(charName: str, message: str):
    rconId = get_rcon_id(charName)
    rconResponse = runRcon(f'con {rconId} PlayerMessage \"{charName}\" \"{message}\"')
    print(rconResponse.output)
    print(f'PlayerMessage \"{charName}\" \"{message}\"')

def get_rcon_id(name: str):
    connected_chars = []

    rconResponse = runRcon('listplayers')
    rconResponse.output.pop(0)

    for x in rconResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', x)
        connected_chars.append(match)
        print(connected_chars)

    if not connected_chars:
        return False

    for x in connected_chars:
        if name.casefold() in x[1].casefold():
            return x[0].strip()

def update_registered_name(input_user, name):
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'update registration set character_name = \'{name}\' where discord_user = \'{input_user}\'')
    con.commit()
    con.close()

def is_registered(discord_id: int):
    class Registration:
        def __init__(self):
            self.id = 0
            self.char_name = ''

    returnValue = Registration()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'select game_char_id, character_name from registration where discord_user = \'{discord_id}\'')
    result = cur.fetchone()

    con.close()

    if result:
        returnValue.id = result[0]
        returnValue.char_name = result[1]
        return returnValue
    else:
        return False

def get_registration(char_name):

    returnList = []
    char_name = str(char_name).casefold()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'select game_char_id, character_name, discord_user from registration where character_name like '
                f'\'%{char_name}%\'')
    results = cur.fetchall()

    con.close()

    if results:
        for result in results:
            returnList.append(result)
        return returnList
    else:
        return False

def get_single_registration(char_name):

    char_name = str(char_name).casefold()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'select game_char_id, character_name, discord_user from registration where character_name like '
                f'\'%{char_name}%\' limit 1')
    results = cur.fetchone()

    con.close()

    if results:
        return results
    else:
        return False

async def editStatus(message, bot):
    currentTime = strftime('%A %m/%d/%y at %I:%M %p', time.localtime())

    response = requests.get(QUERY_URL).json()
    ipAddress = response.get('ipAddress')
    onlineStatus = response.get('online')
    currentPlayers = response.get('currentPlayers')
    maxPlayers = response.get('maxPlayers')

    if onlineStatus == 'False':
        statusSymbol = '<:redtick:1152409914430455839>'
        await bot.change_presence(activity=discord.Activity(name=f'-/{maxPlayers} OFFLINE', type=3))
    else:
        statusSymbol = '🔧'
        await bot.change_presence(activity=discord.Activity(name=f'MAINTENANCE', type=3))
        #statusSymbol = '<:greentick:1152409721966432376>'
        #await bot.change_presence(activity=discord.Activity(name=f'{currentPlayers}/{maxPlayers} ONLINE', type=3))

    onlineSymbol = ':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    if int(currentPlayers) == 30:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::orange_circle::orange_circle:'
    if int(currentPlayers) < 30:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::orange_circle::blue_circle:'
    if int(currentPlayers) < 24:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 18:
        onlineSymbol = f':orange_circle::orange_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 12:
        onlineSymbol = f':orange_circle::blue_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 6:
        onlineSymbol = f':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    await message.edit(content=f'**Band of Outcasts Server Status**\n'
                               f'__{currentTime}__\n'
                               f'- IP Address: {ipAddress}:32200\n'
                               f'-- {statusSymbol} MAINTENANCE {statusSymbol} --\n'
                               f'Season 4 begins at 3pm EST!')
    """
    await message.edit(content=f'**Band of Outcasts Server Status**\n'
                               f'__{currentTime}__\n'
                               f'- IP Address: {ipAddress}:32200\n'
                               f'- Server Online: {onlineStatus} {statusSymbol}\n'
                               f'- Players Connected: {currentPlayers} / {maxPlayers} {onlineSymbol}\n'
                               f'Server restarts are at 8:00am and 2:45pm Eastern')
    """
