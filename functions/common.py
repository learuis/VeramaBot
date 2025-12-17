import datetime
import math
import random

import discord
import re
import time
import os
import sqlite3

from aiohttp.helpers import validate_etag_value

from functions.externalConnections import runRcon, db_query, count_online_players, notify_all, rcon_all, multi_rcon
from time import strftime
from dotenv import load_dotenv
from datetime import date, datetime

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
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))

def add_reward_record(char_id: int, itemId: int, quantity: int, reasonString: str):
    if quantity == 0:
        return
    query = (f'insert into event_rewards (reward_date, character_id, season, reward_material, reward_quantity, '
             f'claim_flag, reward_name) values (\'{date.today()}\', {char_id}, {CURRENT_SEASON}, \'{itemId}\', {quantity}, 0, '
             f'\'{reasonString}\')')

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()
    cur.execute(query)
    con.commit()
    con.close()

def get_provisioner_option(character):

    option = f'Combatant'

    query = f'select discord_id, option from provisioner_option where discord_id = {character.discord_id}'
    print(query)
    results = db_query(False, f'{query}')
    print(f'{results}')

    if results:
        for record in results:
            option = record[1]
        return option
    else:
        option = provisioner_swap(character)
        return option


def provisioner_swap(character):
    option = f'Combatant'

    print(f'Provisioner swapping')
    results = db_query(False, f'select discord_id, option from provisioner_option where discord_id = {character.discord_id}')
    print(f'{results}')
    if results:
        if f'Combatant' in str(results):
            option = f'Crafter'
            print(f'results are combatant {option}')
        else:
            option = f'Combatant'
            print(f'results are Crafter{option}')
    else:
        option = f'Combatant'
        print(f'no results {option}')

    db_query(True, f'insert or replace into provisioner_option (discord_id, option) values ({character.discord_id},\'{option}\')')

    print(f'{option}')
    return option

def get_bot_config(item: str):
    result = db_query(False, f'select value from config where item like \'%{item}%\' limit 1')
    if not result:
        return False
    for record in result:
        value = record[0]
    return value

class Registration:
    def __init__(self):
        self.id = 0
        self.char_name = ''
        self.discord_id = ''

    def reset(self):
        self.__init__()

def update_boons(indv_boon: str = ''):
    command_prep = []
    command_list = []
    currentTime = int_epoch_time()

    if int(get_bot_config(f'maintenance_flag')) == 1:
        print(f'Skipping boons loop, server in maintenance mode')
        return

    if int(get_bot_config(f'boons_toggle')) == 0:
        print(f'Skipping boons loop, boons globally disabled')
        return

    if indv_boon:
        boonList = [f'{indv_boon}']
    else:
        boonList = ['ItemConvertionMultiplier', 'ItemSpoilRateScale', 'PlayerXPKillMultiplier',
                    'PlayerXPRateMultiplier', 'DurabilityMultiplier', 'HarvestAmountMultiplier',
                    'ResourceRespawnSpeedMultiplier', 'NPCRespawnMultiplier', 'StaminaCostMultiplier']

    for boon in boonList:
        if int(get_bot_config(boon)) >= currentTime:
            result = db_query(False, f'select active_value from boon_settings where setting_name = \'{boon}\'')
        else:
            result = db_query(False, f'select inactive_value from boon_settings where setting_name = \'{boon}\'')
        setting = flatten_list(result)
        # print(f'{setting}')
        command_prep.append([boon, setting[0]])

    for command in command_prep:
        (setting, value) = command
        new_command = f'SetServerSetting {setting} {value}'
        command_list.append(new_command)

    multi_rcon(command_list)

    if int(get_bot_config('BoonOfReturning')) >= currentTime:
        set_bot_config('home_cost', get_bot_config('home_discount_value'))
    else:
        set_bot_config('home_cost', get_bot_config('home_default_value'))

    return


def check_channel(ctx):
    whitelist = {'Admin', 'Moderator', 'BuildHelper'}
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
        return False, False
    rconResponse.output.pop(0)

    match = re.findall(r'.*^#\d*\s+(\d*)\s\|\s+(.*) \|', rconResponse.output[0])
    match = flatten_list(match)
    # print(match)
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

