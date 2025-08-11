import math
import random
import re
import os

from discord.ext import commands

from cogs.QuestSystem import check_inventory, count_inventory_qty, treasure_broadcast
from functions.common import custom_cooldown, get_bot_config, is_registered, flatten_list, set_bot_config, get_rcon_id, \
    run_console_command_by_name, get_single_registration, int_epoch_time, no_registered_char_reply, check_channel, \
    add_reward_record, get_treasure_target, clear_treasure_target, increase_notoriety, increment_times_looted
from functions.externalConnections import db_query, runRcon

from dotenv import load_dotenv

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))

treasure_location_count = int(get_bot_config('treasure_location_count'))

def choose_new_treasure_location():
    location = random.randint(int(1), treasure_location_count)
    set_bot_config(f'current_treasure_location', f'{location}')
    return location

def update_daily_eligibility(character):
    db_query(True, f'insert or replace into daily_treasure (char_id, season, next_eligible) '
                   f'values ({character.id}, {CURRENT_SEASON}, {int_epoch_time()+64800})')
    return


def get_character_expertise(char_id):
    bonus = 0
    expertise_points = 0

    results = runRcon(f'sql select stat_value from character_stats '
                      f'where char_id = {char_id} and stat_id = 16 and stat_type = 0 limit 1')

    if results.error:
        print(f'RCON error received in get_character_expertise')
        return bonus, expertise_points

    if results.output:
        results.output.pop(0)
        if not results.output:
            # print(f'Character has no points in Expertise.')
            return bonus, expertise_points
    else:
        # print(f'Should this ever happen?')
        return bonus, expertise_points

    for result in results.output:
        match = re.search(r'\s+\d+ | [^|]*', result)
        expertise_points = int(float(match[0]))
        bonus += expertise_points

    return bonus, expertise_points

def calculate_bonus(char_id, daily=False):
    bonus = 0
    bonusMessage = ''
    bonus_coin = f'\nYou received a bonus `Lucky Coin` for claiming your daily treasure!'

    if not daily:
        bonus_coin = f''
        bonus, expertise_points = get_character_expertise(char_id)
        bonusMessage += f'Expertise Bonus: `+{expertise_points*10}%` | '

        if check_inventory(char_id, 2, 4196) >= 0:
            bonus += 10
            bonusMessage += f'Gravedigger Bonus: `+100%` | '
        else:
            bonusMessage += f'Gravedigger Bonus: `+0%` | '

    count_lucky_coins = get_bot_config(f'count_lucky_coins')
    lucky_coin_multiplier = float(get_bot_config(f'lucky_coin_multiplier'))
    if 'yes' in count_lucky_coins:
        lucky_coins = count_inventory_qty(char_id, 0, 80256)
        if lucky_coins:
            bonus += lucky_coin_multiplier * lucky_coins
            bonusMessage += f'Lucky Coin Bonus: `+{lucky_coins}%`'
        else:
            bonusMessage += f'Lucky Coin Bonus: `+0%`'

    bonusMessage += f'\nChance to find Treasure is increased by `{bonus*10}%!`{bonus_coin}'

    return bonus, bonusMessage

def get_daily_eligibility(character):
    result = db_query(False, f'select next_eligible from daily_treasure '
                             f'where char_id = {character.id} and season = {CURRENT_SEASON} limit 1')
    if not result:
        return True, 0
    for record in result:
        value = record[0]
        if int(value) <= int_epoch_time():
            return True, 0
        else:
            return False, int(value)
    return False

def treasure_portal(bonus):
    portal_chance = int(get_bot_config('treasure_portal_chance'))
    portal_roll = random.randint(int(1), int(100))
    if portal_roll <= portal_chance:
        return True
    else:
        return False

