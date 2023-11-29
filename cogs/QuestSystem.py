import re
import sqlite3
import time

from datetime import datetime
from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id
from functions.externalConnections import runRcon, db_query

def increment_step(quest_status, char_id, char_name, quest_id, quest_start_time):

    quest_status += 1
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'update quest_tracker set quest_status = {quest_status}, quest_char_id = {char_id}, '
                f'quest_char_name = \'{char_name}\', quest_start_time = {quest_start_time} '
                f'where quest_id = {quest_id}')
    print(f'Quest {quest_id} updated to step {quest_status}')

    con.commit()
    con.close()

    return quest_status

def complete_quest(quest_id: int, char_id: int):

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'update quest_tracker set quest_status = 0, '
                f'quest_char_id = NULL, '
                f'quest_char_name = NULL '
                f'where quest_id = {quest_id}')
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

    questText = db_query(f'select Style, Text1, Text2, AltStyle, AltText1, AltText2 from quest_text '
                         f'where quest_id = {quest_id} and step_number = {quest_status}')
    print(f'{questText}')

    for record in questText:
        style = record[0]
        text1 = record[1]
        text2 = record[2]
        altStyle = record[3]
        altText1 = record[4]
        altText2 = record[5]

    if alt:
        run_console_command_by_name(quest_id, char_name,
                                    f'testFIFO {altStyle} \"{altText1}\" \"{altText2}\"')
    else:
        run_console_command_by_name(quest_id, char_name,
                                    f'testFIFO {style} \"{text1}\" \"{text2}\"')

    return

def reset_quest_progress(quest_id):

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'update quest_tracker set quest_status = ?, quest_char_id = ?, '
                f'quest_char_name = ?, quest_start_time = ? where quest_id = ? ',
                (0, None, None, None, quest_id))

    con.commit()
    con.close()

    print(f'Quest progress for quest {quest_id} has been reset.')

    return

def run_console_command_by_name(quest_id: int, char_name: str, command: str):

    rcon_id = get_rcon_id(f'{char_name}')
    if not rcon_id:
        reset_quest_progress(quest_id)
        return False
    else:
        print(f'{command}')
        runRcon(f'con {rcon_id} {command}')

    return

def check_inventory(owner_id, inv_type, template_id):

    results = runRcon(f'sql select template_id from item_inventory '
                      f'where owner_id = {owner_id} and inv_type = {inv_type} '
                      f'and template_id = {template_id} limit 1')
    if results.output:
        results.output.pop(0)
        if not results.output:
            print(f'The required item {template_id} is missing from the inventory of {owner_id}.')
            return False
    else:
        print(f'Should this ever happen?')

    for result in results.output:
        match = re.search(r'\s+\d+ | [^|]*', result)
        print(f'{match}')
        value = match[0]

    if int(value) == template_id:
        print(f'The required item {template_id} is is present in the inventory of {owner_id}.')
        return True

    return False

def int_epoch_time():
    current_time = datetime.now()
    epoch_time = int(round(current_time.timestamp()))

    return epoch_time

def is_active_player_dead(char_id, quest_start_time):
    result = runRcon(f'sql select ownerId from game_events '
                     f'where ownerId = {char_id} and worldtime > {quest_start_time} and eventType = 103')
    result.output.pop(0)

    if result.output:
        return False
    else:
        return True

