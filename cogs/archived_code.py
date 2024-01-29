# @commands.command(name='market')
# @commands.has_any_role('Outcasts')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def market(self, ctx):
#     """- Teleports you to the market.
#
#     Parameters
#     ----------
#     ctx
#
#     Returns
#     -------
#
#     """
#     if '0' in get_bot_config('market_night'):
#         await ctx.reply(f'This command can only be used during Market Night!')
#         return
#
#     character = is_registered(ctx.author.id)
#
#     if not character:
#         await ctx.reply(f'No character registered to player {ctx.author.mention}!')
#         return
#     else:
#         name = character.char_name
#
#     rconCharId = get_rcon_id(character.char_name)
#     if not rconCharId:
#         await ctx.reply(f'Character `{name}` must be online to teleport to the Market!')
#         return
#     else:
#         runRcon(f'con {rconCharId} TeleportPlayer -14452.919922 209139.703125 -17296.822266') #outcast
#         #runRcon(f'con {rconCharId} TeleportPlayer -14412.728516 34739.1875 -8678.910156') #midnight lotus
#         await ctx.reply(f'Teleported `{name}` to the Market.')
#         return

#
# @commands.command(name='eldarium',
#                   aliases=['Eldarium', 'eld', 'e'])
# @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def eldarium(self, ctx, gold_coins: int = 0, gold_bars: int = 0):
#     """- Calculated Decaying Eldarium value for a list of materials.
#
#     Returns the spawnitem command for pasting into the game console.
#
#     Example: 3,245 gold coins and 202 gold ingots
#     Usage: v/eld 3245 202
#
#     Parameters
#     ----------
#     ctx
#     gold_coins
#     gold_bars
#
#     Returns
#     -------
#
#     """
#
#     leftover = gold_coins % 10
#     print(leftover)
#     rounded_gold_coins = math.floor(gold_coins * 10) / 10
#     print(rounded_gold_coins)
#
#     converted = int((rounded_gold_coins / 10)) + (int(gold_bars) * 3)
#     await ctx.send(f'`{leftover}` gold coins rounded off.\n'
#                    f'Decaying Eldarium conversion for `{int(rounded_gold_coins)}` '
#                    f'gold coins, `{gold_bars}` gold bars = `{converted}`:\n\n`spawnitem 11499 {converted}`')

# @commands.command(name='s3_eldarium')
# @commands.has_any_role('Admin')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def s3_eldarium(self, ctx, stacks: int, heads: int, keys: int, skulls: int):
#     """- Calculates Eldarium value for a list of materials.
#
#     Returns the spawnitem command for pasting into the game console.
#     ===============================================
#
#     Example: For 10 Stacks of materials, 3 Dragon Heads, 6 Skeleton Keys, and 72 Sorcerer Skulls
#
#     Usage: v/eld 10 3 6 72
#
#     Parameters
#     ----------
#     ctx
#     stacks
#         - Stacks of Materials (worth 25)
#     heads
#         - Dragon Heads (worth 25)
#     keys
#         - Skeleton Keys (worth 5)
#     skulls
#         - Sorcerer Skulls (worth 1)
#
#     Returns
#     -------
#
#     """
#
#     converted = str((stacks * 25) + (heads * 25) + (keys * 5) + skulls)
#     await ctx.send(f'Eldarium conversion for {stacks} stacks, {heads} heads, {keys} keys, {skulls} skulls:' +
#                    f'\n`spawnitem 11498 {str(converted)}`')


"""
@commands.command(name='claim')
@commands.has_any_role('Outcasts')
@commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
@commands.check(publicChannel)
async def claim(self, ctx):
"""
"""- Delivers veteran or helper rewards to your character

Parameters
----------
ctx

Returns
-------

"""