def grant_treasure_rewards(character, target_name, bonus, daily=False):
    reward_list = []
    default_reward = (11009, 'Eldarium Cache')
    alternate_reward = (80256, 'Lucky Coin')
    # print(f'{character.id}')
    # print(f'{character}')
    #
    for category in range(1, 5):

        category_chance = int(get_bot_config(f'treasure_{category}_chance'))
        # print(f'Class {category}: {(category_chance + (category_chance * bonus/10))}')

        treasure_roll = random.randint(int(1), int(100))

        if treasure_roll <= (category_chance + (category_chance * bonus/10)):
            results = db_query(False, f'select item_id, item_name from treasure_rewards '
                               f'where reward_category = {category} order by RANDOM() limit 1')
            to_add = flatten_list(results)
            reward_list.append(to_add)
        else:
            lucky_coin_chance = random.randint(int(1), int(100))
            if lucky_coin_chance <= int(get_bot_config('lucky_coin_chance')):
                reward_list.append(alternate_reward)
            else:
                reward_list.append(default_reward)
    if daily:
        reward_list.append(alternate_reward)

    outputMessage = f'__Treasure Found__: (claim with `v/claim`)\n| '

    # print(f'{reward_list}')
    for reward in reward_list:
        # print(f'{reward}')
        outputMessage += f'`{reward[1]}` | '
        add_reward_record(int(character.id), int(reward[0]), 1, f'Treasure Hunt: {reward[1]}')

    return outputMessage


