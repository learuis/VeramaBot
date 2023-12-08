import discord
import re
import time
import requests
import os
import sqlite3
import io

from functions.externalConnections import runRcon
from time import strftime
from dotenv import load_dotenv
from datetime import datetime

load_dotenv('data/server.env')
QUERY_URL = os.getenv('QUERY_URL')
BOT_CHANNEL = int(os.getenv('BOT_CHANNEL'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))
BOON_CHANNEL = int(os.getenv('BOON_CHANNEL'))
OWNER_USER_ID = int(os.getenv('OWNER_USER_ID'))
SERVER_PASSWORD = str(os.getenv('SERVER_PASSWORD'))
SERVER_NAME = str(os.getenv('SERVER_NAME'))
SERVER_PORT = int(os.getenv('SERVER_PORT'))

def custom_cooldown(ctx):
    whitelist = {'Admin', 'Moderator'}
    roles = {role.name for role in ctx.author.roles}
    if not whitelist.isdisjoint(roles):
        #if we're a special role, no cooldown assigned
        return None
    else:
        #everyone else
        return discord.app_commands.Cooldown(5, 60)

def modChannel(ctx):
    if ctx.author.id == OWNER_USER_ID:
        return True
    execTime = time.strftime('%c')
    print(f'Command {ctx.command} executed by {ctx.author} on {execTime} in {ctx.channel.name}')
    channelList = [BOT_CHANNEL, OUTCASTBOT_CHANNEL, BOON_CHANNEL]
    return ctx.channel.id in channelList

def publicChannel(ctx):
    if ctx.author.id == OWNER_USER_ID:
        return True
    execTime = time.strftime('%c')
    print(f'Command {ctx.command} executed by {ctx.author} on {execTime} in {ctx.channel.name}')
    channelList = [BOT_CHANNEL, OUTCASTBOT_CHANNEL, BOON_CHANNEL]
    return ctx.channel.id in channelList

def boonChannel(ctx):
    if ctx.author.id == OWNER_USER_ID:
        return True
    execTime = time.strftime('%c')
    print(f'Command {ctx.command} executed by {ctx.author} on {execTime} in {ctx.channel.name}')
    channelList = [BOT_CHANNEL, OUTCASTBOT_CHANNEL, BOON_CHANNEL]
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

def run_console_command_by_name(char_name: str, command: str):
    rcon_id = get_rcon_id(f'{char_name}')
    if not rcon_id:
        return False
    else:
        runRcon(f'con {rcon_id} {command}')
        return

async def editStatus(message, bot):
    currentTime = strftime('%A %m/%d/%y at %I:%M %p', time.localtime())

    try:
        response = requests.get(QUERY_URL).json()
    except Exception:
        print(f'Exception occurred.')
        return

    ipAddress = response.get('ipAddress')
    onlineStatus = response.get('online')
    currentPlayers = response.get('currentPlayers')
    maxPlayers = response.get('maxPlayers')

    if 'False' in str(onlineStatus):
        statusSymbol = '<:redtick:1152409914430455839>'
        await bot.change_presence(activity=discord.Activity(name=f'SERVER DOWN', type=3))
    else:
        if bot.maintenance_flag:
            statusSymbol = '🔧'
            await bot.change_presence(activity=discord.Activity(name=f'MAINTENANCE', type=3))
        else:
            statusSymbol = '<:greentick:1152409721966432376>'
            await bot.change_presence(activity=discord.Activity(
                name=f'{currentPlayers}/{maxPlayers} ONLINE', type=3))

    onlineSymbol = ':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    if int(currentPlayers) == 30:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::orange_circle::orange_circle::orange_circle:'
    if int(currentPlayers) < 30:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::orange_circle::orange_circle::blue_circle:'
    if int(currentPlayers) < 25:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::orange_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 20:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 15:
        onlineSymbol = f':orange_circle::orange_circle::blue_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 10:
        onlineSymbol = f':orange_circle::blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 5:
        onlineSymbol = f':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    if bot.maintenance_flag:
        await message.edit(content=f'**Server Status**\n'
                                   f'__{currentTime}__\n'
                                   f'- Server Name: `{SERVER_NAME}`\n'
                                   f'- IP Address:Port: `{ipAddress}:{SERVER_PORT}`\n'
                                   f'- Password: {SERVER_PASSWORD}\n'
                                   f'-- {statusSymbol} MAINTENANCE {statusSymbol} --\n'
                                   f'We\'ll be back soon!')
    else:
        await message.edit(content=f'**Server Status**\n'
                                   f'__{currentTime}__\n'
                                   f'- Server Name: `{SERVER_NAME}`\n'
                                   f'- IP Address:Port: `{ipAddress}:{SERVER_PORT}`\n'
                                   f'- Password: `{SERVER_PASSWORD}`\n'
                                   f'- Server Online: `{onlineStatus}` {statusSymbol}\n'
                                   f'- Players Connected: `{currentPlayers}` / `{maxPlayers}` {onlineSymbol}\n'
                                   f'Server restarts are at 4pm and 4am Eastern.')
    return

def place_markers():
    settings_list = []
    response = False

    file = io.open('data/markers.dat', mode='r')
    for line in file:
        settings_list.append(f'{line}')

    for command in settings_list:
        try:
            runRcon(command)
            response = f'Markers placed successfully.'
        except TimeoutError:
            response = f'Error when trying to place markers.'

    return response

def int_epoch_time():
    current_time = datetime.now()
    epoch_time = int(round(current_time.timestamp()))

    return epoch_time

def pull_online_character_info():
    #print(f'start {int_epoch_time()}')
    connected_chars = []
    char_id_list = []
    information_list = []

    charlistResponse = runRcon(f'listplayers')
    charlistResponse.output.pop(0)
    for response in charlistResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', response)
        connected_chars.append(match)

    for char in connected_chars:
        char_name = char[1].strip()
        registration = get_single_registration(char_name)
        char_id = registration[0]
        char_id_list.append(str(char_id))

    criteria = ','.join(char_id_list)
    locationResponse = runRcon(f'sql select a.id, c.char_name, a.x, a.y, a.z '
                               f'from actor_position as a left join characters as c on c.id = a.id '
                               f'where a.id in ({criteria}) limit 30')
    locationResponse.output.pop(0)
    for location in locationResponse.output:
        #print(f'{location}')
        locMatch = re.findall(r'\s+\d+ | [^|]*', location)
        information_list.append(locMatch)

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()
    cur.execute(f'delete from online_character_info')

    for info in information_list:
        cur.execute(f'insert or ignore into online_character_info (char_id,char_name,x,y,z) '
                    f'values ({info[0].strip()},\'{info[1].strip()}\','
                    f'{info[2].strip()},{info[3].strip()},{info[4].strip()})')

    con.commit()
    con.close()

    #print(f'end {int_epoch_time()}')