"""
character = is_registered(ctx.author.id)

if not character:
    await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
    return

rconCharId = get_rcon_id(character.char_name)
if not rconCharId:
    await ctx.reply(f'Character {character.char_name} must be online to claim rewards.')
    return

results = db_query(f'select discord_id from reward_claim '
                   f'where discord_id = {ctx.author.id} and claim_type = {ANNIVERSARY_ROLE}')

if results:
    for result in results:
        if result[0] == ctx.author.id:
            await ctx.reply(f'No rewards are available for you to claim.')
            return
        else:
            pass
else:
    role = ctx.author.get_role(ANNIVERSARY_ROLE)
    if role:
        message = await ctx.reply(f'You qualify for the Band of Outcasts 1st Anniversary Reward! '
                                  f'Please wait...')
        rconCommand = f'con {rconCharId} spawnitem 29034 1'
        if rconCommand:
            rconResponse = runRcon(rconCommand)
            if rconResponse.error == 1:
                await ctx.send(f'Authentication error on {rconCommand}')
                return

        reward_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        reward_cur = reward_con.cursor()

        insertResults = reward_cur.execute(f'insert into reward_claim (discord_id,claim_type) '
                                           f'values ({ctx.author.id},{ANNIVERSARY_ROLE})')
        reward_con.commit()

        if insertResults:
            await message.edit(content=f'Granted {role.name} reward to {character.char_name}. '
                                       f'Check your inventory!')
            reward_con.close()
            return
        else:
            await message.edit(content=f'Error when granting {role.name} reward to {character.char_name}.')
            return

    #sql select all records from the faith claim table that match character id and are not older than 2 weeks
    #output those into a list
    #loop through list to grant each item.

    else:
        await ctx.reply(f'No rewards are available for you to claim.')
        return
"""

""" Veteran reward
role = ctx.author.get_role(VETERAN_ROLE)
if role:
    message = await ctx.reply(f'You qualify for a veteran reward! Please wait...')
    rconCommand = f'con {rconCharId} spawnitem 10002 1'
    #rconCommand = f'con {rconCharId} say spawnitem 11108 777'
    if rconCommand:
        rconResponse = runRcon(rconCommand)
        if rconResponse.error == 1:
            await ctx.send(f'Authentication error on {rconCommand}')
            print(f'auth1')
            return

    rconCommand = f'con {rconCharId} spawnitem 10001 1'
    #rconCommand = f'con {rconCharId} say spawnitem 16002 900'
    if rconCommand:
        rconResponse = runRcon(rconCommand)
        if rconResponse.error == 1:
            await ctx.send(f'Authentication error on {rconCommand}')
            print(f'auth2')
            return

    reward_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    reward_cur = reward_con.cursor()

    insertResults = reward_cur.execute(f'insert into reward_claim (discord_id,claim_type) '
                                       f'values ({ctx.author.id},{VETERAN_ROLE})')
    reward_con.commit()
    """

'''@commands.command(name='fixstatus')
@commands.has_any_role('Admin')
@commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
@commands.check(modChannel)
async def fixStatus(self, ctx):
    """

    Parameters
    ----------
    ctx

    Returns
    -------

    """
    if not VeramaBot.liveStatus.is_running():
        VeramaBot.liveStatus.start()
        await ctx.send(f'Attempting to restart status monitor...')'''

# @commands.command(name='jail', aliases=['capture', 'prison'])
# @commands.has_any_role('Admin', 'Moderator')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def jail(self, ctx, cell: int, name: str):
#     """Sends the named player to Fort Greenwall
#
#     Parameters
#     ----------
#     ctx
#     cell
#         Cell number to summon the player to.
#     name
#         Player name to drop!
#
#     Returns
#     -------
#
#     """
#     rconCharId = get_rcon_id(name)
#     if not rconCharId:
#         await ctx.reply(f'Character `{name}` must be online to send to Fort Greenwall!')
#         return
#     else:
#         match cell:
#             case 0:
#                 runRcon(f'con {rconCharId} TeleportPlayer 218110.859375 -124766.046875 -16443.873047')
#             case 1:
#                 runRcon(f'con {rconCharId} TeleportPlayer 219121.40625 -126644.085938 -16396.664063')
#             case 2:
#                 runRcon(f'con {rconCharId} TeleportPlayer 218992.71875 -127653.546875 -16312.618164')
#             case 3:
#                 runRcon(f'con {rconCharId} TeleportPlayer 217231.015625 -127617.046875 -16296.007813')
#             case 4:
#                 runRcon(f'con {rconCharId} TeleportPlayer 217324.59375 -126616.6875 -16287.055664')
#             case _:
#                 await ctx.reply(f'Cell Number must be provided (0-4). 0 = Yard')
#                 return
#
#         await ctx.reply(f'Sent `{name}` to Fort Greenwall in cell {cell}.')
#         return