def get_registration_by_char_id(character_id, last_season: bool = False):

    returnValue = Registration()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    if last_season:
        query = (f'select game_char_id, character_name, discord_user from registration where game_char_id = \'{character_id}\' '
                 f'and season = {PREVIOUS_SEASON} order by id desc limit 1')
    else:
        query = (f'select game_char_id, character_name, discord_user from registration where game_char_id = \'{character_id}\' '
                 f'and season = {CURRENT_SEASON}')

    cur.execute(query)
    result = cur.fetchone()

    con.close()

    if result:
        returnValue.id = result[0]
        returnValue.char_name = result[1]
        returnValue.discord_id = result[2]
        print(returnValue.id, returnValue.char_name, returnValue.discord_id)
        return returnValue
    else:
        return False

def is_registered(discord_id: int, last_season: bool = False):

    # returnValue = RegistrationOLD()
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

    # returnValue = RegistrationOLD()
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
    # character = RegistrationOLD()
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

# def get_multiple_registration(namelist):
#
#     for name in namelist:
#         name = str(name.casefold())
#
#     char_name = str(char_name).casefold()
#     con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
#     cur = con.cursor()
#
#     cur.execute(f'select game_char_id, character_name, discord_user from registration where character_name like '
#                 f'\'%{char_name}%\' and season = {CURRENT_SEASON}')
#     results = cur.fetchone()
#
#     con.close()
#
#     if results:
#         return results
#     else:
#         return False

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
                                   f'Server restarts are at {restart_string} in your local timezone.')
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
    # print(f'we are checking inventory of {owner_id} {inv_type} {template_id}')

    query = (f'sql select item_id, template_id from item_inventory '
             f'where owner_id = {owner_id} and inv_type = {inv_type} '
             f'and template_id in ({template_id}) limit 1')
    # print(query)

    results = runRcon(f'{query}')
    # print(results.output)
    if results.error:
        print(f'RCON error received in check_inventory')
        return False

    if results.output:
        results.output.pop(0)
        if not results.output:
            # print(f'The required item {template_id} is missing from the inventory of {owner_id}.')
            return slot, template_id
    else:
        print(f'Should this ever happen?')

    for result in results.output:
        match = re.findall(r'\s+\d+ | [^|]*', result)
        # print(f'{match}')
        slot = match[0]
        matched_template_id = match[1]
        try:
            # print(f'checking slot {slot}')
            slot = int(slot)
            # print(f'checking template id {matched_template_id}')
            matched_template_id = int(matched_template_id)
            # print(template_id)
            # print(matched_template_id)
            if str(matched_template_id) in str(template_id):
                print(f'The required item {template_id} is present in the inventory of {owner_id} in slot {slot}.')
                return slot, matched_template_id
        except ValueError:
            print(f'ValueError in converting slot ({slot}) or template_id ({template_id}) to int.')
            return slot, template_id

    return slot, template_id

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

def modify_favor(char_id, faction, amount):
    query = db_query(False,
                     f'select char_id, faction, current_favor, lifetime_favor from factions '
                     f'where char_id = {char_id} '
                     f'and faction = \'{faction}\' '
                     f'and season = {CURRENT_SEASON} '
                     f'limit 1')
    if not query:
        db_query(True,
                 f'insert into factions '
                 f'(char_id, season, faction, current_favor, lifetime_favor) '
                 f'values ({char_id},{CURRENT_SEASON}, \'{faction}\', {amount}, {amount})')
        # print(f'Created faction record for {char_id} / {faction}')

    if amount >= 0:
        db_query(True,
                 f'update factions set lifetime_favor = ( '
                 f'select lifetime_favor + {amount} from factions '
                 f'where char_id = {char_id} and faction = \'{faction}\') '
                 f'where char_id = {char_id} and faction = \'{faction}\'')

    db_query(True,
             f'update factions set current_favor = ( '
             f'select current_favor + {amount} from factions '
             f'where char_id = {char_id} and faction = \'{faction}\') '
             f'where char_id = {char_id} and faction = \'{faction}\'')

    results = db_query(False,
                       f'select current_favor from factions '
                       f'where char_id = {char_id} and faction = \'{faction}\' limit 1')
    favor_total = results[0]

    return favor_total


def display_quest_text(quest_id, quest_status, alt, char_name,
                       override_style: int = None, override_text1: str = None, override_text2: str = None):
    style = 0
    text1 = ''
    text2 = ''
    altStyle = ''
    altText1 = ''
    altText2 = ''

    if override_style and override_text1 and override_text2:
        # print(f'Using override quest text for {quest_id}')
        run_console_command_by_name(char_name,
                                    f'testFIFO {override_style} \"{override_text1}\" \"{override_text2}\"')
        return

    questText = db_query(False, f'select Style, Text1, Text2, AltStyle, AltText1, AltText2 from quest_text '
                                f'where quest_id = {quest_id} and step_number = {quest_status}')
    if not questText:
        # print(f'No text defined for {quest_id}, skipping')
        return

    # print(f'{questText}')

    for record in questText:
        style = record[0]
        text1 = record[1]
        text2 = record[2]
        altStyle = record[3]
        altText1 = record[4]
        altText2 = record[5]

    if alt:
        run_console_command_by_name(char_name, f'testFIFO {altStyle} \"{altText1}\" \"{altText2}\"')
    else:
        run_console_command_by_name(char_name, f'testFIFO {style} \"{text1}\" \"{text2}\"')

    return


