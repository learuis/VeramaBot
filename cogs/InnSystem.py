import hashlib
import os
import re

from discord.ext import commands
from dotenv import load_dotenv

from functions.common import is_registered, get_clan, flatten_list, get_rcon_id, int_epoch_time, get_bot_config, \
    get_single_registration_new, no_registered_char_reply, check_channel, eld_transaction, get_balance, \
    transform_coordinates
from cogs.QuestSystem import character_in_radius
from functions.externalConnections import db_query, runRcon

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))


class Character:
    def __init__(self):
        self.id = 0
        self.char_name = ''


class Inn:
    def __init__(self):
        self.inn_id = ''
        self.clan_id = 0
        self.owner_id = 0
        self.name = ''
        self.x = 0
        self.y = 0
        self.z = 0
        self.map_square = ''
        self.loc_map = ''
        self.teleport_counter = 0
        self.subsidized_amount = 0

    def structure_inn(self, inn_id, clan_id, owner_id, name, x, y, z, map_square, loc_map, teleport_counter, subsidized_amount):
        self.inn_id = inn_id
        self.clan_id = clan_id
        self.owner_id = owner_id
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.map_square = map_square
        self.loc_map = loc_map
        self.teleport_counter = teleport_counter
        self.subsidized_amount = subsidized_amount
        return self


class Checkin:
    def __init__(self):
        self.char_id = 0
        self.inn_id = ''


def carpets_in_range(x, y, radius, clan_id):
    carpet_id = 0
    nwPoint = [x - radius, y - radius]
    sePoint = [x + radius, y + radius]

    rconResponse = runRcon(f'sql select b.object_id from actor_position a left join buildings b on a.id = b.object_id '
                           f'where b.owner_id = {clan_id} '
                           f'and x > {nwPoint[0]} and y > {nwPoint[1]} '
                           f'and x < {sePoint[0]} and y < {sePoint[1]} '
                           f'and ( a.class like \'%carpet%\' or a.class like \'%rug%\' ) limit 1;')

    for x in rconResponse.output:
        print(x)
        match = re.search(r'#\b\d\s+(\d+)', x)
        if match:
            match.group(1)
            carpet_id = int(match.group(1))

    return carpet_id

def get_all_inns():
    inn_list = []

    results = db_query(False, f'select inn_id, clan_id, owner_id, inn_name, x, y, z, '
                               f'map_square, loc_map, teleport_counter, subsidized_amount from inn_locations')
    if not results:
        return False
    for result in results:
        inn_id = result[0]
        inn = get_inn_details(inn_id)
        inn_list.append(inn)

    print(inn_list)
    return inn_list

def get_all_checkin_details(character):
    checkin = Checkin()
    inn_list = []

    results = db_query(False, f'select checkins.inn_id from inn_checkins as checkins '
                              f'left join inn_locations as locs on checkins.inn_id = locs.inn_id '
                              f'where checkins.char_id = {character.id} order by checkins.checkin_id asc')
    if not results:
        return False
    for count, result in enumerate(results):
        sequence_id = count + 1
        inn_id = result[0]
        inn = get_inn_details(inn_id)
        inn_list.append(inn)

    print(inn_list)
    return inn_list

    # (checkin.char_id, checkin.inn_id, checkin.valid_until) = results

def is_checked_in(character, inn):
    checkin = Checkin()
    inn_list = []

    results = db_query(False, f'select inn_checkins.inn_id from inn_checkins  '
                              f'where inn_checkins.char_id = {character.id} and inn_checkins.inn_id = \'{inn.inn_id}\'')
    if results:
        return True
    else:
        return False

def count_checkins(clan_id):
    count = 0
    inn_id = get_inn_id(clan_id)

    results = db_query(False, f'select count(*) '
                              f'from inn_checkins as checkins '
                              f'left join inn_locations as locs on checkins.inn_id = locs.inn_id '
                              f'where checkins.inn_id = \'{inn_id}\'')
    if not results:
        return int(count)
    results = flatten_list(results)
    print(results)
    count = results[0]

    return int(count)

def does_object_exist(object_id):
    results = runRcon(f'sql select * from actor_position where id = {object_id}')
    if results.output:
        results.output.pop(0)
        print(results.output)
        if results.output:
            return True
        else:
            return False
    else:
        return False

