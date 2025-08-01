import discord
import re
import time
import requests
import os
import sqlite3

from functions.externalConnections import runRcon, db_query, count_online_players
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
SERVER_IP = str(os.getenv('SERVER_IP'))
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))

def get_bot_config(item: str):
    result = db_query(False, f'select value from config where item like \'%{item}%\' limit 1')
    if not result:
        return False
    for record in result:
        value = record[0]
    return value

CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))

class Registration:
    def __init__(self):
        self.id = 0
        self.char_name = ''
        self.discord_id = ''

def check_channel(ctx):
    whitelist = {'Admin', 'Moderator'}
    roles = {role.name for role in ctx.author.roles}
    if not whitelist.isdisjoint(roles):
        #if we're a special role, no limitations on channel
        return True
    else:
        #everyone else
        if int(ctx.channel.id) != OUTCASTBOT_CHANNEL:
            # print(f'wrong channel {ctx.channel.id} != {OUTCASTBOT_CHANNEL}')
            return False
        else:
            # print(f'good {ctx.channel.id} = {OUTCASTBOT_CHANNEL}')
            return True

def custom_cooldown(ctx):
    whitelist = {'Admin', 'Moderator'}
    roles = {role.name for role in ctx.author.roles}
    if not whitelist.isdisjoint(roles):
        #if we're a special role, no cooldown assigned
        return None
    else:
        #everyone else
        return discord.app_commands.Cooldown(5, 60)

def one_per_min(ctx):
    whitelist = {'Admin'}
    roles = {role.name for role in ctx.author.roles}
    if not whitelist.isdisjoint(roles):
        # if we're a special role, no cooldown assigned
        return None
    else:
        # everyone else
        return discord.app_commands.Cooldown(1, 60)

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
    response = runRcon(f'sql select id, char_name from characters where char_name = \'{name}\' order by id desc limit 1')
    response.output.pop(0)

    if response.output:
        for x in response.output:
            # print(x)
            match = re.findall(r'\s+\d+ | [^|]*', x)
            return match[0]
    else:
        return None

def popup_to_player(charName: str, message: str):
    rconId = get_rcon_id(charName)
    rconResponse = runRcon(f'con {rconId} PlayerMessage \"{charName}\" \"{message}\"')
    # print(rconResponse.output)
    # print(f'PlayerMessage \"{charName}\" \"{message}\"')

def flatten_list(input_list: list):
    #print(f'{input_list}')
    output_list = (sum(input_list, ()))
    return output_list

def get_rcon_id(name: str):
    connected_chars = []

    rconResponse = runRcon('listplayers')
    if rconResponse.error:
        print(f'RCON error in get_rcon_id')
        return False
    rconResponse.output.pop(0)

    for x in rconResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', x)
        connected_chars.append(match)

    if not connected_chars:
        print(f'RCON error in get_rcon_id')
        return False

    for x in connected_chars:
        if name.casefold() == x[1].casefold().strip():
            return x[0].strip()

def get_clan(character):
    match = []

    rconResponse = runRcon(f'sql select c.guild, g.name from characters as c '
                           f'left join guilds as g on c.guild = g.guildId '
                           f'where c.id = {character.id} limit 1')
    if rconResponse.error:
        print(f'RCON error in get_clan')
        return False
    rconResponse.output.pop(0)

    match = re.findall(r'.*^#\d*\s+(\d*)\s\|\s+(.*) \|', rconResponse.output[0])
    match = flatten_list(match)
    print(match)
    if not match:
        return False, False

    (clan_id, clan_name) = match

    return int(clan_id), clan_name

def update_registered_name(input_user, name):
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'update registration set character_name = \'{name}\' where discord_user = \'{input_user}\' '
                f'and season = \'{CURRENT_SEASON}\'')
    con.commit()
    con.close()