def grant_reward(char_id, char_name, quest_id, repeatable, tier: int = 0):
    # character = RegistrationOLD()
    character = Registration()
    character.id = char_id
    character.char_name = char_name

    print(f'Granting reward for quest {quest_id} / character {char_id}')

    reward_list = db_query(False, f'select reward_template_id, reward_qty, reward_feat_id, '
                                  f'reward_thrall_name, reward_emote_name, reward_boon, reward_command, range_min, range_max '
                                  f'from quest_rewards where quest_id = {quest_id}')
    if not reward_list:
        print(f'No records returned from reward list, skipping delivery')
        return

    for reward in reward_list:
        (reward_template_id, reward_qty, reward_feat_id, reward_thrall_name,
         reward_emote_name, reward_boon, reward_command, range_min, range_max) = reward

        # display_quest_text(quest_id, 0, True, char_name)
        if reward_template_id and reward_qty:
            check = run_console_command_by_name(char_name, f'spawnitem {reward_template_id} {reward_qty}')
            if not check:
                error_timestamp = datetime.fromtimestamp(float(int_epoch_time()))
                add_reward_record(int(char_id), int(reward_template_id), int(reward_qty),
                                  f'RCON error during quest #{quest_id} reward step at {error_timestamp}')
            continue
        if reward_feat_id:
            run_console_command_by_name(char_name, f'learnfeat {reward_feat_id}')
            con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
            cur = con.cursor()
            cur.execute(f'insert or ignore into featclaim (char_id,feat_id) values ({char_id},{reward_feat_id})')
            con.commit()
            con.close()
            continue
        if reward_thrall_name:
            runRcon(f'con 0 dc spawn 1 thrall exact {reward_thrall_name}x')
            run_console_command_by_name(char_name, f'dc spawn 1 thrall exact {reward_thrall_name}')
            continue
        if reward_emote_name:
            print(f'granting emote {reward_emote_name} to {char_name} / {char_id}')
            run_console_command_by_name(char_name, f'learnemote {reward_emote_name}')
            continue
        if reward_boon:
            print(f'Activating boon {reward_boon}')
            current_expiration = get_bot_config(f'{reward_boon}')
            boon_interval = int(get_bot_config(f'boon_interval'))
            current_time = int_epoch_time()
            if int(current_expiration) < current_time:
                set_bot_config(f'{reward_boon}', str(current_time + boon_interval))
            else:
                set_bot_config(f'{reward_boon}', str(int(current_expiration) + boon_interval))
            result = db_query(False, f'select boon_name from boon_settings '
                                     f'where setting_name = \'{reward_boon}\'')
            boon_name = flatten_list(result)[0]
            notify_all(7, f'-Boon-', f'{boon_name} +3 hours')
            update_boons(f'{reward_boon}')
            continue
        if reward_command:
            match reward_command:
                case 'dc meteor spawn':
                    current_time = int_epoch_time()
                    last_meteor = get_bot_config(f'{reward_command}')
                    next_meteor = current_time + int(repeatable)
                    cooldown_time = int(last_meteor) - int(current_time)

                    if current_time >= int(last_meteor) + int(repeatable):
                        runRcon(f'con 0 {reward_command}')
                        notify_all(7, f'-Boon-', f'Starfall!')
                        set_bot_config(f'{reward_command}', f'{next_meteor}')
                    else:
                        run_console_command_by_name(char_name, f'testFIFO 2 Cooldown {cooldown_time}s until '
                                                               f'Boon of Starfall is available')
                    continue

                case 'AddPatron Patron_Thrallable 0':
                    current_time = int_epoch_time()
                    last_patron = get_bot_config(f'{reward_command}')
                    next_patron = current_time + int(repeatable)
                    cooldown_time = int(last_patron) - int(current_time)

                    if current_time >= int(last_patron) + int(repeatable):
                        rcon_all(f'{reward_command}')
                        notify_all(7, f'-Boon-', f'Check your tavern for a new patron')
                        set_bot_config(f'{reward_command}', f'{next_patron}')
                    else:
                        run_console_command_by_name(char_name, f'testFIFO 2 Cooldown {cooldown_time}s until '
                                                               f'Boon of Freedom is available')
                    continue

                case 'random range':
                    random_reward = random.randint(int(range_min), int(range_max))
                    check = run_console_command_by_name(char_name, f'spawnitem {random_reward} 1')
                    if not check:
                        error_timestamp = datetime.fromtimestamp(float(int_epoch_time()))
                        add_reward_record(int(char_id), int(random_reward), 1,
                                          f'RCON error during quest #{quest_id} reward step at {error_timestamp}')
                    continue

                # case 'treasure hunt':

                    # # location = get_bot_config(f'current_treasure_location')
                    # # result = db_query(False, f'select location_name from treasure_locations where id = {location}')
                    # # print(f'{result}')
                    # # print(f'{result[0][0]}')
                    # # location_name = result[0][0]
                    # # # location_name = re.search(r'[0-9a-zA-Z\s\-()]+', result[0][0])
                    # treasure_target = get_treasure_target(character)
                    # run_console_command_by_name(char_name, f'testFIFO 6 Treasure {treasure_target.target_name}')

                case 'profession':
                    if tier == 0:
                        tier = 1
                    profession_eldarium_min_mult = int(get_bot_config(f'profession_eldarium_min_mult'))
                    profession_eldarium_min_tier_mult = int(get_bot_config(f'profession_eldarium_min_tier_mult'))
                    profession_eldarium_max_mult = int(get_bot_config(f'profession_eldarium_max_mult'))
                    range_min = (((tier ** 2) * profession_eldarium_min_mult) +
                                 (tier * profession_eldarium_min_tier_mult) +
                                 ((5 - tier) * profession_eldarium_min_tier_mult))
                    range_max = (range_min * profession_eldarium_max_mult)
                    random_qty = random.randint(int(range_min), int(range_max))
                    # print(f'reward quantity for tier {tier}: {range_min} to {range_max}')

                    if int(get_bot_config(f'use_bank')) == 1:
                        query_result = db_query(False, f'select requirement_type '
                                                       f'from one_step_quests where quest_id = {quest_id}')
                        profession_name = flatten_list(query_result)
                        eld_transaction(character, f'{profession_name[0]} Payout', random_qty)
                        run_console_command_by_name(char_name, f'testFIFO 6 Reward Deposited {random_qty} '
                                                               f'Decaying Eldarium ')
                        if tier >= 4:
                            run_console_command_by_name(char_name, f'setstat HealthBarStyle 4')
                    else:
                        check = run_console_command_by_name(char_name, f'spawnitem {reward_template_id} {random_qty}')
                        if not check:
                            error_timestamp = datetime.fromtimestamp(float(int_epoch_time()))
                            add_reward_record(int(char_id), int(reward_template_id), int(random_qty),
                                              f'RCON error during quest #{quest_id} reward step at {error_timestamp}')
                case 'provisioner':
                    current_favor = get_favor(char_id, reward_command)
                    threshhold = int(get_bot_config(f'{reward_command}_reward_threshhold'))
                    # print(f'{reward_command} threshhold: {threshhold} current_favor = {current_favor.current_favor}')

                    print(f'get provisioner option')
                    char_lookup = get_registration_by_char_id(int(char_id))
                    if not char_lookup:
                        print(f'Unregistered character {char_id} completed quest')
                    selected_type = get_provisioner_option(char_lookup)
                    print(f'{selected_type}')

                    if int(current_favor.current_favor) >= threshhold:
                        modify_favor(char_id, reward_command, -threshhold)
                        thrall_to_give = provisioner_thrall(selected_type)
                        print(f"{thrall_to_give}")

                        last_restart = int(get_bot_config(f'last_server_restart'))

                        check_time = int(get_bot_config(f'last_thrall_spawned'))
                        print(f'time: {int_epoch_time()} player: {char_name} check_time: {check_time} reward: {thrall_to_give}')
                        if int(check_time) < last_restart:
                            # Run an extra time if no thrall has been delivered since last server restart.
                            run_console_command_by_name(char_name, f'dc spawn 1 thrall exact {thrall_to_give}')
                        run_console_command_by_name(char_name, f'dc spawn 1 thrall exact {thrall_to_give}')
                        set_bot_config(f'last_thrall_spawned', str(int_epoch_time()))
                        display_quest_text(quest_id, 0, False, char_name,
                                           6, f'Joined!',
                                           f'A new follower has pledged loyalty to you!')
                    else:
                        continue
                case 'reliquarian':
                    # already granted favor
                    continue

                case 'slayer':
                    # print(f'we are in slayer reward')
                    reroll_cost = int(get_bot_config(f'beast_slayer_reroll_cost'))
                    reward_quantity = int(get_bot_config(f'beast_slayer_reward'))
                    t1_favor = int(get_bot_config(f'beast_slayer_t1_favor'))
                    t2_favor = int(get_bot_config(f'beast_slayer_t2_favor'))
                    t3_favor = int(get_bot_config(f'beast_slayer_t3_favor'))

                    current_target = get_slayer_target(character)
                    notorious_target, notorious_multiplier = get_notoriety(current_target)

                    # print(f'{notorious_target} {notorious_multiplier} for grant_reward')

                    reward_quantity = reward_quantity + (reroll_cost * notorious_multiplier)

                    chance, value = slayer_bonus_item_chance(notorious_multiplier)
                    if chance:
                        print(f'Notoriety {notorious_multiplier} target slain, chance: {value}%, bonus item earned.')
                        results = db_query(False, f'select item_id, item_name from treasure_rewards '
                                                  f'where reward_category = 1 order by RANDOM() limit 1')
                        reward_list.append(flatten_list(results))
                        for hunt_treasure in reward_list:
                            # print(f'{reward}')
                            outputMessage += f'`{hunt_treasure[1]}` | '
                            add_reward_record(int(character.id), int(hunt_treasure[0]), 1, f'Treasure Hunt: {hunt_treasure[1]}')

                    else:
                        print(f'Notoriety {notorious_multiplier} target slain, chance: {value}%, no bonus item.')

                    current_favor = get_favor(char_id, reward_command)
                    if current_favor.lifetime_favor >= t3_favor:
                        run_console_command_by_name(char_name, f'setstat HealthBarStyle 3')
                    elif current_favor.lifetime_favor >= t2_favor:
                        run_console_command_by_name(char_name, f'setstat HealthBarStyle 2')
                    elif current_favor.lifetime_favor >= t1_favor:
                        run_console_command_by_name(char_name, f'setstat HealthBarStyle 1')

                    # print(f'granting eld')
                    if notorious_multiplier == 0:
                        eld_transaction(character, f'Beast Slayer Reward', reward_quantity)
                    else:
                        eld_transaction(character, f'Notorious Beast Reward', reward_quantity)

                    clear_notoriety(current_target)

                    run_console_command_by_name(char_name, f'testFIFO 6 Reward Deposited {reward_quantity} '
                                                           f'Decaying Eldarium ')


        continue

    return