# async def runRcon3():
#     print(f'inside runRcon3')
#     print(f'{RCON_HOST}:{RCON_PORT} {RCON_PASS}')
#     rcon = AsyncRCON(f'{RCON_HOST}:{RCON_PORT}', f'{RCON_PASS}')
#     try:
#         print(f'trying')
#         await rcon.open_connection()
#     except AuthenticationException:
#         print('Login failed: Unauthorized.')
#         return
#
#     print(f'sending command')
#     res = await rcon.command(f'listplayers')
#     if not res:
#         print(f'nothing from server')
#     print(res)
#
#     rcon.close()
#
#     return res

# @tasks.loop(seconds=30)
# async def questChecker():
#
#     try:
#         await questUpdate()
#     except TimeoutError:
#         print(f'questUpdate took too long to complete.')

# @commands.command(name='resetquest')
# @commands.has_any_role('Admin', 'Moderator')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def resetquest(self, ctx, quest_id):
#     """
#
#     Parameters
#     ----------
#     ctx
#     quest_id
#
#     Returns
#     -------
#
#     """
#     try:
#         int(quest_id)
#     except ValueError:
#         await ctx.send(f'Quest ID must be an integer.')
#         return
#
#     reset_quest_progress(quest_id)
#
#     await ctx.send(f'Quest {quest_id} has been reset.')

# @commands.command(name='createquest')
# @commands.has_any_role('Admin')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def createquest(self, ctx, quest_id: int, quest_name: str):
#     """
#
#     Parameters
#     ----------
#     ctx
#     quest_id
#     quest_name
#
#     Returns
#     -------
#
#     """
#     try:
#         int(quest_id)
#         str(quest_name)
#     except ValueError:
#         await ctx.send(f'Input error.')
#         return
#
#     print(f'{quest_name}')
#
#     con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
#     cur = con.cursor()
#
#     cur.execute(f'insert or ignore into quest_tracker (quest_id, quest_name, quest_status, '
#                 f'quest_char_id, quest_char_name ) '
#                 f'values ( {quest_id}, \'{quest_name}\', 0, NULL, NULL )')
#
#     con.commit()
#     con.close()
#
#     await ctx.send(f'Added Quest {quest_id} - {quest_name}')