def get_inn_details(inn_id: str):
    inn = Inn()
    results = db_query(False, f'select inn_id, clan_id, owner_id, inn_name, x,y,z, '
                              f'map_square, loc_map, teleport_counter, subsidized_amount '
                              f'from inn_locations where inn_id = \'{inn_id}\' limit 1')
    if results:
        results = flatten_list(results)
        print(results)
        inn = inn.structure_inn(results[0],results[1],results[2],results[3],results[4],results[5],
                                results[6],results[7],results[8],results[9], results[10])
        # (inn.inn_id, inn.clan_id, inn.owner_id, inn.name, inn.x, inn.y, inn.z,
        #  inn.map_square, inn.loc_map, inn.teleport_counter) = results
    return inn

def set_subsidized_amount(inn_id, amount):
    db_query(True, f'update inn_locations set subsidized_amount = {amount} where inn_id = \'{inn_id}\'')
    return

def checkin_to_inn(character, inn):
    length = int(get_bot_config(f'inn_checkin_length'))
    # checkout_time = int_epoch_time() + length
    db_query(True, f'delete from inn_checkins where char_id = {character.id} and inn_id = {inn.inn_id}')
    db_query(True, f'insert into inn_checkins (char_id, inn_id) '
                   f'values ({character.id}, \'{inn.inn_id}\')')
    return True


def clear_all_checkins(inn_id):
    db_query(True, f'delete from inn_checkins where inn_id = \'{inn_id}\'')
    return


def create_inn(inn):
    db_query(True, f'insert or replace into inn_locations '
                   f'(inn_id, clan_id, owner_id, inn_name, x, y, z, map_square, loc_map, teleport_counter, subsidized_amount) values '
                   f'(\'{inn.inn_id}\', {inn.clan_id}, {inn.owner_id}, \'{inn.name}\', '
                   f'\'{inn.x}\', \'{inn.y}\', \'{inn.z}\', \'{inn.map_square}\', \'{inn.loc_map}\', 0, 0)')


def delete_inn(inn_id):
    db_query(True, f'delete from inn_locations where inn_id = \'{inn_id}\'')
    return

def modify_inn(inn_id, inn_name):
    db_query(True, f'update inn_locations set inn_name = \'{inn_name}\' where inn_id = \'{inn_id}\'')
    return

def increment_inn_teleport_counter(inn: Inn):
    db_query(True, f'update inn_locations set teleport_counter = teleport_counter + 1 where inn_id = \'{inn.inn_id}\'')
    return

def get_inn_id(clan_id):
    inn_id = 0
    # inn_id = hashlib.md5(str(clan_id).encode('utf-8')).hexdigest()
    result = db_query(False, f'select inn_id from inn_locations where clan_id = \'{clan_id}\'')
    if result:
        result = flatten_list(result)
        inn_id = result[0]

    return inn_id

def inn_transaction(inn, character, cost, revenue, owner_character):
    if inn.subsidized_amount > 0:
        extra_output = f' (Subsidized)'
        if cost > 0:
            # guest pays cost, owner pays subsidy. no revenue
            eld_transaction(character, f'Inn TP to {inn.name}', -cost )
            eld_transaction(character, f'{character.char_name} teleported to {inn.name}{extra_output}', -inn.subsidized_amount)
        else:
            # owner pays subsidy. no revenue
            eld_transaction(owner_character, f'{character.char_name} teleported to {inn.name}{extra_output}', -cost)
    else:
        # guest pays cost. owner receives full revenue
        eld_transaction(character, f'Inn TP to {inn.name}', -cost)
        eld_transaction(owner_character, f'{character.char_name} teleported to {inn.name}', revenue)

    increment_inn_teleport_counter(inn)

    return


class InnSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # @commands.command(name='renameinn')
    # @commands.check(check_channel)
    # @commands.has_any_role('Outcasts')
    # async def renameinn(self, ctx, new_name: str = ''):
    #     """ - Renames your inn
    #
    #     Parameters
    #     ----------
    #     ctx
    #     new_name
    #         The new name for the inn
    #
    #     Returns
    #     -------
    #
    #     """
    #
    #     character = is_registered(ctx.author.id)
    #     if not character:
    #         await no_registered_char_reply(self.bot, ctx)
    #         # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
    #         return
    #
    #     clan_id, clan_name = get_clan(character)
    #     if not clan_id:
    #         await ctx.reply(f'`{character.char_name}` must be in a clan to rename an inn!')
    #         return
    #
    #     if not new_name:
    #         await ctx.reply(f'Provide the new name for the inn, surrounded by "double quotes"')
    #         return
    #
    #     # inn_id = hashlib.md5(str(clan_id).encode('utf-8')).hexdigest()
    #     inn_id = clan_id
    #     old_inn = get_inn_details(inn_id)
    #
    #     if inn_id:
    #         modify_inn(old_inn.inn_id,new_name)
    #         await ctx.reply(f'`{old_inn.name}` owned by `{character.char_name}` has been renamed to `{new_name}`!')
    #         return
    #     else:
    #         await ctx.reply(f'There is no inn registered to `{character.char_name}`!')
    #         return

    @commands.command(name='closeinn')
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def closeinn(self, ctx, confirm: str = ''):
        """ - Closes your current inn

        Parameters
        ----------
        ctx
        confirm
            Type confirm to finalize closure of your inn

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        clan_id, clan_name = get_clan(character)
        if not clan_id:
            await ctx.reply(f'`{character.char_name}` must be in a clan to establish an inn!')
            return

        # inn_id = hashlib.md5(str(clan_id).encode('utf-8')).hexdigest()
        inn_id = get_inn_id(clan_id)
        inn = get_inn_details(inn_id)

        if inn_id:
            if 'confirm' in confirm:
                clear_all_checkins(inn.inn_id)
                delete_inn(inn.inn_id)
                await ctx.reply(f'`{inn.name}` owned by `{character.char_name}` has been closed and all '
                                f'guests have been checked out.')
                return

            else:
                await ctx.reply(f'This command will close your inn, ending all current check-ins. '
                                f'\nIf you are sure you want to do this, use `v/closeinn confirm`')
                return
        else:
            await ctx.reply(f'There is no inn registered to `{character.char_name}`!')
            return

    @commands.command(name='establishinn', aliases=['setupinn'])
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def establishinn(self, ctx, inn_name: str, *args):
        """ - Establishes an inn at your current location

        Parameters
        ----------
        ctx
        inn_name
            Name of the inn in double quotes. No special characters!
        args
            Surround inn name in "double quotes"!

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        if args:
            await ctx.reply(f'Inn names with spaces must be surrounded with "double quotes"!')
            return
        else:
            inn_name = re.sub(r'[^a-zA-Z0-9 -]', '', inn_name)


        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{character.char_name}` must be online to establish an inn!')
            return

        clan_id, clan_name = get_clan(character)
        if not clan_id:
            await ctx.reply(f'`{character.char_name}` must be in a clan to establish an inn!')
            return

        inn_id = get_inn_id(str(clan_id))
        inn = get_inn_details(inn_id)
        if inn.inn_id:
            await ctx.reply(f'`{character.char_name}` already has an inn, `{inn.name}`! \n'
                            f'To establish a new inn, you must first close your existing inn with `v/closeinn`. This '
                            f'will check out all guests staying at that inn immediately.')
            return

        location = db_query(False, f'select x, y, z '
                                   f'from online_character_info as online '
                                   f'where char_id = {character.id}')
        (x, y, z) = flatten_list(location)

        carpet_id = int(carpets_in_range(x, y, 500, clan_id))
        if not carpet_id:
            await ctx.reply(f'No carpet detected within range of the inn location. '
                            f'You must place any type of carpet to serve as the check-in point!')
            return
        sq_x, sq_y, loc_map = transform_coordinates(x, y)
        map_square = f'{sq_x}{sq_y}'

        inn = inn.structure_inn(carpet_id, clan_id, character.id, inn_name, x, y, z, map_square, loc_map, 0, 0)
        create_inn(inn)

        await ctx.reply(f'`{character.char_name}` of clan `{clan_name}` has established an inn - `{inn_name}` with Inn ID `{carpet_id}`!\n'
                        f'Located at: `TeleportPlayer {x} {y} {z}`\n'
                        f'Please verify that the inn location matches your in-game location!')
        return


    @commands.command(name='inninfo', aliases=['innfo'])
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def inninfo(self, ctx):
        """ - Shows information about your check-in and your clan's inn

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputString = ''
        character = is_registered(ctx.author.id)
        cost = int(get_bot_config('inn_teleport_cost'))

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        checkin_list = get_all_checkin_details(character)
        if checkin_list:
            for count, checkin in enumerate(checkin_list):
                sequence = count + 1
                outputString += (f'`v/inn {sequence}` - `{checkin.name}` in `{checkin.loc_map} - {checkin.map_square}`, '
                    f'Cost: `{cost}` Bronze Coin\n')
            outputString += '\n'
        else:
            outputString += f'You are not checked in at any inn. Travel to an inn (`v/innlist` to see a list), then check in with `v/checkin`!\n\n'

        clan_id, clan_name = get_clan(character)
        if not clan_id:
            outputString += f'`{character.char_name}` is not a member of a clan with an inn.'
        else:
            inn_id = get_inn_id(str(clan_id))
            inn = get_inn_details(inn_id)
            if inn.inn_id:
                if does_object_exist(inn.inn_id):
                    pass
                else:
                    outputString += (f'The carpet which was used to register `{inn.name}` no longer exists. '
                                    f'You must close and re-establish your inn.')
                    await ctx.reply(f'{outputString}')
                    return

                outputString += f'Your clan, `{clan_name}`, owns `{inn.name}` '
            # f'at `{inn.x} {inn.y} {inn.z}`')
                number_of_checkins = count_checkins(clan_id)
                outputString += f'\nCurrently checked-in characters: `{number_of_checkins}`'
                outputString += f'\nTotal teleports to your inn: `{inn.teleport_counter}`'
            else:
                outputString += f'Your clan, `{clan_name}`, has not established an inn.'

        await ctx.reply(f'{outputString}')

    @commands.command(name='inn')
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def inn(self, ctx, target_inn: int = 1):
        """ - Teleports you to the specified inn. Must be previously checked-in. Costs Bronze Coins.

        Parameters
        ----------
        ctx
        target_inn
            Inn ID to teleport to

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        outputString = ''
        cost = int(get_bot_config('inn_teleport_cost'))
        revenue = int(get_bot_config('inn_teleport_revenue'))
        checkinString = ''

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{character.char_name}` must be online to teleport to an inn!')
            return
        else:
            checkin_list = get_all_checkin_details(character)
            if checkin_list:
                for count, checkin in enumerate(checkin_list):
                    sequence = count + 1
                    checkinString += (
                        f'`v/inn {sequence}` - `{checkin.name}` in `{checkin.loc_map} - {checkin.map_square}`, '
                        f'Cost: `{cost}` Bronze Coin\n')
            else:
                checkinString = f'You are not checked in at any inn. Travel to an inn (`v/innlist` to see a list), then check in with `v/checkin`!'
                await ctx.reply(f'{checkinString}')
                return

            # if not target_inn:
            #     outputString += (f'You must specify an inn ID to teleport to! See list below then use `v/inn <1 2 3 etc..>`\n\n'
            #                      f'__List of Inns where are you are checked in:__\n'
            #                      f'{checkinString}')
            #     await ctx.reply(f'{outputString}')
            #     return
            # else:
            try:
                destination_inn = checkin_list[target_inn - 1]
                print(destination_inn)
            except IndexError | TypeError:
                outputString += (f'You must use the short-form inn sequence number referenced below. `v/inn <1 2 3 etc..>`\n\n'
                                 f'__List of Inns where are you are checked in:__\n'
                                 f'{checkinString}')
                await ctx.reply(f'{outputString}')
                return

            if is_checked_in(character, destination_inn):
                inn = get_inn_details(destination_inn.inn_id)
                owner_character = get_single_registration_new(char_id=inn.owner_id)

                if does_object_exist(inn.inn_id):
                    pass
                else:
                    outputString = f'The carpet which was used to register `{destination_inn.name}` no longer exists. You may not teleport there.'
                    await ctx.reply(f'{outputString}')
                    return
                if inn.subsidized_amount > 0:
                    adjusted_cost = cost - int(inn.subsidized_amount)
                    adjusted_revenue = revenue - int(inn.subsidized_amount)
                    owner_balance = get_balance(owner_character)
                    if owner_balance >= inn.subsidized_amount:
                        pass
                    else:
                        await ctx.reply(f'`{owner_character.char_name}` does not have the required `{cost}` '
                                        f'Bronze Coins to subsidize your teleport to your inn room at `{inn.name}`.\n'
                                        f'You must pay the full price.\n')
                        adjusted_cost = cost
                        adjusted_revenue = revenue
                        pass
                else:
                    adjusted_cost = cost
                    adjusted_revenue = revenue
                    pass

                balance = get_balance(character)
                if balance >= adjusted_cost:
                    inn_transaction(inn, character, adjusted_cost, adjusted_revenue, owner_character)
                else:
                    await ctx.reply(f'`{character.char_name}` does not have the required `{cost}` '
                                    f'Bronze Coins to teleport to their inn room at `{inn.name}`.')
                    return
                runRcon(f'con {rconCharId} TeleportPlayer {inn.x} {inn.y}, {inn.z}')
                outputString += f'Returned `{character.char_name}` into their inn room at `{inn.name}`'
                if adjusted_cost > 0:
                    outputString += f'\n`{adjusted_cost}` Bronze Coins have been deducted from your account.\n'
                if inn.subsidized_amount > 0:
                    outputString += f'\n`{inn.subsidized_amount}` Bronze Coins have been deducted from `{owner_character.char_name}`\'s account due to the subsidized amount.'
                await ctx.reply(f'{outputString}')
                return
            else:
                outputString += (f'You are not checked in at that inn.\n\n'
                                 f'__List of Inns where are you are checked in:__\n'
                                 f'{checkinString}')
                await ctx.reply(f'{outputString}')
                return

            # # checkin_list = get_all_checkin_details(character)
            # # for chosen_inn in checkin_list:
            # #     inn = get_inn_details(chosen_inn.inn_id)
            # #     outputString += (f'``{inn.name}` - {inn.name}, '
            # #                      # f'location `TeleportPlayer {inn.x} {inn.y} {inn.z}` \n'
            # #                      f'\nCheckout Time: <t:{checkin.valid_until}:f> in your timezone\n'
            # #                      f'Cost to teleport: `{inn_teleport_cost}` Bronze Coin\n\n')
            # # if checkin.inn_id:
            #     # bonus_mult = int(get_bot_config('inn_checkin_bonus_mult'))
            #
            #
            # # else:
            #     outputString += f'Character `{character.char_name}` is not checked in at any inn!\n\n'
            #
            # await ctx.reply(f'{outputString}')
            # return

    @commands.command(name='checkin', aliases=['book'])
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def checkin(self, ctx):
        """- Checks in to the inn room nearest to your location, costs 10 BC

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        target_inn = ''
        inn = Inn()
        checkin_cost = int(get_bot_config(f'checkin_cost'))

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        # inn_list = db_query(False, f'select inn_id, clan_id, owner_id, inn_name, x, y, z, '
        #                            f'map_square, loc_map, teleport_counter from inn_locations')
        inn_list = get_all_inns()
        print(inn_list)
        if not inn_list:
            await ctx.reply(f'Character `{character.char_name}` is not located at an inn!')
            return

        for inn in inn_list:
            # (inn.inn_id, inn.clan_id, inn.owner_id, inn.name, inn.x, inn.y, inn.z, inn.map_square,
            #  inn.loc_map, inn.teleport_counter) = inn_record
            result_id, result_name = character_in_radius(inn.x, inn.y, inn.z, 2500, character.id)
            if result_id:
                clan_id, clan_name = get_clan(character)
                # print(f'Player Clan: {clan_id}, Inn Clan Id: {inn.clan_id}')
                if clan_id == inn.clan_id:
                    await ctx.reply(f'You cannot check in at an inn owned by your clan!')
                    return
                else:
                    target_inn = inn
                break

        if target_inn:
            balance = get_balance(character)
            if balance >= checkin_cost:
                eld_transaction(character, f'Inn Check-in fee', -checkin_cost)
                checkin_to_inn(character, target_inn)
                await ctx.reply(f'Character `{character.char_name}` has checked in at inn `{inn.name}` '
                                f'for {checkin_cost} Bronze Coins.')
                return
            else:
                await ctx.reply(f'You do not have enough bronze coins to check in! Available Bronze Coins: `{balance}`, '
                                f'Needed: `{checkin_cost}`')
        else:
            await ctx.reply(f'Character `{character.char_name}` is not located at an inn!')
            return

    @commands.command(name='subsidize')
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def subsidize(self, ctx, amount: int = 0):
        """- Subsidize the cost of teleporting to your inn, reducing the cost guests pay but charging you instead.

        Parameters
        ----------
        ctx
        amount

        Returns
        -------

        """
        outputString = ''
        character = is_registered(ctx.author.id)
        cost = int(get_bot_config('inn_teleport_cost'))

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        clan_id, clan_name = get_clan(character)
        if not clan_id:
            outputString += f'`{character.char_name}` is not a member of a clan with an inn.'
        else:
            inn_id = get_inn_id(str(clan_id))
            inn = get_inn_details(inn_id)
            if inn.inn_id:
                if amount not in list(range(0, cost + 1, 1)):
                    await ctx.reply(f'You must specify an integer <= to the inn teleport cost of `{cost}`.')
                    return
                else:
                    set_subsidized_amount(inn.inn_id, amount)
                    await ctx.reply(f'Teleports to your inn now cost `{cost-amount}` for guests. '
                                    f'The subsidized balance of `{amount}` will be paid from your account when it is used. '
                                    f'You will not earn any revenue from teleports to the inn.')
                    return

        await ctx.reply(f'{outputString}')

    @commands.command(name='innlist')
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def innlist(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        inn = Inn()
        outputString = '__List of Server-wide Inns__\n'
        results = db_query(False, f'select * from inn_locations')
        if not results:
            await ctx.reply(f'There are no inns registered yet.')
            return

        for result in results:
            (inn.inn_id, inn.clan_id, inn.owner_id, inn.name, inn.x, inn.y, inn.z, inn.map_square, inn.loc_map, inn.teleport_counter, inn.subsidized_amount) = result
            owner = get_single_registration_new(char_id=inn.owner_id)
            clan_id, clan_name = get_clan(owner)
            # new_x, new_y = transform_coordinates(inn.x, inn.y)
            outputString += (f'`{inn.name}` - Owned by `{owner.char_name}` of `{clan_name}` '
                             f'located in `{inn.loc_map} - {inn.map_square}` at `({inn.x},{inn.y})`\n')

        await ctx.reply(f'{outputString}')

        return

    @commands.command(name='shoplist')
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def shoplist(self, ctx):
        """ - List all thrall shops and their locations

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        splitOutput = ''
        outputList = []
        once = True

        character = is_registered(ctx.author.id)
        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        # if 'pet' in option or 'animal' in option:
        #     type_string = f'Pet'
        #     class_string = f'/Game/Systems/Building/Placeables/ThrallTrading/BP_PL_ThrallTrade_Animal1.BP_PL_ThrallTrade_Animal1_C'
        # elif 'thrall' in option or 'human' in option:
        #     type_string = f'Thrall'
        #     class_string = f'/Game/Systems/Building/Placeables/ThrallTrading/BP_PL_ThrallTrade_Humanoid1.BP_PL_ThrallTrade_Humanoid1_C'
        # else:
        #     await ctx.reply(f'`{option}` is not a valid option. Use `thrall` or `pet`')
        #     return

        class_string = 'ThrallTrade'

        outputString = f'__List of Active Shops__\n'
        query = (f'sql select x, y, coalesce(guilds.name, characters.char_name) as owner from actor_position '
                 f'left join buildings on actor_position.id = buildings.object_id '
                 f'left join guilds on buildings.owner_id = guilds.guildId '
                 f'left join characters on buildings.owner_id = characters.id '
                 f'left join used_smart_objects on buildings.object_id = used_smart_objects.smart_object_actor_id '
                 f'left join properties on used_smart_objects.interacting_actor_id = properties.object_id '
                 f'where used_smart_objects.interacting_actor_id is not null '
                 f'and class like \'%{class_string}%\' '
                 f'and properties.name like \'%SourceSpawnTable%\' order by x asc, y asc, owner desc')
        results = runRcon(query)
        if not results:
            await ctx.reply(f'There are no active shops right now.')
            return

        results.output.pop(0)
        for result in results.output:
            match = re.findall(r'#\d+\s+(.*?)\s[|]\s+(.*?)\s[|]\s+(.*)\s[|]', result)
            x = float(match[0][0])
            y = float(match[0][1])
            clan = match[0][2]
            sq_x, sq_y, loc_map = transform_coordinates(x, y)
            outputString += f'{clan} - `{loc_map} {sq_x}{sq_y}` ({str(round(x))}, {str(round(y))})\n'
            #
            # new_x, new_y = transform_coordinates(inn.x, inn.y)
            # outputString += (f'`{inn.name}` - Owned by `{owner.char_name}` of `{clan_name}` '
            #                  f'located in `{new_x}{new_y}` at `({inn.x},{inn.y})`\n')

        if results:
            message = await ctx.reply(f'Working on it...')

            if outputString:
                print(len(str(outputString)))
                if len(str(outputString)) > 1500:
                    outputList = outputString.splitlines()
                    for items in outputList:
                        splitOutput += f'{str(items)}\n'
                        if len(str(splitOutput)) > 1500:
                            if once:
                                once = False
                                await message.edit(content=str(splitOutput))
                                splitOutput = '(continued)\n'
                            else:
                                await ctx.send(str(splitOutput))
                                splitOutput = '(continued)\n'
                        else:
                            continue
                    await ctx.send(str(splitOutput))
                else:
                    await message.edit(content=f'{outputString}')
                    return
            return
        else:
            await ctx.reply(f'No results found.')
        return

        # await ctx.reply(f'{outputString}')

        # return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(InnSystem(bot))