def grant_slayer_rewards(character, current_target):
    item_list = []
    outputString = ''

    reroll_cost = int(get_bot_config(f'beast_slayer_reroll_cost'))
    reward_quantity = int(get_bot_config(f'beast_slayer_reward'))
    t1_favor = int(get_bot_config(f'beast_slayer_t1_favor'))
    t2_favor = int(get_bot_config(f'beast_slayer_t2_favor'))
    t3_favor = int(get_bot_config(f'beast_slayer_t3_favor'))

    notorious_target, notorious_multiplier = get_notoriety(current_target)

    reward_quantity = reward_quantity + (reroll_cost * notorious_multiplier)

    current_favor = get_favor(character.id, 'slayer')
    if current_favor.lifetime_favor >= t3_favor:
        run_console_command_by_name(character.char_name, f'setstat HealthBarStyle 3')
    elif current_favor.lifetime_favor >= t2_favor:
        run_console_command_by_name(character.char_name, f'setstat HealthBarStyle 2')
    elif current_favor.lifetime_favor >= t1_favor:
        run_console_command_by_name(character.char_name, f'setstat HealthBarStyle 1')

    # print(f'granting eld')
    if notorious_multiplier == 0:
        eld_transaction(character, f'Beast Slayer Reward', reward_quantity)
    else:
        eld_transaction(character, f'Notorious Beast Reward', reward_quantity)

    chance, value = slayer_bonus_item_chance(notorious_multiplier)
    if chance:
        results = db_query(False, f'select item_id, item_name from treasure_rewards '
                                  f'where reward_category = 1 order by RANDOM() limit 1')
        item_list.append(flatten_list(results))
        for item in item_list:
            add_reward_record(int(character.id), int(item[0]), 1, f'Beast Slayer: {item[1]}')
            item_string = f'You found `{item[1]}` hidden in a nearby loot cache! Use `v/claim` to receive it.\n'
    else:
        item_string = f'You had a `{value}%` chance to find a loot cache, but didn\'t find one this time.\n'

    clear_notoriety(current_target)
    increment_killed_total(current_target)

    run_console_command_by_name(character.char_name, f'testFIFO 6 Reward Deposited {reward_quantity} '
                                           f'Decaying Eldarium')

    reward = int(get_bot_config(f'beast_slayer_reward'))
    reroll_cost = int(get_bot_config('beast_slayer_reroll_cost'))
    outputString += (f'Your quarry, `{current_target.display_name}`, has been slain! '
                     f'You have earned '
                     f'`{reward + (reroll_cost * notorious_multiplier)}` decaying eldarium!\n{item_string}'
                     f'Return to the Beast Slayer at the Profession Hub to be assigned a new Quarry.')
    print(f'{outputString}')

    return outputString