def is_registered(discord_id: int, last_season: bool = False):

    returnValue = Registration()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    if last_season:
        query = (f'select game_char_id, character_name, discord_user from registration where discord_user = \'{discord_id}\' '
                 f'and season = {PREVIOUS_SEASON} order by id desc limit 1')
    else:
        query = (f'select game_char_id, character_name, discord_user from registration where discord_user = \'{discord_id}\' '
                 f'and season = \'{CURRENT_SEASON}\'')

    cur.execute(query)
    result = cur.fetchone()

    con.close()

    if result:
        returnValue.id = result[0]
        returnValue.char_name = result[1]
        returnValue.discord_id = result[2]
        return returnValue
    else:
        return False

async def is_message_deleted(channel: discord.TextChannel, message_id):
    try:
        await channel.fetch_message(message_id)
        return False
    except discord.NotFound:
        print(f'Could not find message {message_id} in channel {channel.id}')
        return True

async def no_registered_char_reply(bot, ctx):
    reg_channel = bot.get_channel(REGHERE_CHANNEL)
    await ctx.reply(f'Could not find a Season {CURRENT_SEASON} character registered to {ctx.author.mention}. '
                    f'Visit {reg_channel.mention}!')

def last_season_char(discord_id: int):

    returnValue = Registration()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'select game_char_id, character_name, discord_user from registration where discord_user = \'{discord_id}\' '
                f'and season = {PREVIOUS_SEASON} order by id desc limit 1')
    result = cur.fetchone()

    con.close()

    if result:
        returnValue.id = result[0]
        returnValue.char_name = result[1]
        returnValue.discord_id = result[2]
        return returnValue
    else:
        return False

def get_registration(char_name, char_id: int = 0):
    returnList = []
    char_name = str(char_name).casefold()

    if char_id:
        query_string = (f'select game_char_id, character_name, discord_user from registration '
                        f'where game_char_id = {char_id} and season = {CURRENT_SEASON}')
    else:
        query_string = (f'select game_char_id, character_name, discord_user from registration '
                        f'where character_name like \'%{char_name}%\' and season = {CURRENT_SEASON}')

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'{query_string}')
    results = cur.fetchall()

    con.close()

    if results:
        for result in results:
            returnList.append(result)
        return returnList
    else:
        return False

def get_single_registration_new(char_name: str = '', char_id: int = 0):
    character = Registration()

    if char_id:
        query_string = (f'select game_char_id, character_name, discord_user from registration '
                        f'where game_char_id = {char_id} and season = {CURRENT_SEASON} limit 1')
    else:
        query_string = (f'select game_char_id, character_name, discord_user from registration '
                        f'where character_name like \'%{char_name}%\' and season = {CURRENT_SEASON} limit 1')

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'{query_string}')
    results = cur.fetchone()

    con.close()

    if results:
        character.id = results[0]
        character.char_name = results[1]
        character.discord_id = results[2]

    return character

def get_single_registration(char_name):

    char_name = str(char_name).casefold()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'select game_char_id, character_name, discord_user from registration where character_name like '
                f'\'%{char_name}%\' and season = {CURRENT_SEASON} limit 1')
    results = cur.fetchone()

    con.close()

    if results:
        return results
    else:
        return False

def get_single_registration_temp(char_name):

    # char_name = str(char_name).casefold()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    query = (f'select game_char_id, character_name, discord_user from registration where character_name = '
             f'\'{char_name}\' and season = {CURRENT_SEASON} limit 1')

    # print(f'{query}')
    cur.execute(f'{query}')
    results = cur.fetchone()

    con.close()

    if results:
        return results
    else:
        return False

def get_multiple_registration(namelist):

    for name in namelist:
        name = str(name.casefold())

    char_name = str(char_name).casefold()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'select game_char_id, character_name, discord_user from registration where character_name like '
                f'\'%{char_name}%\' and season = {CURRENT_SEASON}')
    results = cur.fetchone()

    con.close()

    if results:
        return results
    else:
        return False

def run_console_command_by_name(char_name: str, command: str):
    rcon_id = get_rcon_id(f'{char_name}')
    if not rcon_id:
        print(f'No RCON ID returned by get_rcon_id, looking for {char_name}')
        return False
    else:
        runRcon(f'con {rcon_id} {command}')
        return True

