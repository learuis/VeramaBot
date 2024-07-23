import math
import random
import re
import os

from discord.ext import commands

from cogs.QuestSystem import check_inventory
from cogs.Reward import add_reward_record
from functions.common import custom_cooldown, get_bot_config, is_registered, flatten_list, set_bot_config, get_rcon_id, \
    run_console_command_by_name, get_single_registration
from functions.externalConnections import db_query, runRcon

from dotenv import load_dotenv

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))

def choose_new_treasure_location():
    location = random.randint(int(1), int(254))
    set_bot_config(f'current_treasure_location', f'{location}')
    return location

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
            print(f'Character has no points in Expertise.')
            return bonus, expertise_points
    else:
        print(f'Should this ever happen?')
        return bonus, expertise_points

    for result in results.output:
        match = re.search(r'\s+\d+ | [^|]*', result)
        expertise_points = int(float(match[0]))
        bonus += expertise_points

    return bonus, expertise_points

def calculate_bonus(char_id):
    bonus = 0
    bonusMessage = ''

    bonus, expertise_points = get_character_expertise(char_id)
    bonusMessage += f'Expertise Bonus: `+{expertise_points*10}%` | '

    if check_inventory(char_id, 2, 4196):
        bonus += 10
        bonusMessage += f'Gravedigger Bonus: `+100%`'
    else:
        bonusMessage += f'Gravedigger Bonus: `+0%`'

    bonusMessage += f'\nChance to find Treasure is increased by `{bonus*10}%`!'

    return bonus, bonusMessage


def grant_treasure_rewards(character, target_name, bonus: int):
    reward_list = []
    default_reward = (11009, 'Eldarium Cache')
    print(f'{character.id}')
    print(f'{character}')

    for category in range(1, 5):

        category_chance = int(get_bot_config(f'treasure_{category}_chance'))
        print(f'Class {category}: {(category_chance + (category_chance * bonus/10))}')

        treasure_roll = random.randint(int(1), int(100))

        if treasure_roll <= (category_chance + (category_chance * bonus/10)):
            results = db_query(False, f'select item_id, item_name from treasure_rewards '
                               f'where reward_category = {category} order by RANDOM() limit 1')
            to_add = flatten_list(results)
            reward_list.append(to_add)
        else:
            reward_list.append(default_reward)

    outputMessage = f'__Treasure Found__: (claim with `v/claim`)\n| '

    print(f'{reward_list}')
    for reward in reward_list:
        print(f'{reward}')
        outputMessage += f'`{reward[1]}` | '
        add_reward_record(int(character.id), int(reward[0]), 1, f'Treasure Hunt: {reward[1]}')

    return outputMessage

class TreasureHunt(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='dig', aliases=['treasure'])
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts', 'Helper')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        target = int(get_bot_config(f'current_treasure_location'))

        locs = db_query(False, f'select location_name, x, y, radius '
                        f'from treasure_locations '
                        f'where id = {target} limit 1')

        (target_name, target_x, target_y, target_radius) = flatten_list(locs)

        nwPoint = [target_x - target_radius, target_y - target_radius]
        sePoint = [target_x + target_radius, target_y + target_radius]

        online_chars = db_query(False, f'select x, y '
                                f'from online_character_info as online '
                                f'where char_id = {character.id}')

        (digger_x, digger_y) = flatten_list(online_chars)

        if nwPoint[0] <= digger_x <= sePoint[0] and nwPoint[1] <= digger_y <= sePoint[1]:

            choose_new_treasure_location()
            bonus, bonusMessage = calculate_bonus(character.id)
            reward_list = grant_treasure_rewards(character, target_name, bonus)
            run_console_command_by_name(character.char_name, f'testFIFO 7 Treasure! Use v/claim to get rewards')

            outputMessage += f'`{character.char_name}` has found the treasure hidden at `{target_name}`!\n'
            outputMessage += f'{bonusMessage}\n\n'
            outputMessage += f'{reward_list}'

            print(f'NW: ({nwPoint[0]}, {nwPoint[1]}) SE: ({sePoint[0]}, {sePoint[1]})\n'
                  f'TeleportPlayer {target_x} {target_y} 0\n'
                  f'Character Coordinates: ({digger_x}, {digger_y})\n'
                  f'{character.char_name} is within the bounds of location {target_name} ({target})\n'
                  f'Rewards: {reward_list}')

        else:
            outputMessage += (f'{character.char_name} tried to dig up hidden treasure, but didn\'t find anything. '
                              f'Wait 1 minute and make sure you\'re in the correct location before trying again!\n')

            print(f'NW: ({nwPoint[0]}, {nwPoint[1]}) SE: ({sePoint[0]}, {sePoint[1]})\n'
                  f'TeleportPlayer {target_x} {target_y} 0\n'
                  f'Character Coordinates: ({digger_x}, {digger_y})\n'
                  f'{character.char_name} is not within the bounds of location {target_name} ({target})')

        await ctx.reply(f'{outputMessage}')

        return

    @commands.command(name='givetreasure')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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