def eld_transaction(character, reason: str, amount: int = 0, eld_type: str = 'raw', season = CURRENT_SEASON):

    if eld_type == 'bars':
        amount = amount * 2
        reason += f' (Bars)'
    else:
        reason += f' (DE)'

    db_query(True, f'insert into bank_transactions (season, char_id, amount, reason, timestamp) '
                   f'values ({season}, {character.id}, {amount}, \'{reason}\', \'{int_epoch_time()}\')')
    db_query(True, f'insert or replace into bank (season, char_id, balance) '
                   f'values ({season}, {character.id}, '
                   f'( select sum(amount) from bank_transactions '
                   f'where season = {season} and char_id = {character.id}) )')
    new_balance = get_balance(character)
    return new_balance


def get_balance(character, season = CURRENT_SEASON):
    balance = 0

    results = db_query(False,
                       f'SELECT balance from bank where char_id = {character.id} and season = {season} limit 1')
    if results:
        balance = int(flatten_list(results)[0])
    return balance


def sufficient_funds(character, debit_amount: int = 0, eld_type: str = 'raw'):

    balance = int(get_balance(character))

    if eld_type == 'bars':
        debit_amount = debit_amount * 2

    if balance >= debit_amount:
        return True
    else:
        return False

def record_claimed_kit(character, kit_name):
    db_query(True, f'insert or replace into claimed_kits (season, char_id, kit_name) values '
                   f'({CURRENT_SEASON}, {character.id}, \'{kit_name}\')')
    return

