import datetime
import re
import sqlite3
import random

from discord.ext import commands
from datetime import datetime

from cogs.CommunityBoons import update_boons
from cogs.Reward import add_reward_record
from functions.common import (custom_cooldown, run_console_command_by_name, int_epoch_time,
                              flatten_list, get_bot_config, set_bot_config, get_single_registration)
from functions.externalConnections import runRcon, db_query, notify_all, rcon_all

def pull_online_character_info():
    print(f'start char info query {int_epoch_time()}')
    connected_chars = []
    char_id_list = []
    information_list = []

    if int(get_bot_config(f'maintenance_flag')) == 1:
        print(f'Skipping online char info loop, server in maintenance mode')
        return False

    if int(get_bot_config(f'quest_toggle')) == 0:
        print(f'Skipping online char info loop, quests are globally disabled')
        return

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()
    cur.execute(f'delete from online_character_info')
    con.commit()
    con.close()

    charlistResponse = runRcon(f'listplayers')
    if charlistResponse.error:
        print(f'{charlistResponse.output}')
        print(f'Error in RCON listplayers command at {datetime.now()}')
        return False

    charlistResponse.output.pop(0)
    for response in charlistResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', response)
        connected_chars.append(match)

    for char in connected_chars:
        char_name = char[1].strip()
        #print(char_name)
        registration = get_single_registration(char_name)
        if not registration:
            continue
        char_id = registration[0]
        char_id_list.append(str(char_id))

    criteria = ','.join(char_id_list)

    locationResponse = runRcon(f'sql select a.id, c.char_name, a.x, a.y, a.z '
                               f'from actor_position as a left join characters as c on c.id = a.id '
                               f'where a.id in ({criteria}) limit 40')
    locationResponse.output.pop(0)
    for location in locationResponse.output:
        #print(f'{location}')
        locMatch = re.findall(r'\s+\d+ | [^|]*', location)
        information_list.append(locMatch)

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    for info in information_list:
        cur.execute(f'insert or ignore into online_character_info (char_id,char_name,x,y,z) '
                    f'values ({info[0].strip()},\'{info[1].strip()}\','
                    f'{info[2].strip()},{info[3].strip()},{info[4].strip()})')

    con.commit()
    con.close()

    print(f'end char info query {int_epoch_time()}')
    return True

def complete_quest(quest_id: int, char_id: int):

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    # cur.execute(f'update quest_tracker set quest_status = ?, '
    #             f'quest_char_id = ?, '
    #             f'quest_char_name = ? '
    #             f'where quest_id = ?', (0, None, None, None, quest_id))
    cur.execute(f'insert into quest_history (quest_id, char_id) '
                f'values ( {quest_id}, {char_id} )')
    print(f'Quest {quest_id} has been completed.')

    con.commit()
    con.close()

    return

def display_quest_text(quest_id, quest_status, alt, char_name):
    style = 0
    text1 = ''
    text2 = ''
    altStyle = ''
    altText1 = ''
    altText2 = ''

    questText = db_query(False, f'select Style, Text1, Text2, AltStyle, AltText1, AltText2 from quest_text '
                         f'where quest_id = {quest_id} and step_number = {quest_status}')
    if not questText:
        print(f'No text defined for {quest_id}, skipping')
        return

    print(f'{questText}')

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

def consume_from_inventory(char_id, char_name, template_id):
    results = runRcon(f'sql select item_id from item_inventory '
                      f'where owner_id = {char_id} and inv_type = 0 '
                      f'and template_id = {template_id} limit 1')
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
    return True

def check_inventory(owner_id, inv_type, template_id):
    value = 0

    results = runRcon(f'sql select template_id from item_inventory '
                      f'where owner_id = {owner_id} and inv_type = {inv_type} '
                      f'and template_id = {template_id} limit 1')
    if results.error:
        print(f'RCON error received in check_inventory')
        return False

    if results.output:
        results.output.pop(0)
        if not results.output:
            print(f'The required item {template_id} is missing from the inventory of {owner_id}.')
            return False
    else:
        print(f'Should this ever happen?')

    for result in results.output:
        match = re.search(r'\s+\d+ | [^|]*', result)
        #print(f'{match}')
        value = match[0]

    if int(value) == template_id:
        print(f'The required item {template_id} is present in the inventory of {owner_id}.')
        return True

    return False