# @timeout(5, TimeoutError)
# async def questUpdate():
#
#     value = 0
#     char_name = ''
#     char_id = 0
#
#     questList = db_query(f'select quest_id, quest_name, quest_status, quest_char_id, quest_char_name,
#     quest_start_time '
#                          f'from quest_tracker')
#     print(f'{questList}')
#
#     for quest in questList:
#         quest_id = int(quest[0])
#         quest_name = str(quest[1])
#         quest_status = int(quest[2])
#         quest_char_id = quest[3]
#         quest_char_name = quest[4]
#         quest_start_time = quest[5]
#
#         #print(f'Looping through quest entry: {quest_id}, {quest_name}, {quest_status}, '
#         #      f'{quest_char_id}, {quest_char_name}')
#
#         questTriggers = db_query(f'select trigger_x, trigger_y, trigger_radius, trigger_type, template_id, '
#                                  f'target_x, target_y, target_z, spawn_name, spawn_qty, '
#                                  f'end_condition, target_container, step_ready '
#                                  f'from quest_triggers where quest_id = {quest_id} '
#                                  f'and quest_step_number = {quest_status}')
#
#         current_trigger = list(sum(questTriggers, ()))
#
#         (trigger_x, trigger_y, trigger_radius, trigger_type, template_id, target_x,
#          target_y, target_z, spawn_name, spawn_qty, end_condition, target_container, step_ready) = current_trigger
#
#         if not step_ready:
#             print(f'Quest {quest_id} - Step number {quest_status} is not ready')
#             continue
#
#         # rcon_id = get_rcon_id(f'{char_name}')
#         # if not rcon_id:
#         #     reset_quest_progress(quest_id)
#         #     continue
#
#         # step specific logic
#
#         # if not char_id == quest_char_id and quest_status > 0:
#         #     print(f'Quest {quest_id} is already in progress by {quest_char_name} with id {quest_char_id}')
#         #     runRcon(f'con {rcon_id} testFIFO 2 \"Sorry\" '
#         #             f'\"Quest is currently active. Come back later!\"')
#         #     continue
#
#         match trigger_type:
#             case 'Start':
#                 char_id, char_name = check_trigger_radius(quest_id, quest_name, trigger_x, trigger_y, trigger_radius)
#
#                 if not char_id and not char_name:
#                     continue
#
#                 display_quest_text(quest_id, quest_status, False, char_name)
#                 increment_step(quest_status, char_id, char_name, quest_id, int_epoch_time())
#
#                 continue
#
#             case 'Visit':
#                 char_id, char_name = check_trigger_radius(quest_id, quest_name, trigger_x, trigger_y, trigger_radius)
#
#                 if not char_id and not char_name:
#                     continue
#
#                 display_quest_text(quest_id, quest_status, False, char_name)
#                 increment_step(quest_status, char_id, char_name, quest_id, int_epoch_time())
#
#                 continue
#
#             case 'Bring Item' | 'Deliver':
#                 char_id, char_name = check_trigger_radius(quest_id, quest_name, trigger_x, trigger_y, trigger_radius)
#
#                 if not char_id and not char_name:
#                     continue
#
#                 inventoryHasItem = False
#
#                 if 'Bring Item' in trigger_type:
#                     inventoryHasItem = check_inventory(char_id, 0, template_id)
#                 if 'Deliver' in trigger_type:
#                     inventoryHasItem = check_inventory(target_container, 4, template_id)
#
#                 if inventoryHasItem:
#                     display_quest_text(quest_id, quest_status, False, char_name)
#                     increment_step(quest_status, char_id, char_name, quest_id, int_epoch_time())
#                     run_console_command_by_name_reset_quest(quest_id, char_name,
#                                                 f'teleportplayer {target_x} {target_y} {target_z}')
#                 else:
#                     display_quest_text(quest_id, quest_status, True, char_name)
#
#                 continue
#
#             case 'Steal':
#                 char_id, char_name = check_trigger_radius(quest_id, quest_name, trigger_x, trigger_y, trigger_radius)
#
#                 if not char_id and not char_name:
#                     continue
#
#                 inventoryHasItem = check_inventory(target_container, 4, template_id)
#
#                 if inventoryHasItem:
#                     display_quest_text(quest_id, quest_status, True, char_name)
#                 else:
#                     display_quest_text(quest_id, quest_status, False, char_name)
#                     increment_step(quest_status, char_id, char_name, quest_id, int_epoch_time())
#
#                     #This is not necessarily have to teleport....
#                     #run_console_command_by_name(quest_id, char_name,
#                     #                            f'teleportplayer {target_x} {target_y} {target_z}')
#
#             # case 'Spawn':
#             #     runRcon(f'con {rcon_id} dc spawn {spawn_qty} exact {spawn_name} silent s100')
#             #     rcon_id = get_rcon_id(f'{char_name}')
#             #     reset_quest_progress(quest_id)
#             #     if not rcon_id:
#             #         print(f'Reset quest due to offline character')
#             #         continue
#             #     runRcon(f'con {rcon_id} testFIFO 3 \"Zombies!\"')
#             #
#             #     if 'Deliver' in end_condition:
#             #         deliver_results = runRcon(f'sql select count(template_id) from item_inventory '
#             #                                   f'where owner_id = {target_container} '
#             #                                   f'and inv_type = 4 and template_id = {template_id}')
#             #         for result in deliver_results.output:
#             #             match = re.search(r'\s+\d+ | [^|]*', result)
#             #             print(f'{match}')
#             #             value = match[0]
#             #
#             #         if int(value) == 0:
#             #             print(f'Item has not been placed in the target container yet.')
#             #             continue
#             #
#             #         quest_status = increment_step(quest_status, char_id, char_name, quest_id)
#             #
#             #     continue
#
#             case 'Finish':
#                 char_id, char_name = check_trigger_radius(quest_id, quest_name, trigger_x, trigger_y, trigger_radius)
#
#                 if not char_id and not char_name:
#                     continue
#
#                 display_quest_text(quest_id, quest_status, False, char_name)
#
#                 run_console_command_by_name_reset_quest(quest_id, char_name, f'spawnitem {template_id} {spawn_qty}')
#
#                 run_console_command_by_name_reset_quest(quest_id, char_name, f'dc spawn kill')
#
#                 run_console_command_by_name_reset_quest(quest_id, char_name, f' teleportplayer
#                 {target_x} {target_y} {target_z}')
#
#                 complete_quest(quest_id, char_id)
#
#                 increment_step(quest_status, None, f'Waiting to be reset.', quest_id, int_epoch_time())
#
#                 continue
#
#             case 'ResetMe':
#                 inventoryHasItem = check_inventory(target_container, 4, template_id)
#
#                 if inventoryHasItem:
#                     reset_quest_progress(quest_id)
#                 else:
#                     print(f'Quest {quest_id} needs to be reset.')
#
#                 continue
#
#             case _:
#                 print(f'You done goofed.')
#                 continue
#
#         continue
#
#     # if not character:
#     #     await ctx.reply(f'**Proving Grounds Testing**\n'
#     #                     f'Could not find a character registered to {ctx.author.mention}.')
#     #     return
#     #
#     # rconCharId = get_rcon_id(character.char_name)
#     # if not rconCharId:
#     #     await ctx.reply(f'**Proving Grounds Testing**\n'
#     #                     f'Character {character.char_name} must be online to begin the Proving Grounds.')
#     #     return