def claimed_kit(character, kit_name):
    result = db_query(False, f'select * from claimed_kits '
                             f'where char_id = {character.id} and season = {CURRENT_SEASON} and kit_name = \'{kit_name}\'')
    if result:
        return True
    else:
        return False

def get_kit_details(kit_name):
    result = db_query(False, f'select item_id, quantity, item_name from kits '
                             f'where kit_name = \'{kit_name}\'')
    if result:
        item_list = []
        for item in result:
            item_tuple = (item[0], item[1], item[2])
            item_list.append(item_tuple)
        print(item_list)
        return item_list
    else:
        return False

def killed_target(my_target, character):
    clan_id, clan_name = get_clan(character)
    if clan_id:
        causer_string = f'causerGuildId = {clan_id}'
    else:
        causer_string = f'causerId = {character.id}'

    query = (f'sql select worldTime from game_events where '
                           f'eventType = 86 and '
                           f'objectName = \'{my_target.target_name}\' and '
                           f'worldTime >= {my_target.start_time} and '
                           f'{causer_string} '
                           f'order by worldTime desc limit 1')

    rconResponse = runRcon(f'{query}')
    # print(str(rconResponse.output))
    match = re.search(r'#0 (\d+) \|', str(rconResponse.output))
    if match:
        return True
    else:
        return False


class SlayerTarget:
    def __init__(self):
        self.char_id = 0
        self.target_name = ''
        self.display_name = ''
        self.start_time = 0

def get_character_level(character):
    level = 0
    results = runRcon(f'sql select level from characters where id = {character.id}')
    print(results.output)
    if results:
        results.output.pop(0)
        for result in results.output:
            match = re.search(r'\s+\d+ | [^|]*', result)
            level = int(match[0])
    return level

def has_arachnophobia(character):
    # print(f'do we have arachnophobia? {character.id}')
    results = db_query(False, f'select discord_id from arachnophobia where discord_id = {character.discord_id}')
    return True if results else False

def toggle_arachnophobia(character):
    results = db_query(False, f'select discord_id from arachnophobia where discord_id = {character.discord_id}')
    if results:
        db_query(True, f'delete from arachnophobia where discord_id = {character.discord_id}')
        return False
    else:
        db_query(True, f'insert into arachnophobia (discord_id) values ({character.discord_id})')
        return True