def character_in_radius(trigger_x, trigger_y, trigger_z, trigger_radius):
    nwPoint = [trigger_x - trigger_radius, trigger_y - trigger_radius]
    sePoint = [trigger_x + trigger_radius, trigger_y + trigger_radius]

    #connected_chars = []
    #print(f'{nwPoint} {sePoint}')
    results = db_query(False, f'select char_id, char_name from online_character_info '
                       f'where x >= {nwPoint[0]} and y >= {nwPoint[1]} '
                       f'and x <= {sePoint[0]} and y <= {sePoint[1]} '
                       f'and z >= {trigger_z-100} and z <= {trigger_z+100} limit 1')
    if results:
        char_info = flatten_list(results)
    else:
        return False, False

    if char_info:
        (char_id, char_name) = char_info
    else:
        return False, False

    if char_id and char_name:
        return char_id, char_name
    else:
        return False, False

def clear_cooldown(char_id, quest_id):
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'delete from quest_timeout where character_id = {char_id} and quest_id = {quest_id}')
    print(f'Cooldown cleared for quest {quest_id} / character {char_id}')

    con.commit()
    con.close()

def finish_cooldowns():
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'delete from quest_timeout where timeout_until <= {int_epoch_time()}')

    con.commit()
    con.close()

def add_cooldown(char_id, quest_id, cooldown: int):
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'insert or ignore into quest_timeout '
                f'values ({quest_id}, {char_id}, {int_epoch_time()+int(cooldown)})')

    con.commit()
    con.close()

def grant_reward(char_id, char_name, quest_id, repeatable):
    reward_list = db_query(False, f'select reward_template_id, reward_qty, reward_feat_id, '
                           f'reward_thrall_name, reward_emote_name, reward_boon, reward_command, range_min, range_max '
                           f'from quest_rewards where quest_id = {quest_id}')
    if not reward_list:
        print(f'No records returned from reward list, skipping delivery')
        return

    for reward in reward_list:
        (reward_template_id, reward_qty, reward_feat_id, reward_thrall_name,
         reward_emote_name, reward_boon, reward_command, range_min, range_max) = reward

        #display_quest_text(quest_id, 0, True, char_name)
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
            current_time = int_epoch_time()
            if int(current_expiration) < current_time:
                set_bot_config(f'{reward_boon}', str(current_time+10800))
            else:
                set_bot_config(f'{reward_boon}', str(int(current_expiration)+10800))
            notify_all(7, f'-Boon-', f'{reward_boon} improvement +3 hours')
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

                case 'treasure hunt':
                    location = get_bot_config(f'current_treasure_location')
                    result = str(db_query(False, f'select location_name from treasure_locations where id = {location}'))
                    print(f'{result}')
                    location_name = re.search(r'[a-zA-Z\s\-]+', result)
                    run_console_command_by_name(char_name, f'testFIFO 6 Treasure {location_name.group()}')

        continue

    return