# def check_trigger_radius(quest_id, quest_name, trigger_x, trigger_y, trigger_radius):
#     # this needs to be rewritten to move quest specific logic into the main function
#     nwPoint = [trigger_x - trigger_radius, trigger_y - trigger_radius]
#     sePoint = [trigger_x + trigger_radius, trigger_y + trigger_radius]
#
#     connected_chars = []
#
#     # if player is offline, they should not be selected
#     # look for players who are on the quest first before looking for any player
#     rconResponse = runRcon(f'sql select a.id, c.char_name from actor_position as a '
#                            f'left join characters as c on c.id = a.id '
#                            f'left join account as acc on acc.id = c.playerId '
#                            f'where x >= {nwPoint[0]} and y >= {nwPoint[1]} '
#                            f'and x <= {sePoint[0]} and y <= {sePoint[1]} '
#                            f'and a.class like \'%BasePlayerChar_C%\' '
#                            f'and acc.online = 1 limit 1')
#     rconResponse.output.pop(0)
#
#     if rconResponse.output:
#         match = re.findall(r'\s+\d+ | [^|]*', rconResponse.output[0])
#
#         connected_chars.append(match)
#         character_info = sum(connected_chars, [])
#
#         if character_info:
#             char_id = int(character_info[0].strip())
#             char_name = str(character_info[1].strip())
#
#             questHistory = db_query(f'select char_id from quest_history '
#                                     f'where char_id = {char_id} and quest_id = {quest_id}')
#             if questHistory:
#                 # if there are any records, the character has already completed this quest.
#                 print(f'Quest {quest_id} - {char_name} is in the box with character ID {char_id}, '
#                       f'but has already completed it..')
#                 rcon_id = get_rcon_id(f'{char_name}')
#                 if not rcon_id:
#                     reset_quest_progress(quest_id)
#                     return False, False
#
#                 runRcon(f'con {rcon_id} testFIFO 2 \"Complete!\" \"{quest_name}\"')
#
#                 return False, False
#
#             print(f'Quest {quest_id} - {char_name} is in the trigger area with character ID {char_id}.')
#             return char_id, char_name
#
#     else:
#         print(f'Quest {quest_id} - No one is in the trigger area.')
#         return False, False
# @commands.command(name='addwarp')
# @commands.has_any_role('Admin', 'Moderator')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def addwarp(self, ctx, description: str, warp_name: str, marker_label: str,
#                   x: float, y: float, z: float, marker_flag: str):
#     """
#
#     Parameters
#     ----------
#     ctx
#     description
#     warp_name
#     marker_label
#     x
#     y
#     z
#     marker_flag
#
#     Returns
#     -------
#
#     """
#     try:
#         str(description)
#         str(warp_name)
#         str(marker_label)
#         float(x)
#         float(y)
#         float(z)
#         str(marker_flag)
#     except TypeError:
#         await ctx.send(f'Error in one or more parameters.')