async def questUpdate():

    value = 0

    questList = db_query(f'select quest_id, quest_name, quest_status, quest_char_id, quest_char_name, quest_start_time '
                         f'from quest_tracker')
    print(f'{questList}')

    for quest in questList:
        quest_id = int(quest[0])
        quest_name = str(quest[1])
        quest_status = int(quest[2])
        quest_char_id = quest[3]
        quest_char_name = quest[4]
        quest_start_time = quest[5]

        print(f'Looping through quest entry: {quest_id}, {quest_name}, {quest_status}, '
              f'{quest_char_id}, {quest_char_name}')

        questTriggers = db_query(f'select trigger_x, trigger_y, trigger_radius, trigger_type, template_id, '
                                 f'target_x, target_y, target_z, spawn_name, spawn_qty, '
                                 f'end_condition, target_container, step_ready '
                                 f'from quest_triggers where quest_id = {quest_id} '
                                 f'and quest_step_number = {quest_status}')
        print(f'Looking for character within: {questTriggers}')

        for trigger in questTriggers:
            trigger_x = trigger[0]
            trigger_y = trigger[1]
            trigger_radius = trigger[2]
            trigger_type = trigger[3]
            template_id = trigger[4]
            target_x = trigger[5]
            target_y = trigger[6]
            target_z = trigger[7]
            spawn_name = trigger[8]
            spawn_qty = trigger[9]
            end_condition = trigger[10]
            target_container = trigger[11]
            step_ready = trigger[12]

            if not step_ready:
                print(f'Step number {quest_status} is not ready')
                continue

            nwPoint = [trigger_x - trigger_radius, trigger_y - trigger_radius]
            sePoint = [trigger_x + trigger_radius, trigger_y + trigger_radius]

            connected_chars = []

            #check for corpses
            # rconResponse = runRcon(f'sql select a.id from actor_position as a '
            #                        f'where x >= {nwPoint[0]} and y >= {nwPoint[1]} '
            #                        f'and x <= {sePoint[0]} and y <= {sePoint[1]} '
            #                        f'and a.class like \'%Corpse_C%\' limit 1')
            # rconResponse.output.pop(0)
            #
            # if rconResponse.output:

            #if player is offline, they should not be selected
            rconResponse = runRcon(f'sql select a.id, c.char_name from actor_position as a '
                                   f'left join characters as c on c.id = a.id '
                                   f'left join account as acc on acc.id = c.playerId '
                                   f'where x >= {nwPoint[0]} and y >= {nwPoint[1]} '
                                   f'and x <= {sePoint[0]} and y <= {sePoint[1]} '
                                   f'and a.class like \'%BasePlayerChar_C%\' '
                                   f'and acc.online = 1 limit 1')
            # f'and c.id not in '
            # f'( select ownerId from game_events '
            # f'where eventType = 103 and worldTime >= {quest_start_time}
            rconResponse.output.pop(0)

            if rconResponse.output:
                for line in rconResponse.output:
                    match = re.findall(r'\s+\d+ | [^|]*', line)
                    connected_chars.append(match)
            else:
                print(f'Quest {quest_id} - No one is in the box.')
                continue

            for character in connected_chars:
                char_name = character[1].strip()
                char_id = int(character[0].strip())
                print(f'Player {char_name} is in the box with character ID {char_id}.')

                questHistory = db_query(f'select char_id from quest_history '
                                        f'where char_id = {char_id} and quest_id = {quest_id}')
                print(f'{questHistory}')
                if questHistory:
                    #if there are any records, the character has already completed this quest.
                    print(f'{char_name} has already completed quest {quest_id}')
                    rcon_id = get_rcon_id(f'{char_name}')
                    if not rcon_id:
                        continue
                    runRcon(f'con {rcon_id} testFIFO 2 \"Complete!\" \"{quest_name}\"')
                    continue

                rcon_id = get_rcon_id(f'{char_name}')
                if not rcon_id:
                    reset_quest_progress(quest_id)
                    continue

                # step specific logic

                if not char_id == quest_char_id and quest_status > 0:
                    print(f'Quest {quest_id} is already in progress by {quest_char_name} with id {quest_char_id}')
                    runRcon(f'con {rcon_id} testFIFO 2 \"Sorry\" '
                            f'\"Quest is currently active. Come back later!\"')
                    continue

                match trigger_type:
                    case 'Start' | 'Visit':
                        display_quest_text(quest_id, quest_status, False, char_name)
                        quest_status = increment_step(quest_status, char_id, char_name, quest_id, int_epoch_time())

                        continue

                    case 'Bring Item' | 'Deliver':
                        inventoryHasItem = False

                        if 'Bring Item' in trigger_type:
                            inventoryHasItem = check_inventory(char_id, 0, template_id)
                        if 'Deliver' in trigger_type:
                            inventoryHasItem = check_inventory(target_container, 4, template_id)

                        if inventoryHasItem:
                            display_quest_text(quest_id, quest_status, False, char_name)
                            quest_status = (
                                increment_step(quest_status, char_id, char_name, quest_id, int_epoch_time()))
                            run_console_command_by_name(quest_id, char_name,
                                                        f'teleportplayer {target_x} {target_y} {target_z}')
                        else:
                            display_quest_text(quest_id, quest_status, True, char_name)

                        continue

                    case 'Steal':
                        inventoryHasItem = check_inventory(target_container, 4, template_id)

                        if inventoryHasItem:
                            display_quest_text(quest_id, quest_status, True, char_name)
                        else:
                            display_quest_text(quest_id, quest_status, False, char_name)
                            quest_status = (
                                increment_step(quest_status, char_id, char_name, quest_id, int_epoch_time()))
                            #This is not necessarily have to teleport....
                            #run_console_command_by_name(quest_id, char_name,
                            #                            f'teleportplayer {target_x} {target_y} {target_z}')

                    # case 'Spawn':
                    #     runRcon(f'con {rcon_id} dc spawn {spawn_qty} exact {spawn_name} silent s100')
                    #     rcon_id = get_rcon_id(f'{char_name}')
                    #     reset_quest_progress(quest_id)
                    #     if not rcon_id:
                    #         print(f'Reset quest due to offline character')
                    #         continue
                    #     runRcon(f'con {rcon_id} testFIFO 3 \"Zombies!\"')
                    #
                    #     if 'Deliver' in end_condition:
                    #         deliver_results = runRcon(f'sql select count(template_id) from item_inventory '
                    #                                   f'where owner_id = {target_container} '
                    #                                   f'and inv_type = 4 and template_id = {template_id}')
                    #         for result in deliver_results.output:
                    #             match = re.search(r'\s+\d+ | [^|]*', result)
                    #             print(f'{match}')
                    #             value = match[0]
                    #
                    #         if int(value) == 0:
                    #             print(f'Item has not been placed in the target container yet.')
                    #             continue
                    #
                    #         quest_status = increment_step(quest_status, char_id, char_name, quest_id)
                    #
                    #     continue

                    case 'Finish':
                        display_quest_text(quest_id, quest_status, False, char_name)

                        run_console_command_by_name(quest_id, char_name, f'spawnitem {template_id} {spawn_qty}')

                        run_console_command_by_name(quest_id, char_name, f'dc spawn kill')

                        run_console_command_by_name(quest_id, char_name, f' teleportplayer {target_x} {target_y} {target_z}')

                        complete_quest(quest_id, char_id)

                        continue

                    case _:
                        print(f'You done goofed.')
                        continue

                continue

        continue

    # if not character:
    #     await ctx.reply(f'**Proving Grounds Testing**\n'
    #                     f'Could not find a character registered to {ctx.author.mention}.')
    #     return
    #
    # rconCharId = get_rcon_id(character.char_name)
    # if not rconCharId:
    #     await ctx.reply(f'**Proving Grounds Testing**\n'
    #                     f'Character {character.char_name} must be online to begin the Proving Grounds.')
    #     return


class QuestSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='resetquest')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def resetquest(self, ctx, quest_id):
        """

        Parameters
        ----------
        ctx
        quest_id

        Returns
        -------

        """
        try:
            int(quest_id)
        except ValueError:
            await ctx.send(f'Quest ID must be an integer.')
            return

        reset_quest_progress(quest_id)

        await ctx.send(f'Quest {quest_id} has been reset.')

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

        await ctx.send(f'Quest History for quest {quest_id} / player {char_id} has been reset.')

    @commands.command(name='queststatus')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def queststatus(self, ctx, quest_id):
        """

        Parameters
        ----------
        ctx
        quest_id

        Returns
        -------

        """
        try:
            int(quest_id)
        except ValueError:
            await ctx.send(f'Quest ID must be an integer.')
            return

        output = db_query(f'select * from quest_tracker where quest_id = {quest_id}')

        await ctx.send(f'Quest Status:\n{output}')

    @commands.command(name='createquest')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def createquest(self, ctx, quest_id: int, quest_name: str):
        """

        Parameters
        ----------
        ctx
        quest_id
        quest_name

        Returns
        -------

        """
        try:
            int(quest_id)
            str(quest_name)
        except ValueError:
            await ctx.send(f'Input error.')
            return

        print(f'{quest_name}')

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'insert or ignore into quest_tracker (quest_id, quest_name, quest_status, '
                    f'quest_char_id, quest_char_name ) '
                    f'values ( {quest_id}, \'{quest_name}\', 0, NULL, NULL )')

        con.commit()
        con.close()

        await ctx.send(f'Added Quest {quest_id} - {quest_name}')

    @commands.command(name='addqueststep')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def addqueststep(self, ctx, trigger_type: str, quest_id: int, quest_step_number: int, trigger_x: float,
                           trigger_y: float, trigger_z: float, trigger_radius: int, target_x, target_y,
                           target_z, target_radius, template_id, spawn_name, spawn_qty, end_condition,
                           target_container, step_ready: int):
        """

        Parameters
        ----------
        ctx
        trigger_type
        quest_id
        quest_step_number
        target_x
        target_y
        target_z
        trigger_radius
        template_id
        target_container
        trigger_x
        trigger_y
        trigger_z
        spawn_name
        spawn_qty
        end_condition
        target_radius
        step_ready

        Returns
        -------

        """
        try:
            str(trigger_type)
            int(quest_id)
            int(quest_step_number)
            float(trigger_x)
            float(trigger_y)
            float(trigger_z)
            int(trigger_radius)
            int(step_ready)
        except ValueError:
            await ctx.send(f'Input error.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'insert or ignore into quest_triggers (trigger_type, quest_id, quest_step_number, trigger_x, '
                    f'trigger_y, trigger_z, trigger_radius, target_x, target_y, '
                    f'target_z, target_radius, template_id, spawn_name, spawn_qty, end_condition, '
                    f'target_container, step_ready ) '
                    f'values ( \'{trigger_type}\', {quest_id}, {quest_step_number}, {trigger_x}, '
                    f'{trigger_y}, {trigger_z}, {trigger_radius}, {target_x}, {target_y}, '
                    f'{target_z}, {target_radius}, {template_id}, \'{spawn_name}\', {spawn_qty}, \'{end_condition}\', '
                    f'{target_container}, {step_ready} )')

        con.commit()
        con.close()

        await ctx.send(f'Added Quest Trigger Step {quest_id} - {quest_step_number} \'{trigger_type}\'')

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(QuestSystem(bot))