class TreasureHunt(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='treasurebroadcast')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def treasurebroadcast(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        treasure_broadcast(True)
        await ctx.reply(f'Treasure location has been broadcast!')

    @commands.command(name='dig', aliases=['treasure'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def dig(self, ctx):
        """- Dig for treasure at your current location

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        character = is_registered(ctx.author.id)
        bonus = 0
        outputMessage = ''
        daily = False

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}. '
            #                 f'Visit {reg_channel.mention}!')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character {character.char_name} must be online to dig!')
            return

        # target = int(get_bot_config(f'current_treasure_location'))
        treasure_target = get_treasure_target(character)
        if not treasure_target:
            await ctx.reply(f'You don\'t know where any treasure is buried! Visit Satiah at the Sinkhole to get a location!')
            return

        locs = db_query(False, f'select location_name, x, y, radius '
                        f'from treasure_locations '
                        f'where id = {treasure_target.location_id} limit 1')

        (target_name, target_x, target_y, target_radius) = flatten_list(locs)

        nwPoint = [target_x - target_radius, target_y - target_radius]
        sePoint = [target_x + target_radius, target_y + target_radius]

        online_chars = db_query(False, f'select x, y, z '
                                f'from online_character_info as online '
                                f'where char_id = {character.id}')

        if not online_chars:
            await ctx.reply(f'Character {character.char_name} must be online to dig for treasure!')
            return

        (digger_x, digger_y, digger_z) = flatten_list(online_chars)

        if nwPoint[0] <= digger_x <= sePoint[0] and nwPoint[1] <= digger_y <= sePoint[1]:

            # choose_new_treasure_location()
            increment_times_looted(treasure_target)
            clear_treasure_target(character)

            bonus, bonusMessage = calculate_bonus(character.id, daily)
            reward_list = grant_treasure_rewards(character, target_name, bonus)
            portal_result = treasure_portal(bonus)
            if portal_result:
                print(f'Treasure Portal triggered!')

            run_console_command_by_name(character.char_name, f'testFIFO 7 Treasure! Use v/claim to get rewards')

            outputMessage += f'`{character.char_name}` has found the treasure hidden at `{target_name}`!\n'
            outputMessage += f'{bonusMessage}\n\n'
            outputMessage += f'{reward_list}'

            print(f'NW: ({nwPoint[0]}, {nwPoint[1]}) SE: ({sePoint[0]}, {sePoint[1]})\n'
                  f'TeleportPlayer {target_x} {target_y} 0\n'
                  f'Character Coordinates: ({digger_x}, {digger_y})\n'
                  f'{character.char_name} is within the bounds of location {target_name} ({treasure_target.location_id})\n'
                  f'Rewards: {reward_list}')

        else:
            outputMessage += (f'{character.char_name} tried to dig up hidden treasure, but didn\'t find anything. '
                              f'Wait 1 minute and make sure you\'re at `{treasure_target.location_name}` before trying again!\n'
                              f'The bot sees your location as: `TeleportPlayer {digger_x} {digger_y} {digger_z}`')

            print(f'NW: ({nwPoint[0]}, {nwPoint[1]}) SE: ({sePoint[0]}, {sePoint[1]})\n'
                  f'TeleportPlayer {target_x} {target_y} 0\n'
                  f'Character Coordinates: ({digger_x}, {digger_y})\n'
                  f'{character.char_name} is not within the bounds of location {target_name} ({treasure_target.location_id})')

        await ctx.reply(f'{outputMessage}')

        return

    @commands.command(name='daily', aliases=['dailydig', 'dailytrasure'])
    @commands.check(check_channel)
    async def daily(self, ctx):
        """- Collect daily treasure

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        character = is_registered(ctx.author.id)
        bonus = 0
        outputMessage = ''
        daily = True

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}. '
            #                 f'Visit {reg_channel.mention}!')
            return

        eligible, time = get_daily_eligibility(character)
        if not eligible:
            outputMessage += f'{character.char_name} cannot claim another daily treasure until <t:{time}>\n'
            await ctx.reply(f'{outputMessage}')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Daily treasure is ready to claim, but character '
                            f'{character.char_name} must be online to dig for treasure!')
            return

        target = int(get_bot_config(f'daily_treasure_location'))

        locs = db_query(False, f'select location_name, x, y, radius '
                        f'from treasure_locations '
                        f'where id = {target} limit 1')

        (target_name, target_x, target_y, target_radius) = flatten_list(locs)

        nwPoint = [target_x - target_radius, target_y - target_radius]
        sePoint = [target_x + target_radius, target_y + target_radius]

        online_chars = db_query(False, f'select x, y, z '
                                f'from online_character_info as online '
                                f'where char_id = {character.id}')

        if not online_chars:
            await ctx.reply(f'Character {character.char_name} must be online to dig for treasure!')
            return

        (digger_x, digger_y, digger_z) = flatten_list(online_chars)

        if nwPoint[0] <= digger_x <= sePoint[0] and nwPoint[1] <= digger_y <= sePoint[1]:

            update_daily_eligibility(character)

            bonus, bonusMessage = calculate_bonus(character.id, daily)
            reward_list = grant_treasure_rewards(character, target_name, bonus, daily)

            run_console_command_by_name(character.char_name, f'testFIFO 7 Treasure! Use v/claim to get rewards')

            outputMessage += f'`{character.char_name}` has claimed their daily treasure at `{target_name}`!\n'
            outputMessage += f'{bonusMessage}\n\n'
            outputMessage += f'{reward_list}'

            print(f'NW: ({nwPoint[0]}, {nwPoint[1]}) SE: ({sePoint[0]}, {sePoint[1]})\n'
                  f'TeleportPlayer {target_x} {target_y} 0\n'
                  f'Character Coordinates: ({digger_x}, {digger_y})\n'
                  f'{character.char_name} is within the bounds of location {target_name} ({target})\n'
                  f'Rewards: {reward_list}')

        else:
            outputMessage += (f'{character.char_name} tried to claim their daily treasure, but wasn\'t '
                              f'at {target_name}. Wait 1 minute and make sure you\'re '
                              f'at {target_name} before trying again!\n'
                              f'The bot sees your location as: `TeleportPlayer {digger_x} {digger_y} {digger_z}`')

            print(f'NW: ({nwPoint[0]}, {nwPoint[1]}) SE: ({sePoint[0]}, {sePoint[1]})\n'
                  f'TeleportPlayer {target_x} {target_y} 0\n'
                  f'Character Coordinates: ({digger_x}, {digger_y})\n'
                  f'{character.char_name} is not within the bounds of location {target_name} ({target})')

        await ctx.reply(f'{outputMessage}')

        return

    @commands.command(name='givetreasure')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def givetreasure(self, ctx, name: str, bonus: int = 0):
        """

        Parameters
        ----------
        ctx
        name
            Character to award the treasure to.
        bonus
            Input a bonus percentage chance to find treasure

        Returns
        -------

        """
        outputMessage = f''
        calc_bonus = round(bonus / 10)

        registration_record = get_single_registration(name)
        (char_id, char_name, discord_id) = registration_record

        character = is_registered(int(discord_id))

        print(f'{character.id} {character.char_name} {discord_id}')
        print(f'{character}')

        if not character:
            await ctx.send(f'No character named `{character.char_name}` registered!')
            return
        else:
            user = self.bot.get_user(int(discord_id))

            outputMessage += f'{user.mention}\n'
            outputMessage += f'`{character.char_name}` has been awarded a bonus treasure! (claim with `v/claim`)\n'
            outputMessage += f'\nChance to find Treasure is increased by `{bonus}%`!\n\n'
            outputMessage += grant_treasure_rewards(character, f'', calc_bonus)
            channel = self.bot.get_channel(OUTCASTBOT_CHANNEL)
            await channel.send(outputMessage)

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(TreasureHunt(bot))