# @commands.command(name='warpaint')
# @commands.has_any_role('Outcasts')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def warpaint(self, ctx, option: str = commands.parameter(default='apply')):
#     """- Modifies your active warpaint so that it is not removed upon death.
#
#     Character must be offline to use this command. A normal warpaint must be applied before using this command.
#
#     Parameters
#     ----------
#     ctx
#     option
#         remove | apply
#
#     Returns
#     -------
#
#     """
#
#     outputString = f'Commencing warpaint death persistence process:\n'
#     message = await ctx.reply(content=outputString)
#
#     charId = is_registered(ctx.message.author.id)
#
#     if not charId:
#         outputString = f'No character registered to {ctx.message.author.mention}!'
#         await message.edit(content=outputString)
#         return
#
#     if get_rcon_id(charId.char_name):
#         outputString = f'Character `{charId.char_name}` must be offline to modify permanent warpaints!'
#         await message.edit(content=outputString)
#         return
#
#     rconCommand = f'sql delete from item_inventory where item_id = 25 and owner_id = {charId.id} and inv_type = 1'
#     rconResponse = runRcon(rconCommand)
#
#     if rconResponse.error == 1:
#         outputString = f'Error on {rconCommand}'
#         await message.edit(content=outputString)
#         return
#     else:
#         for x in rconResponse.output:
#             print(f'{x}')
#             outputString = f'Removed all persistent warpaints applied to `{charId.char_name}`.\n'
#             await message.edit(content=outputString)
#             if 'remove' in option.casefold():
#                 outputString += f'You may need to use Sloughing Fluid to fully remove the warpaint or tattoo.\n'
#                 await message.edit(content=outputString)
#                 return
#
#     rconCommand = (f'sql update or ignore item_inventory set item_id = 25 '
#                    f'where item_id = 11 and owner_id = {charId.id} and inv_type = 1')
#     rconResponse = runRcon(rconCommand)
#
#     if rconResponse.error == 1:
#         outputString = f'Error on {rconCommand}'
#         await message.edit(content=outputString)
#         return
#     else:
#         for x in rconResponse.output:
#             print(f'{x}')
#             outputString += (f'Successfully made the warpaint of `{charId.char_name}` persist through death.\n'
#                              f'Warpaints still expire after 1-4 hours. Log in and then use `v/tattoo` to make '
#                              f'it permanent.')
#             await message.edit(content=outputString)
#
# @commands.command(name='tattoo')
# @commands.has_any_role('Outcasts')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def tattoo(self, ctx, option: str = commands.parameter(default='apply')):
#     """- Convert your death-persistent warpaint into a tattoo that will not expire over time
#
#     Character must be online to use this command, and must have a persistent warpaint from v/warpaint
#
#     Parameters
#     ----------
#     ctx
#     option
#         remove | apply
#
#     Returns
#     -------
#
#     """
#     outputString = f'Commencing tattoo process:\n'
#     message = await ctx.reply(content=outputString)
#
#     charId = is_registered(ctx.message.author.id)
#
#     if not charId:
#         outputString = f'No character registered to {ctx.message.author.mention}!'
#         await message.edit(content=outputString)
#         return
#
#     if not get_rcon_id(charId.char_name):
#         outputString = f'Character `{charId.char_name}` must be online to convert warpaint into a tattoo!'
#         await message.edit(content=outputString)
#         return
#
#     rconId = get_rcon_id(charId.char_name)
#
#     if 'remove' in option.casefold():
#         outputString += f'Please log out and use `v/warpaint` to remove tattoos.\n'
#         await message.edit(content=outputString)
#         return
#
#     #rconCommand = f'con {rconId} setinventoryitemfloatstat 25 12 -1 1'
#     rconCommand = f'con {rconId} setinventoryitemfloatstat 25 7 100000000 1'
#     rconResponse1 = runRcon(rconCommand)
#     rconCommand = f'con {rconId} setinventoryitemfloatstat 25 8 100000000 1'
#     rconResponse2 = runRcon(rconCommand)
#
#     if rconResponse1.error == 1 or rconResponse2.error == 1:
#         outputString = f'Error on {rconCommand}'
#         await message.edit(content=outputString)
#         return
#     else:
#         for x in rconResponse1.output:
#             print(f'{x}')
#             outputString = f'Converted warpaint to tattoo for `{charId.char_name}`.\n'
#             await message.edit(content=outputString)