async def editStatus(message, bot):
    currentTime = strftime('%A %m/%d/%y at %I:%M %p', time.localtime())

    onlineStatus = f'<indicator disabled>'

    currentPlayers = count_online_players()
    if currentPlayers is False:
        onlineStatus = f'False'
    maxPlayers = 40

    # try:
    #     response = requests.get(QUERY_URL, timeout=5) #.json()
    # except requests.exceptions.Timeout:
    #     print("Livestatus Request timed out")
    #     raise requests.exceptions.Timeout
    # except Exception:
    #     print(f'Exception occurred in querying server for bot status update.')
    #     return
    # matches = re.findall(r'.*<li>&lt;span class=\'label\'&gt;(.*):&lt;\/span&gt; (.*)', response.text)

    # for match in matches:
    #     continue

    # # ipAddress = response.get('ipAddress')
    # onlineStatus = response.get('online')
    # currentPlayers = response.get('currentPlayers')
    # maxPlayers = response.get('maxPlayers')

    if int(get_bot_config(f'maintenance_flag')) == 1:
        statusSymbol = '🔧'
        await bot.change_presence(activity=discord.Activity(name=f'MAINTENANCE', type=3))
    else:
        if 'False' in str(onlineStatus):
            statusSymbol = '<:redtick:1152409914430455839>'
            await bot.change_presence(activity=discord.Activity(name=f'SERVER DOWN', type=3))
        else:
            statusSymbol = '<:greentick:1152409721966432376>'
            await bot.change_presence(activity=discord.Activity(
                name=f'{currentPlayers}/{maxPlayers} ONLINE', type=3))

    onlineSymbol = ':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    if int(currentPlayers) == 40:
        onlineSymbol = (f':orange_circle::orange_circle::orange_circle::orange_circle:'
                        f':orange_circle::orange_circle::orange_circle:')
    if int(currentPlayers) < 35:
        onlineSymbol = (f':orange_circle::orange_circle::orange_circle::orange_circle:'
                        f':orange_circle::orange_circle::blue_circle:')
    if int(currentPlayers) < 30:
        onlineSymbol = (f':orange_circle::orange_circle::orange_circle::orange_circle:'
                        f':orange_circle::blue_circle::blue_circle:')
    if int(currentPlayers) < 25:
        onlineSymbol = (f':orange_circle::orange_circle::orange_circle::orange_circle:'
                        f':blue_circle::blue_circle::blue_circle:')
    if int(currentPlayers) < 20:
        onlineSymbol = (f':orange_circle::orange_circle::orange_circle::blue_circle:'
                        f':blue_circle::blue_circle::blue_circle:')
    if int(currentPlayers) < 15:
        onlineSymbol = (f':orange_circle::orange_circle::blue_circle::blue_circle:'
                        f':blue_circle::blue_circle::blue_circle:')
    if int(currentPlayers) < 10:
        onlineSymbol = f':orange_circle::blue_circle::blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 5:
        onlineSymbol = f':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    if int(get_bot_config(f'maintenance_flag')) == 1:
        await message.edit(content=f'**Server Status**\n'
                                   f'__{currentTime}__\n'
                                   f'- Server Name: `{SERVER_NAME}`\n'
                                   f'- IP Address:Port: `{SERVER_IP}:{SERVER_PORT}`\n'
                                   f'- Password: `{SERVER_PASSWORD}`\n'
                                   f'-- {statusSymbol} MAINTENANCE {statusSymbol} --\n'
                                   f'We\'ll be back soon!')
    else:
        restart_string = get_bot_config('restart_string')
        await message.edit(content=f'**Server Status**\n'
                                   f'__{currentTime}__\n'
                                   f'- Server Name: `{SERVER_NAME}`\n'
                                   f'- IP Address:Port: `{SERVER_IP}:{SERVER_PORT}`\n'
                                   f'- Password: `{SERVER_PASSWORD}`\n'
                                   f'- Direct Connect: ```directconnect {SERVER_IP} {SERVER_PORT}```\n'
                                   # f'- Server Online: `{onlineStatus}` {statusSymbol}\n'
                                   f'- Players Connected: `{currentPlayers}` / `{maxPlayers}` {onlineSymbol}\n'
                                   f'Server restarts are at {restart_string} Eastern.')
    return