def set_slayer_reroll_exclusion(character, exclude_target):
    db_query(True, f'insert or replace into beast_slayer_rerolled_targets (season, char_id, target_name) values '
                   f'({CURRENT_SEASON}, {character.id}, \'{exclude_target.target_name}\')')
    return

def get_slayer_reroll_exclusion(character):
    result = db_query(False, f'select target_name from beast_slayer_rerolled_targets '
                             f'where char_id = {character.id} and season = {CURRENT_SEASON}')
    if result:
        target_list = []
        for target in result:
            target_list.append(target[0])
        print(target_list)
        return target_list
    else:
        return False

def clear_slayer_reroll(target_to_remove):
    db_query(True, f'delete from beast_slayer_rerolled_targets '
                   f'where target_name = \'{target_to_remove.target_name}\'')
    return

def set_slayer_target(character):
    spider_string = f'target_name not like \'%spider%\''
    where_clause = ''

    exclude_list = get_slayer_reroll_exclusion(character)
    if exclude_list:
        where_clause = f' where target_name not like '
        for index, excluded_target in enumerate(exclude_list):
            where_clause += f'\'%{excluded_target}\''
            if index == len(exclude_list) - 1:
                continue
            else:
                where_clause += f' and target_name not like '

    # if exclude_target:
    #     where_clause = f' where target_name not like \'%{exclude_target.target_name}%\' and notoriety = 0'

    if has_arachnophobia(character):
        if where_clause:
            where_clause += f' and {spider_string}'
        else:
            where_clause = f' where {spider_string}'

    print(where_clause)

    my_target = SlayerTarget()
    my_target.char_id = character.id
    my_target.start_time = int_epoch_time()
    # randomizer = random.randint(0, int(get_bot_config('beast_slayer_target_count')))
    query = (f'select target_name, target_display_name from beast_slayer_target_list'
             f'{where_clause} order by notoriety desc, times_killed asc, random() limit 1')
    print(query)
    # rconResponse = runRcon(query)
    query_result = db_query(False, f'{query}')
    # print(query_result)
    (my_target.target_name, my_target.display_name) = flatten_list(query_result)
    db_query(True, f'insert or replace into beast_slayers '
                   f'(char_id, season, target_name, target_display_name, start_time) '
                   f'values ({my_target.char_id}, {CURRENT_SEASON}, \'{my_target.target_name}\', '
                   f'\'{my_target.display_name}\', {my_target.start_time})')
    return my_target


def clear_slayer_target(character: Registration):
    db_query(True, f'delete from beast_slayers where char_id = {character.id} and season = {CURRENT_SEASON}')
    return


def get_slayer_target(character: Registration):
    my_target = SlayerTarget()
    query_result = db_query(False, f'select char_id, target_name, target_display_name, start_time from beast_slayers'
                                   f' where char_id = {character.id} and season = {CURRENT_SEASON}')
    if query_result:
        print(query_result)
        (my_target.char_id, my_target.target_name,
         my_target.display_name, my_target.start_time) = flatten_list(query_result)
        # print(f'My target {my_target}')
        return my_target
    else:
        return False

def slayer_bonus_item_chance(notoriety: int):
    notoriety_value = int(get_bot_config('notoriety_bonus_item_mult'))
    reward_chance = 10 + ( notoriety * notoriety_value )
    item_roll = random.randint(int(1), int(100))
    if item_roll <= reward_chance:
        return True, reward_chance
    else:
        return False, reward_chance

def get_notoriety(quarry: SlayerTarget):
    # print(f'getting notoriety {quarry.target_name}')
    query_result = db_query(False, f'select target_name, notoriety from beast_slayer_target_list '
                                   f'where target_name like \'%{quarry.target_name}%\' limit 1')
    # print(query_result)
    notorious_target, notorious_multiplier = flatten_list(query_result)
    # print(notorious_target, notorious_multiplier)

    return notorious_target, int(notorious_multiplier)


def clear_notoriety(quarry: SlayerTarget):
    db_query(True, f'update beast_slayer_target_list set notoriety = 0 '
                   f'where target_name like \'%{quarry.target_name}%\'')
    query_result = db_query(False, f'select target_name, notoriety from beast_slayer_target_list '
                                   f'where target_name like \'%{quarry.target_name}%\' limit 1')

    notorious_target, notorious_multiplier = flatten_list(query_result)

    return notorious_target, int(notorious_multiplier)


