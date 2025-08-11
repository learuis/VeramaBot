import hashlib
import os
import re
import math

from discord.ext import commands
from dotenv import load_dotenv

from functions.common import is_registered, get_clan, flatten_list, get_rcon_id, int_epoch_time, get_bot_config, \
    get_single_registration_new, no_registered_char_reply, check_channel, eld_transaction, get_balance
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
        self.teleport_counter = 0

    def structure_inn(self, inn_id, clan_id, owner_id, name, x, y, z):
        self.inn_id = inn_id
        self.clan_id = clan_id
        self.owner_id = owner_id
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.teleport_counter = teleport_counter
        return self


class Checkin:
    def __init__(self):
        self.char_id = 0
        self.inn_id = ''
        self.valid_until = 0


def carpets_in_range(x, y, radius, clan_id):
    count = 0
    nwPoint = [x - radius, y - radius]
    sePoint = [x + radius, y + radius]

    rconResponse = runRcon(f'sql select count(*) from actor_position a left join buildings b on a.id = b.object_id '
                           f'where b.owner_id = {clan_id} '
                           f'and x > {nwPoint[0]} and y > {nwPoint[1]} '
                           f'and x < {sePoint[0]} and y < {sePoint[1]} '
                           f'and ( a.class like \'%carpet%\' or a.class like \'%rug%\' ) limit 1;')

    for x in rconResponse.output:
        print(x)
        match = re.search(r'#\b\d\s+(\d+)', x)
        if match:
            match.group(1)
            count = int(match.group(1))

    return count


def get_checkin_details(character):
    checkin = Checkin()

    results = db_query(False, f'select checkins.char_id, checkins.inn_id, checkins.valid_until '
                              f'from inn_checkins as checkins '
                              f'left join inn_locations as locs on checkins.inn_id = locs.inn_id '
                              f'where checkins.char_id = {character.id} order by checkins.valid_until desc limit 1')
    if not results:
        return checkin
    results = flatten_list(results)
    print(results)
    (checkin.char_id, checkin.inn_id, checkin.valid_until) = results

    return checkin


def count_checkins(clan_id):
    count = 0
    inn_id = encode_inn_id(clan_id)

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


def get_inn_details(inn_id: str):
    inn = Inn()
    results = db_query(False, f'select inn_id, clan_id, owner_id, inn_name, x,y,z, teleport_counter '
                              f'from inn_locations where inn_id = \'{inn_id}\' limit 1')
    if results:
        results = flatten_list(results)
        print(results)
        (inn.inn_id, inn.clan_id, inn.owner_id, inn.name, inn.x, inn.y, inn.z, inn.teleport_counter) = results
    return inn


def checkin_to_inn(character, inn_id):
    length = int(get_bot_config(f'inn_checkin_length'))
    checkout_time = int_epoch_time() + length
    db_query(True, f'insert or replace into inn_checkins (char_id, inn_id, valid_until) '
                   f'values ({character.id}, \'{inn_id}\', \'{int_epoch_time() + length}\')')
    return checkout_time

def transform_coordinates(x, y):
    x_squares = 'ABCDEFGHIJKLMNOP'
    x = math.floor(1 + ((x + 307682) / 46500))
    y = math.floor(1 + (-(y - 330805) / 46500))

    x_square_label = x_squares[x-1]
    y_square_label = y + 1
    print(f'{x_square_label}{y_square_label}')
    return x_square_label, y_square_label


def clear_all_checkins(inn_id):
    db_query(True, f'delete from inn_checkins where inn_id = \'{inn_id}\'')
    return


def create_inn(inn):
    db_query(True, f'insert or replace into inn_locations '
                   f'(inn_id, clan_id, owner_id, inn_name, x, y, z) values '
                   f'(\'{inn.inn_id}\', {inn.clan_id}, {inn.owner_id}, \'{inn.name}\', '
                   f'\'{inn.x}\', \'{inn.y}\', \'{inn.z}\')')


def delete_inn(inn_id):
    db_query(True, f'delete from inn_locations where inn_id = \'{inn_id}\'')
    return


def encode_inn_id(clan_id):
    inn_id = hashlib.md5(str(clan_id).encode('utf-8')).hexdigest()
    return inn_id

def inn_transaction(inn, character, cost, revenue, bonus_mult):
    eld_transaction(character, f'Inn TP to {inn.name}', -cost)
    inn_owner = get_single_registration_new(char_id=int(inn.owner_id))
    guests = count_checkins(inn.clan_id)
    bonus_revenue = guests * bonus_mult
    print(bonus_revenue)
    final_revenue = bonus_revenue + revenue
    if final_revenue > 10:
        final_revenue = 10
    print(final_revenue)
    eld_transaction(inn_owner, f'{character.char_name} teleported to {inn.name}', final_revenue)
    return


class InnSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

        inn_id = hashlib.md5(str(clan_id).encode('utf-8')).hexdigest()
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
    async def establishinn(self, ctx, inn_name: str):
        """ - Establishes an inn at your current location

        Parameters
        ----------
        ctx
        inn_name
            Name of the inn in double quotes. No special characters!

        Returns
        -------

        """
        inn_name = re.sub(r'[^a-zA-Z0-9 -]', '', inn_name)

        character = is_registered(ctx.author.id)
        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{character.char_name}` must be online to establish an inn!')
            return

        clan_id, clan_name = get_clan(character)
        if not clan_id:
            await ctx.reply(f'`{character.char_name}` must be in a clan to establish an inn!')
            return

        inn_id = encode_inn_id(str(clan_id))
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

        if int(carpets_in_range(x, y, 500, clan_id)) == 0:
            await ctx.reply(f'No carpet detected within range of the inn location. '
                            f'You must place any type of carpet to serve as the check-in point!')
            return

        inn = inn.structure_inn(inn_id, clan_id, character.id, inn_name, x, y, z)
        create_inn(inn)

        await ctx.reply(f'`{character.char_name}` of clan `{clan_name}` has established an inn - `{inn_name}`!\n'
                        f'Located at: `TeleportPlayer {x} {y} {z}`\n'
                        f'Please verify that the inn location matches your in-game location!')
        return

        # get character and clan
        # Get character location
        # add record to inns table
        # add checkin command
        # checkin table has char id, inn id, valid until timestamp,
        # telporting will add 1 week of duration to your stay automatically
        # add inn command to teleport to inn
        # consume decaying eldarium and grant a reward to the inn owner

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

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        checkin = get_checkin_details(character)
        inn = get_inn_details(checkin.inn_id)
        if checkin.inn_id:
            inn_teleport_cost = int(get_bot_config(f'inn_teleport_cost'))
            outputString += (f'`{character.char_name}` is checked in at `{inn.name}`, '
                             # f'location `TeleportPlayer {inn.x} {inn.y} {inn.z}` \n'
                             f'\nCheckout Time: <t:{checkin.valid_until}:f> in your timezone\n'
                             f'Cost to teleport: `{inn_teleport_cost}` Decaying Eldarium\n\n')
        else:
            outputString += f'`{character.char_name}` is not checked in at any inn!\n\n'

        clan_id, clan_name = get_clan(character)
        if not clan_id:
            outputString += f'`{character.char_name}` is not a member of a clan with an inn.'
        else:
            inn_id = encode_inn_id(str(clan_id))
            inn = get_inn_details(inn_id)
            if inn.inn_id:
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
    async def inn(self, ctx):
        """ - Teleports you to the inn where you are checked-in. Costs Decyain Eldarium.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        outputString = ''

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{character.char_name}` must be online to teleport to an inn!')
            return
        else:
            checkin = get_checkin_details(character)
            inn = get_inn_details(checkin.inn_id)
            if checkin.inn_id:
                cost = int(get_bot_config('inn_teleport_cost'))
                bonus_mult = int(get_bot_config('inn_checkin_bonus_mult'))
                revenue = int(get_bot_config('inn_teleport_revenue'))
                balance = get_balance(character)
                if balance >= cost:
                    inn_transaction(inn, character, cost, revenue, bonus_mult)
                else:
                    await ctx.reply(f'`{character.char_name}` does not have the required `{cost}` '
                                    f'decaying eldarium to teleport to their inn room at `{inn.name}`.')
                    return
                runRcon(f'con {rconCharId} TeleportPlayer {inn.x} {inn.y}, {inn.z}')
                checkout_time = checkin_to_inn(character, inn.inn_id)
                await ctx.reply(f'Returned `{character.char_name}` into their inn room at `{inn.name}`\n'
                                f'`{cost}` Decaying Eldarium has been deducted from your account.\n'
                                f'Your check-in has been refreshed and now lasts until <t:{checkout_time}:f>.')
                return
            else:
                outputString += f'Character `{character.char_name}` is not checked in at any inn!\n\n'

            await ctx.reply(f'{outputString}')
            return

    @commands.command(name='checkin', aliases=['book'])
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def checkin(self, ctx):
        """- Checks in to the inn room nearest to your location

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        target_inn = ''
        inn = Inn()

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        inn_list = db_query(False, f'select inn_id, clan_id, owner_id, inn_name, x, y, z from inn_locations')
        print(inn_list)
        if not inn_list:
            await ctx.reply(f'Character `{character.char_name}` is not located at an inn!')
            return

        for inn_record in inn_list:
            (inn.inn_id, inn.clan_id, inn.owner_id, inn.name, inn.x, inn.y, inn.z) = inn_record
            result_id, result_name = character_in_radius(inn.x, inn.y, inn.z, 2500, character.id)
            if result_id:
                clan_id, clan_name = get_clan(character)
                # print(f'Player Clan: {clan_id}, Inn Clan Id: {inn.clan_id}')
                if clan_id == inn.clan_id:
                    await ctx.reply(f'You cannot check in at an inn owned by your clan!')
                    return
                else:
                    target_inn = inn.inn_id
                break

        if target_inn:
            checkout_time = checkin_to_inn(character, target_inn)
            await ctx.reply(f'Character `{character.char_name}` has checked in at inn `{inn.name}` '
                            f'until <t:{checkout_time}:f>.')
            return
        else:
            await ctx.reply(f'Character `{character.char_name}` is not located at an inn!')
            return

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
        outputString = '__List of Inns__\n'
        results = db_query(False, f'select * from inn_locations')
        if not results:
            await ctx.reply(f'There are no inns registered yet.')
            return

        for result in results:
            (inn.inn_id, inn.clan_id, inn.owner_id, inn.name, inn.x, inn.y, inn.z) = result
            owner = get_single_registration_new(char_id=inn.owner_id)
            clan_id, clan_name = get_clan(owner)
            new_x, new_y = transform_coordinates(inn.x, inn.y)
            outputString += (f'`{inn.name}` - Owned by `{owner.char_name}` of `{clan_name}` '
                             f'located in `{new_x}{new_y}` at `({inn.x},{inn.y})`\n')

        await ctx.reply(f'{outputString}')

        return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(InnSystem(bot))