# def increment_step(quest_status, char_id, char_name, quest_id, quest_start_time):
#
#     quest_status += 1
#     con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
#     cur = con.cursor()
#
#     cur.execute(f'update quest_tracker set quest_status = ?, quest_char_id = ?, '
#                 f'quest_char_name = ?, quest_start_time = ? '
#                 f'where quest_id = ?', (quest_status, char_id, char_name, quest_start_time, quest_id))
#     print(f'Quest {quest_id} updated to step {quest_status}')
#
#     con.commit()
#     con.close()
#
#     return quest_status

# def reset_quest_progress(quest_id):
#
#     con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
#     cur = con.cursor()
#
#     cur.execute(f'update quest_tracker set quest_status = ?, quest_char_id = ?, '
#                 f'quest_char_name = ?, quest_start_time = ? where quest_id = ? ',
#                 (0, None, None, None, quest_id))
#
#     con.commit()
#     con.close()
#
#     print(f'Quest progress for quest {quest_id} has been reset.')
#
#     return

# def is_active_player_dead(char_id, quest_start_time):
#     result = runRcon(f'sql select ownerId from game_events '
#                      f'where ownerId = {char_id} and worldtime > {quest_start_time} and eventType = 103')
#     result.output.pop(0)
#
#     if result.output:
#         return False
#     else:
#         return True

# @commands.command(name='queststatus')
# @commands.has_any_role('Admin', 'Moderator')
# @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
# async def queststatus(self, ctx):
#     """
#
#     Parameters
#     ----------
#     ctx
#
#     Returns
#     -------
#
#     """
#
#     output = db_query(f'select quest_id, quest_name, quest_char_name from quest_tracker')
#
#     for record in output:
#         if record[2]:
#             await ctx.send(f'{record[1]} ({record[0]}) - `{record[2]}`')
#         else:
#             await ctx.send(f'{record[1]} ({record[0]}) - `Available`')