def place_markers():
    #settings_list = []
    response = False

    # print(f'marker prep')
    if int(get_bot_config(f'maintenance_flag')) == 1:
        print(f'Skipping marker loop, server in maintenance mode')
        return response

    markers_last_placed = get_bot_config(f'markers_last_placed')
    if int(markers_last_placed) > int_epoch_time() - 900:
        print(f'Skipping marker loop, placed too recently')
        return response
    # print(f'marker list')
    marker_list = db_query(False, f'select marker_label, x, y from warp_locations where marker_flag = \'Y\'')

    #marker_list = flatten_list(result_list)

    # print(f'marker rcon')
    for marker in marker_list:
        command = f'con 0 AddGlobalMarker {marker[0]} {marker[1]} {marker[2]} 3600'
        try:
            runRcon(command)
            response = f'Markers placed successfully.'
            set_bot_config(f'markers_last_placed', str(int_epoch_time()))
        except TimeoutError:
            response = f'Error when trying to place markers.'

    # print(f'marker return')
    return response

    # file = io.open('data/markers.dat', mode='r')
    # for line in file:
    #     settings_list.append(f'{line}')
    #
    # for command in settings_list:
    #     try:
    #         runRcon(command)
    #         response = f'Markers placed successfully.'
    #     except TimeoutError:
    #         response = f'Error when trying to place markers.'
    #
    # return response

def fillThrallCages():
    response = False
    command = f'con 0 dc thrallcage spawn'

    # print(f'cage prep')
    if int(get_bot_config(f'maintenance_flag')) == 1:
        print(f'Skipping thrall cage loop, server in maintenance mode')
        return response

    cages_last_filled = int(get_bot_config(f'cages_last_filled'))
    cage_fill_interval = int(get_bot_config(f'cage_fill_interval'))
    if cages_last_filled > int_epoch_time() - cage_fill_interval:
        # print(f'Skipping thrall cage loop, filled too recently')
        return response

    if int(count_online_players()):
        try:
            rcon_response = runRcon(command)
            if rcon_response.error:
                print(f'Rcon error.')
            # print(f"{rcon_response.output}")
            # print(f'thrall cages filled!')
            response = f'Thrall Cages filled successfully at {str(int_epoch_time())}.'
            set_bot_config(f'cages_last_filled', str(int_epoch_time()))
        except TimeoutError:
            response = f'Error when trying to fill cages'

    return response

def set_bot_config(item: str, value: str):
    db_query(True, f'update config set value = \'{value}\' where item like \'{str(item)}\'')
    return value

def add_bot_config(item: str, value: str):
    db_query(True, f'insert into config (item, value) values (\'{item}\', \'{value}\')')
    return value

def int_epoch_time():
    current_time = datetime.now()
    epoch_time = int(round(current_time.timestamp()))

    return epoch_time

def consume_from_inventory(char_id, char_name, template_id, item_slot=-1):
    if item_slot >= 0:
        run_console_command_by_name(char_name, f'setinventoryitemintstat {item_slot} 1 0 0')
        print(f'Deleted {template_id} from {char_id} {char_name} in slot {item_slot}')
        return True

    elif item_slot == -1:
        print(f'item_slot ({item_slot}) not specified, searching inventory for {template_id}')
        results = runRcon(f'sql select item_id from item_inventory '
                          f'where owner_id = {char_id} and inv_type = 0 '
                          f'and template_id = {template_id} order by item_id asc limit 1')
        if results.error:
            print(f'RCON error received in consume_from_inventory')
            return False

        if results.output:
            results.output.pop(0)
            if not results.output:
                print(f'Tried to delete {template_id} from {char_id} {char_name} but they do not have {template_id}')
                return False
            else:
                for result in results.output:
                    match = re.search(r'\s+\d+ | [^|]*', result)
                    item_slot = int(match[0])
                    run_console_command_by_name(char_name, f'setinventoryitemintstat {item_slot} 1 0 0')
                    print(f'Deleted {template_id} from {char_id} {char_name} in slot {item_slot}')
                    return True
        print(f'Tried to delete {template_id} from {char_id} {char_name} but they do not have {template_id}')
        return False
    return None