def increase_notoriety(quarry: SlayerTarget):
    db_query(True, f'update beast_slayer_target_list set notoriety = notoriety + 1 '
                   f'where target_name like \'%{quarry.target_name}%\'')
    query_result = db_query(False, f'select target_name, notoriety from beast_slayer_target_list '
                                   f'where target_name like \'%{quarry.target_name}%\' limit 1')
    notorious_target, notorious_multiplier = flatten_list(query_result)

    return notorious_target, int(notorious_multiplier)

def increment_killed_total(quarry: SlayerTarget):
    db_query(True, f'update beast_slayer_target_list set times_killed = times_killed + 1 '
                   f'where target_name like \'%{quarry.target_name}%\'')

    return

class TreasureTarget:
    def __init__(self):
        self.char_id = 0
        self.location_id = ''
        self.location_name = ''
        self.start_time = 0


def set_treasure_target(character):

    my_target = TreasureTarget()
    my_target.char_id = character.id
    my_target.start_time = int_epoch_time()
    # randomizer = random.randint(0, int(get_bot_config('beast_slayer_target_count')))
    query = (f'select id, location_name from treasure_locations'
             f' order by times_looted asc, random() limit 1')
    query_result = db_query(False, f'{query}')
    # print(query_result)
    (my_target.location_id, my_target.location_name) = flatten_list(query_result)
    db_query(True, f'insert or replace into treasure_hunters '
                   f'(char_id, season, location_id, location_name, start_time) '
                   f'values ({my_target.char_id}, {CURRENT_SEASON}, \'{my_target.location_id}\', '
                   f'\'{my_target.location_name}\', {my_target.start_time})')
    return my_target


def clear_treasure_target(character: Registration):
    db_query(True, f'delete from treasure_hunters where char_id = {character.id} and season = {CURRENT_SEASON}')
    return


def get_treasure_target(character: Registration):
    my_target = TreasureTarget()
    query_result = db_query(False, f'select char_id, location_id, location_name, start_time from treasure_hunters'
                                   f' where char_id = {character.id} and season = {CURRENT_SEASON}')
    if query_result:
        print(query_result)
        (my_target.char_id, my_target.location_id,
         my_target.location_name, my_target.start_time) = flatten_list(query_result)
        # print(f'My target {my_target}')
        return my_target
    else:
        return False

def increment_times_looted(target: TreasureTarget):
    db_query(True, f'update treasure_locations set times_looted = times_looted + 1 '
                   f'where id = {target.location_id}')

    return


def get_favor(char_id, faction):
    favor_values = Favor()

    query = db_query(False,
                     f'select char_id, faction, current_favor, lifetime_favor from factions '
                     f'where char_id = {char_id} '
                     f'and faction = \'{faction}\' '
                     f'and season = {CURRENT_SEASON} '
                     f'limit 1')
    # print(f'{query}')

    if not query:
        db_query(True,
                 f'insert into factions '
                 f'(char_id, season, faction, current_favor, lifetime_favor) '
                 f'values ({char_id},{CURRENT_SEASON}, \'{faction}\', 0, 0)')
        # print(f'Created faction record for {char_id} / {faction}')
        favor_values.char_id = char_id
        favor_values.faction = faction
        favor_values.current_favor = 0
        favor_values.lifetime_favor = 0

        return favor_values

    for record in query:
        (favor_values.char_id,
         favor_values.faction,
         favor_values.current_favor,
         favor_values.lifetime_favor) = record

    return favor_values


def provisioner_thrall(selected_type):
    thrall_to_give = ''
    count = int(get_bot_config(f'provisioner_thrall_count'))
    # record_id = random.randint(int(1), count)
    results = db_query(False, f'select thrall_name from provisioner_rewards '
                              f'where thrall_type = \'{selected_type}\' order by random() limit 1')
    print(f'random thrall results: {results}')

    for result in results:
        thrall_to_give = str(result[0])

    return thrall_to_give


class Favor:
    def __init__(self):
        self.char_id = 0
        self.faction = ''
        self.current_favor = 0
        self.lifetime_favor = 0


class RegistrationOLD:
    def __init__(self):
        self.id = 0
        self.char_name = ''

    def reset(self):
        self.__init__()


def transform_coordinates(x, y):
    x_squares = 'ABCDEFGHIJKLMNOP'
    x = math.floor(1 + ((x + 307682) / 46500))
    y = math.floor(1 + (-(y - 330805) / 46500))

    x_square_label = x_squares[x-1]
    y_square_label = y + 1
    print(f'{x_square_label}{y_square_label}')
    return x_square_label, y_square_label
