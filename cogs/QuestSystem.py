from discord.ext import commands

from cogs.Professions import get_current_objective, get_profession_tier, give_profession_xp
from functions.common import *
from functions.common import display_quest_text, grant_reward, killed_target, set_slayer_target, clear_slayer_target, \
    get_slayer_target, get_notoriety, RegistrationOLD
from functions.externalConnections import runRcon, db_query, rcon_all


class CharLocation:
    def __init__(self):
        self.id = 0
        self.x = 0
        self.y = 0
        self.z = 0

def pull_online_character_info_new():
    matches = []
    worklist = []
    character_location = CharLocation()
    responses = runRcon(f'sql select c.id, ap.x, ap.y, ap.z from characters c '
                        f'left join account a on c.playerId = a.id '
                        f'left join actor_position ap on c.id = ap.id '
                        f'where a.online = 1 '
                        f'and c.lastTimeOnline >= ( select max(lastTimeOnline)-60 from characters ) '
                        f'order by c.lastTimeOnline desc limit 40')
    responses.output.pop(0)

    for response in responses.output:
        matches = re.findall(r'#\d+\s+(\d+)\s[|]\s+([-\d+.]+)\s[|]\s+([-\d+.]+)\s[|]\s+([-\d+.]+)', response)

        for match in matches:
            print(match)
            (character_location.id, character_location.x, character_location.y, character_location.z) = match
            worklist.append(character_location)

    for item in worklist:
        character = get_single_registration_new(f'', item.id)
        print(character.char_name)


def pull_online_character_info():
    # print(f'start char info query {int_epoch_time()}')
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
    # print(f'Trying to clear online_character_info')
    cur.execute(f'delete from online_character_info')
    con.commit()
    con.close()

    charlistResponse = runRcon(f'listplayers')
    if charlistResponse.error:
        # print(f'{charlistResponse.output}')
        print(f'Error in RCON listplayers {charlistResponse.output} command at {datetime.now()}')
        return False

    charlistResponse.output.pop(0)
    for response in charlistResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', response)
        connected_chars.append(match)

    for char in connected_chars:
        char_name = char[1].strip()
        # print(char_name)
        # registration = get_single_registration(char_name)
        registration = get_single_registration_temp(char_name)
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
        # print(f'{location}')
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

    result = runRcon(f'sql select worldTime from game_events '
                     f'where eventType = 0 order by worldTime desc limit 1')
    # print(result.output)
    result.output.pop(0)
    # print(f'server last restarted at: {result.output}')
    match = re.search(r'(\d{10})', result.output[0])
    last_restart = int(match.group(1))
    # print(f'server last restarted at: {last_restart}')
    set_bot_config(f'last_server_restart', f'{last_restart}')

    # print(f'end char info query {int_epoch_time()}')
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
    # print(f'Quest {quest_id} has been completed.')

    con.commit()
    con.close()

    return


def character_in_radius(trigger_x, trigger_y, trigger_z, trigger_radius, query_id: int = 0):
    nwPoint = [trigger_x - trigger_radius, trigger_y - trigger_radius]
    sePoint = [trigger_x + trigger_radius, trigger_y + trigger_radius]
    id_query = ''

    # connected_chars = []
    # print(f'{nwPoint} {sePoint}')
    if query_id:
        id_query = f'and char_id = {query_id} '

    results = db_query(False, f'select char_id, char_name from online_character_info '
                              f'where x >= {nwPoint[0]} and y >= {nwPoint[1]} '
                              f'and x <= {sePoint[0]} and y <= {sePoint[1]} '
                              f'and z >= {trigger_z - 100} {id_query}and z <= {trigger_z + 100} limit 1')
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
                f'values ({quest_id}, {char_id}, {int_epoch_time() + int(cooldown)})')

    con.commit()
    con.close()


def treasure_broadcast(override=False):
    if not override:
        treasure_last_announced = get_bot_config(f'treasure_last_announced')
        if int(treasure_last_announced) > int_epoch_time() - 3600:
            print(f'Skipping treasure broadcast, executed too recently')
            return

    location = get_bot_config(f'current_treasure_location')
    result = db_query(False, f'select location_name from treasure_locations where id = {location}')
    result = flatten_list(result)
    location_name = result[0]
    print(f'Broadcasting treasure location: {location_name}')
    set_bot_config(f'treasure_last_announced', int_epoch_time())
    # location_name = re.search(r'[0-9a-zA-Z\s\-]+', result)
    rcon_all(f'testFIFO 6 Treasure! {location_name}')