def check_inventory(owner_id, inv_type, template_id):
    matched_template_id = 0
    slot = -1
    print(f'we are checking inventory of {owner_id} {inv_type} {template_id}')

    results = runRcon(f'sql select item_id, template_id from item_inventory '
                      f'where owner_id = {owner_id} and inv_type = {inv_type} '
                      f'and template_id in ({template_id}) limit 1')
    if results.error:
        print(f'RCON error received in check_inventory')
        return False

    if results.output:
        results.output.pop(0)
        if not results.output:
            print(f'The required item {template_id} is missing from the inventory of {owner_id}.')
            return slot
    else:
        print(f'Should this ever happen?')

    for result in results.output:
        match = re.findall(r'\s+\d+ | [^|]*', result)
        print(f'{match}')
        slot = match[0]
        matched_template_id = match[1]
        try:
            print(f'checking slot {slot}')
            slot = int(slot)
            print(f'checking template id {matched_template_id}')
            matched_template_id = int(matched_template_id)
            if matched_template_id == template_id:
                print(f'The required item {template_id} is present in the inventory of {owner_id} in slot {slot}.')
                return slot
        except ValueError:
            print(f'ValueError in converting slot ({slot}) or template_id ({template_id}) to int.')
            return slot

    return slot

def count_inventory_qty(owner_id, inv_type, template_id):
    value = 0

    hex_template_id = template_id.to_bytes(4, 'little').hex() + '0300'

    results = runRcon(f'sql select '
                      f'substr(hex(item_inventory.data),instr(hex(item_inventory.data),\'{hex_template_id}\')+12,8) '
                      f'as field_id, '
                      f'substr(hex(item_inventory.data),instr(hex(item_inventory.data),'
                      f'\'{hex_template_id}\')+24,4) as stacksize from item_inventory '
                      f'where owner_id = {owner_id} and inv_type = {inv_type} and template_id = {template_id} '
                      f'order by item_id asc limit 1')

    # results = runRcon(f'sql select trim(substr(hex(data),instr(hex(item_inventory.data),\'001600\') - 4,2) || '
    #                   f'substr(hex(data),instr(hex(item_inventory.data),\'001600\') - 6,2)) as qty_hex '
    #                   f'from item_inventory '
    #                   f'where owner_id = {owner_id} and inv_type = {inv_type} and template_id = {template_id} '
    #                   f'order by item_id asc limit 1')
    if results.error:
        print(f'RCON error received in count_inventory_qty')
        return False

    if results.output:
        results.output.pop(0)
        if not results.output:
            print(f'The required item {template_id} is missing from the inventory of {owner_id}.')
            return False
    else:
        print(f'Should this ever happen?')

    for result in results.output:
        # match = re.search(r'\s+\d+ | [^|]*', result)
        match = re.search(r'#0\s+([A-Z\d]+)\s+[|]\s+([A-Z\d]+)', result)
        if match:
            if match.group(1) == '00000100':
                value_string = match.group(2)
                print(value_string)
                value_bytes = bytes.fromhex(value_string)
                value_int = int.from_bytes(value_bytes, 'little')
                print(value_int)
                value = value_int

                print(f'The required item {template_id} x {value} is present in the inventory of {owner_id}.')
                return value
            else:
                print(f'There must only be one coin in this stack')
                value = 1
                return value
        else:
            print(f'no matches, something is wrong.')
            return False
        # print(f'{match}')
        # value = match[0]
        # value.strip()
        # value = int(value, 16)

    return False