async def oneStepQuestUpdate(bot):

    if int(get_bot_config(f'maintenance_flag')) == 1:
        print(f'Skipping quest loop, server in maintenance mode')
        bot.quest_running = False
        return

    if int(get_bot_config(f'quest_toggle')) == 0:
        print(f'Skipping quest loop, quests are globally disabled')
        bot.quest_running = False
        return

    bot.quest_running = True
    #print(f'boop')

    quest_list = db_query(False, f'select quest_id, quest_name, active_flag, requirement_type, repeatable, '
                          f'trigger_x, trigger_y, trigger_z, trigger_radius, '
                          f'target_x, target_y, target_z '
                          f'from one_step_quests')

    for quest in quest_list:
        (quest_id, quest_name, active_flag, requirement_type, repeatable,
         trigger_x, trigger_y, trigger_z, trigger_radius, target_x, target_y, target_z) = quest

        char_id, char_name = character_in_radius(trigger_x, trigger_y, trigger_z, trigger_radius)

        if not char_id:
            #print(f'Skipping quest {quest_id}, no one in the box')
            continue

        if active_flag == 0:
            display_quest_text(999999, 0, False, char_name)
            continue

        #clear all fulfilled cooldowns
        finish_cooldowns()

        cooldown_records = db_query(False, f'select timeout_until from quest_timeout '
                                    f'where character_id = {char_id} and quest_id = {quest_id} limit 1')
        if cooldown_records:
            cooldown = flatten_list(cooldown_records)
            cooldown_until = cooldown[0]
            if int(int_epoch_time() < cooldown_until):
                cooldown_time = cooldown_until - int_epoch_time()
                if cooldown_time > 12000:
                    print(f'Quest {quest_id} / {quest_name} is already complete for id {char_id} {char_name}')
                else:
                    print(f'Skipping quest {quest_id} / {quest_name} for id {char_id} {char_name}, on cooldown')
                continue
            else:
                print(f'Clearing cooldown on {quest_id} for id {char_id} {char_name}')
                clear_cooldown(char_id, quest_id)

        match requirement_type:
            case 'Treasure':
                grant_reward(char_id, char_name, quest_id, repeatable)
                print(f'Quest {quest_id} completed by id {char_id} {char_name}')
                continue
            case 'Information':
                display_quest_text(quest_id, 0, False, char_name)
                add_cooldown(char_id, quest_id, repeatable)
                print(f'Quest {quest_id} completed by id {char_id} {char_name}')
                continue
            case 'Presence':
                display_quest_text(quest_id, 0, False, char_name)
                grant_reward(char_id, char_name, quest_id, repeatable)
                if target_x:
                    run_console_command_by_name(char_name, f'teleportplayer {target_x} {target_y} {target_z}')
                print(f'Quest {quest_id} completed by id {char_id} {char_name}')
                add_cooldown(char_id, quest_id, repeatable)
                continue
            case 'Meteor':
                if target_x:
                    run_console_command_by_name(char_name, f'teleportplayer {target_x} {target_y} {target_z}')
                grant_reward(char_id, char_name, quest_id, repeatable)
                print(f'Quest {quest_id} completed by id {char_id} {char_name}')
                add_cooldown(char_id, quest_id, repeatable)
                continue
            case 'BringItems':
                missingitem = 0
                req_list = db_query(False, f'select template_id, item_qty '
                                    f'from quest_requirements where quest_id = {quest_id}')
                for requirement in req_list:
                    (template_id, item_qty) = requirement
                    inventoryHasItem = check_inventory(char_id, 0, template_id)
                    if inventoryHasItem:
                        consume_from_inventory(char_id, char_name, template_id)
                    else:
                        missingitem += 1
                        print(f'Skipping quest {quest_id}, id {char_id} {char_name} '
                              f'does not have the required item {template_id}')
                        continue
                if missingitem == 0:
                    display_quest_text(quest_id, 0, False, char_name)
                    grant_reward(char_id, char_name, quest_id, repeatable)
                    print(f'Quest {quest_id} completed by id {char_id} {char_name}')
                    add_cooldown(char_id, quest_id, repeatable)
                    if target_x:
                        run_console_command_by_name(char_name, f'teleportplayer {target_x} {target_y} {target_z}')

                continue

    bot.quest_running = False

class QuestSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='clearquesthistory')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def clearquesthistory(self, ctx, quest_id, char_id):
        """

        Parameters
        ----------
        ctx
        quest_id
        char_id

        Returns
        -------

        """
        try:
            int(char_id)
        except ValueError:
            await ctx.send(f'Character ID must be an integer.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'delete from quest_history where char_id = {char_id} and quest_id = {quest_id}')

        con.commit()
        con.close()

        clear_cooldown(char_id, quest_id)

        await ctx.send(f'Quest History for quest {quest_id} / player {char_id} has been reset.')

    @commands.command(name='updatequesttext')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def updatequesttext(self, ctx, quest_id: int, style: int, text1: str, text2: str):
        """

        Parameters
        ----------
        ctx
        quest_id
        style
        text1
        text2

        Returns
        -------

        """
        try:
            int(quest_id)
            int(style)
            str(text1)
            str(text2)
        except ValueError:
            await ctx.send(f'Input error.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'update or ignore quest_text set quest_id = {quest_id}, step_number = 0, style = {style}, '
                    f'Text1 = \'{text1}\', Text2 = \'{text2}\' where quest_id = {quest_id}')

        con.commit()
        con.close()

        await ctx.send(f'Modified Quest Text: {quest_id} 0 {style} \'{text1}\' \'{text2}\'')

    @commands.command(name='updatequestcooldown')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def addqueststep(self, ctx, quest_id: int, new_cooldown: int):
        """

        Parameters
        ----------
        ctx
        quest_id
        new_cooldown

        Returns
        -------

        """
        try:
            int(quest_id)
            int(new_cooldown)
        except ValueError:
            await ctx.send(f'Input error.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'update one_step_quests set repeatable = \'{new_cooldown}\' where quest_id = {quest_id}')

        con.commit()
        con.close()

        await ctx.send(f'Modified Quest Cooldown: {quest_id} {new_cooldown}')

    @commands.command(name='replayquesttext')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def createquest(self, ctx, quest_id: int, char_name: str):
        """

        Parameters
        ----------
        ctx
        quest_id
        char_name

        Returns
        -------

        """
        try:
            int(quest_id)
            str(char_name)
        except ValueError:
            await ctx.send(f'Input error.')
            return

        display_quest_text(quest_id, 0, False, char_name)

        await ctx.send(f'Displayed text for quest {quest_id} to {char_name}')

    @commands.command(name='onlinecharinfo')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def onlinecharinfo(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        print(f'{ctx}')
        pull_online_character_info()

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(QuestSystem(bot))