async def oneStepQuestUpdate(bot):
    # print(f'{int_epoch_time()}')

    character = RegistrationOLD()
    # character = Registration()
    if int(get_bot_config(f'maintenance_flag')) == 1:
        print(f'Skipping quest loop, server in maintenance mode')
        bot.quest_running = False
        return

    if int(get_bot_config(f'quest_toggle')) == 0:
        print(f'Skipping quest loop, quests are globally disabled')
        bot.quest_running = False
        return

    bot.quest_running = True
    # print(f'boop')

    quest_list = db_query(False, f'select quest_id, quest_name, active_flag, requirement_type, repeatable, '
                                 f'trigger_x, trigger_y, trigger_z, trigger_radius, '
                                 f'target_x, target_y, target_z '
                                 f'from one_step_quests')

    for quest in quest_list:
        character.reset()
        (quest_id, quest_name, active_flag, requirement_type, repeatable,
         trigger_x, trigger_y, trigger_z, trigger_radius, target_x, target_y, target_z) = quest

        char_id, char_name = character_in_radius(trigger_x, trigger_y, trigger_z, trigger_radius)


        if not char_id:
            # print(f'Skipping quest {quest_id}, no one in the box')
            continue

        character.id = char_id
        character.char_name = char_name

        if active_flag == 0:
            display_quest_text(999999, 0, False, char_name)
            continue

        # clear all fulfilled cooldowns
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
                treasure_target = get_treasure_target(character)
                if not treasure_target:
                    print(f'character has no treasure target, assigning one')
                    treasure_target = set_treasure_target(character)

                display_quest_text(0, 0, False, char_name, 6,
                                   f'Treasure!', f'{treasure_target.location_name}')
                print(f'Quest {quest_id} / {quest_name} completed by id {char_id} {char_name}')
                continue
            case 'Information':
                display_quest_text(quest_id, 0, False, char_name)
                add_cooldown(char_id, quest_id, repeatable)
                print(f'Quest {quest_id} / {quest_name} completed by id {char_id} {char_name}')
                continue
            case 'Presence':
                display_quest_text(quest_id, 0, False, char_name)
                grant_reward(char_id, char_name, quest_id, repeatable)
                if target_x:
                    run_console_command_by_name(char_name, f'teleportplayer {target_x} {target_y} {target_z}')
                print(f'Quest {quest_id} / {quest_name} completed by id {char_id} {char_name}')
                add_cooldown(char_id, quest_id, repeatable)
                continue
            case 'Meteor':
                if target_x:
                    run_console_command_by_name(char_name, f'teleportplayer {target_x} {target_y} {target_z}')
                grant_reward(char_id, char_name, quest_id, repeatable)
                print(f'Quest {quest_id} / {quest_name} completed by id {char_id} {char_name}')
                add_cooldown(char_id, quest_id, repeatable)
                continue
            case 'BringItems':
                missingitem = 0
                req_list = db_query(False, f'select template_id, item_qty '
                                           f'from quest_requirements where quest_id = {quest_id}')
                for requirement in req_list:
                    (template_id, item_qty) = requirement
                    inventoryHasItem, found_item_id = check_inventory(char_id, 0, template_id)
                    if inventoryHasItem >= 0:
                        consume_from_inventory(char_id, char_name, template_id, inventoryHasItem)
                    else:
                        missingitem += 1
                        print(f'Skipping quest {quest_id} / {quest_name}, id {char_id} {char_name} '
                              f'does not have the required item {template_id}')
                        continue
                if missingitem == 0:
                    display_quest_text(quest_id, 0, False, char_name)
                    grant_reward(char_id, char_name, quest_id, repeatable)
                    print(f'Quest {quest_id} / {quest_name}completed by id {char_id} {char_name}')
                    add_cooldown(char_id, quest_id, repeatable)
                    if target_x:
                        run_console_command_by_name(char_name, f'teleportplayer {target_x} {target_y} {target_z}')
            case 'Blacksmith' | 'Armorer' | 'Archivist' | 'Tamer':
                player_tier = get_profession_tier(char_id, requirement_type)
                if player_tier.turn_ins_this_cycle >= int(get_bot_config(f'profession_cycle_limit')):
                    print(f'Skipping quest {quest_id}/ {quest_name} , id {char_id} {char_name}, at cycle limit')
                    display_quest_text(quest_id, 0, True, char_name,
                                       2, f'Exceeded', f'Limit for this cycle')
                    continue

                # get_favor(char_id, 'VoidforgedExiles')
                objective = get_current_objective(requirement_type, player_tier.tier)

                inventoryHasItem, found_item_id = check_inventory(char_id, 0, objective.item_id)
                if inventoryHasItem >= 0:
                    consume_from_inventory(char_id, char_name, found_item_id, inventoryHasItem)
                    display_quest_text(quest_id, 0, False, char_name)
                    await give_profession_xp(
                        player_tier.char_id, char_name, player_tier.profession, player_tier.tier, bot)
                    grant_reward(char_id, char_name, quest_id, repeatable, player_tier.tier)
                    #give_favor(player_tier.char_id, 'VoidforgedExiles', player_tier.tier)
                    print(f'Quest {quest_id} / {quest_name} completed by id {char_id} {char_name}')
                    continue

                else:
                    # display_quest_text(quest_id, 0, True, char_name)
                    display_quest_text(0, 0, False, char_name,
                                       5, 'Missing', objective.item_name)
                    print(f'Skipping quest {quest_id}/ {quest_name}, id {char_id} {char_name} '
                          f'does not have the required item {objective.item_id} / {objective.item_name}')
                    continue
            case 'Slayer':
                print(f'Quest {quest_id} / {quest_name} completed by id {char_id} {char_name}')
                current_target = get_slayer_target(character)
                if not current_target:
                    # print(f'character has no quarry, assigning one')
                    # no current target, set one
                    current_target = set_slayer_target(character)
                    notorious_target, notorious_multiplier = get_notoriety(current_target)
                    if notorious_multiplier > 0:
                        display_quest_text(0, 0, False, char_name, 6,
                                           f'Notorious!', f' Quarry: {current_target.display_name}')
                    else:
                        display_quest_text(0, 0, False, char_name, 6,
                                           f'Quarry:', f'{current_target.display_name}')
                # else:
                #     # has a current target, check if killed
                #     if killed_target(current_target, character):
                #         # print(f'{current_target.display_name} has been killed by {character.char_name}')
                #         favor_to_give = int(get_bot_config(f'slayer_favor_per_kill'))
                #         modify_favor(char_id, 'slayer', favor_to_give)
                #
                #         notorious_target, notorious_multiplier = get_notoriety(current_target)
                #         # print(f'{notorious_target} {notorious_multiplier} in killed_target')
                #         if notorious_multiplier > 0:
                #             display_quest_text(0, 0, False, char_name, 7,
                #                                f'Notorious Beast Slain!', f'{current_target.display_name}')
                #         else:
                #             display_quest_text(0, 0, False, char_name, 7,
                #                                f'Slain', f'{current_target.display_name}')
                #         grant_reward(char_id, char_name, quest_id, repeatable)
                #         clear_slayer_target(character)
                else:
                    # print(f'displaying existing quarry')
                    display_quest_text(0, 0, False, char_name, 6,
                                       f'Quarry:', f'{current_target.display_name}')
                continue
            case 'Provisioner' | 'Reliquarian':
                # item_qty here is used for how many points will be awarded for the item
                missingitem = 0
                item_qty = 0
                found_item_id = 0

                req_list = db_query(False, f'select template_id, item_qty '
                                           f'from quest_requirements where quest_id = {quest_id}')
                favor_list = db_query(False, f'select template_id, favor from favor_reward_values '
                                             f'where profession = \'{requirement_type.lower()}\'')
                favor_dict = dict(favor_list)
                item_name_list = db_query(False, f'select template_id, item_name from favor_reward_values '
                                             f'where profession = \'{requirement_type.lower()}\'')
                item_name_dict = dict(item_name_list)
                selection_string = ', '.join(str(i) for i in favor_dict.keys())
                # print(f'{selection_string}')
                for requirement in req_list:
                    # (template_id, item_qty) = requirement
                    inventoryHasItem, found_item_id = check_inventory(char_id, 0, selection_string)
                    # print(inventoryHasItem)
                    # print(found_item_id)
                    if inventoryHasItem >= 0:
                        consume_from_inventory(char_id, char_name, found_item_id, inventoryHasItem)
                    else:
                        missingitem += 1
                        print(f'Skipping quest {quest_id}, id {char_id} {char_name} '
                              f'does not have the required item {selection_string}')
                        continue
                if missingitem == 0:
                    # display_quest_text(quest_id, 0, False, char_name)
                    display_quest_text(quest_id, 0, False, char_name,
                                       6, 'Delivered', item_name_dict.get(found_item_id))
                    # print(f'{item_qty}')
                    modify_favor(char_id, requirement_type.lower(), favor_dict.get(found_item_id))
                    print(f'Quest {quest_id} / {quest_name} completed by id {char_id} {char_name}')
                    add_cooldown(char_id, quest_id, repeatable)
                    grant_reward(char_id, char_name, quest_id, repeatable)

    bot.quest_running = False


class QuestSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='clearquesthistory')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
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
    @commands.check(check_channel)
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
    @commands.check(check_channel)
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
    @commands.check(check_channel)
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
    @commands.check(check_channel)
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
