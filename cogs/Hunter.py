import os
import random
import re

import discord
from discord.ext import commands

from cogs.EldariumBank import sufficient_funds, eld_transaction, get_balance
from functions.common import is_registered, int_epoch_time, flatten_list, get_bot_config, no_registered_char_reply, \
    Registration
from dotenv import load_dotenv

from functions.externalConnections import runRcon, db_query

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))



class SlayerTarget:
    def __init__(self):
        self.char_id = 0
        self.target_name = ''
        self.display_name = ''
        self.start_time = 0

def killed_target(my_target):
    rconResponse = runRcon(f'sql select worldTime from game_events where '
                           f'eventType = 86 and '
                           f'objectName = \'{my_target.target_name}\' and '
                           f'worldTime >= {my_target.start_time} and '
                           f'causerId = {my_target.char_id} '
                           f'order by worldTime desc limit 1;')
    # print(str(rconResponse.output))
    match = re.search(r'#0 (\d+) \|', str(rconResponse.output))
    if match:
        return True
    else:
        return False


def set_slayer_target(character, exclude_target: SlayerTarget = False):
    if exclude_target:
        where_clause = f' where target_name not like \'%{exclude_target.target_name}%\''
    else:
        where_clause = f''

    my_target = SlayerTarget()
    my_target.char_id = character.id
    my_target.start_time = int_epoch_time()
    # randomizer = random.randint(0, int(get_bot_config('beast_slayer_target_count')))
    query = (f'select target_name, target_display_name from beast_slayer_target_list'
             f'{where_clause} order by random() limit 1')
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
        print(f'My target {my_target}')
        return my_target
    else:
        return False

def get_notoriety(quarry: SlayerTarget):
    print(f'getting notoriety {quarry.target_name}')
    query_result = db_query(False, f'select target_name, notoriety from beast_slayer_target_list '
                                   f'where target_name like \'%{quarry.target_name}%\' limit 1')
    print(query_result)
    notorious_target, notorious_multiplier = flatten_list(query_result)
    print(notorious_target, notorious_multiplier)

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

class Hunter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='quarry', aliases=['rq'])
    async def quarry(self, ctx, confirm: str = ''):
        """ - Be assigned a different Beast Slayer quarry, costs 50 DE

        Parameters
        ----------
        ctx
        confirm
            Add confirm to execute the command

        Returns
        -------

        """
        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        exclude_target = get_slayer_target(character)
        if not exclude_target:
            await ctx.reply(f'`{character.char_name}` does not currently have a Beast Slayer Quarry! '
                            f'Visit the Profession Hub to be assigned one.')
            return

        if 'confirm' in confirm:
            reason = (f'Quarry Reroll')
            reroll_cost = int(get_bot_config(f'beast_slayer_reroll_cost'))
            amount = -reroll_cost
            reward_quantity = int(get_bot_config(f'beast_slayer_reward'))
            check_balance = sufficient_funds(character, abs(amount))

            if check_balance:
                new_balance = eld_transaction(character, reason, amount)
                current_target = set_slayer_target(character, exclude_target)

                (notorious_target, notorious_multiplier) = increase_notoriety(exclude_target)
                total_bounty = reward_quantity + (reroll_cost * notorious_multiplier)

                await ctx.reply(
                    f'Consumed {abs(amount)} decaying eldarium from {character.char_name}\'s account\n'
                    f'New Balance: {new_balance}\n\n'
                    f'`{character.char_name}` was assigned a new Beast Slayer quarry: `{current_target.display_name}`'
                    f' on <t:{current_target.start_time}:f>'
                    f'\n\nThe bounty on `{exclude_target.display_name}` has increased to `{total_bounty}` '
                    f'decaying eldarium!')
                return
            else:
                balance = int(get_balance(character))
                await ctx.reply(f'Insufficient funds! Available decaying eldarium: {balance}')
                return

        else:
            await ctx.reply(f'`{character.char_name}`\'s current quarry: `{exclude_target.display_name}`.\n\n'
                            f'This command will clear your quarry and assign you a new one for 50 decaying eldarium. '
                            f'You will not be able to claim any reward for the current quarry, even if you already '
                            f'killed it.\n\nIf you are sure want to be assigned a new quarry, '
                            f'use `v/quarry confirm`.')
            return

    @commands.command(name='notorious')
    async def notorious(self, ctx):
        """ - Lists the top 10 notorious quarries

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        outputString = '__Notorious Quarries__\n'

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        query = (f'select target_display_name, notoriety from beast_slayer_target_list '
                 f'where notoriety > 0 order by notoriety desc, target_display_name')
        results = db_query(False, f'{query}')
        if not results:
            await ctx.reply(f'There are currently no notorious quarries. '
                            f'When a quarry is re-rolled, notoriety of that quarry is increased.')
            return
        else:
            reroll_cost = int(get_bot_config(f'beast_slayer_reroll_cost'))
            reward_quantity = int(get_bot_config(f'beast_slayer_reward'))
            for result in results:
                display_name, notoriety = result
                total_reward = reward_quantity + (reroll_cost * notoriety)
                outputString += f'`{display_name}` - `{total_reward}` DE\n'

        await ctx.reply(outputString)
        return

    @commands.command(name='adminquarry')
    @commands.has_any_role('Admin', 'Moderator')
    async def adminquarry(self, ctx, user: discord.Member, option: str = ''):
        """ - Assigns a Beast Slayer task
        
        Parameters
        ----------
        ctx
        user
        option
    
        Returns
        -------
    
        """
        character = is_registered(user.id)

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        if 'new' in option:
            current_target = set_slayer_target(character)
        else:
            current_target = get_slayer_target(character)

        await ctx.reply(f'`{character.char_name}` was assigned a task to slay `{current_target.display_name}`'
                        f' on <t:{current_target.start_time}:f>')

    @commands.command(name='logkill')
    @commands.has_any_role('Admin', 'Moderator')
    async def logkill(self, ctx):
        """ - Completes a Beast Slayer task

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

        current_target = get_slayer_target(character)
        if killed_target(current_target):
            outputString += f'`{character.char_name}` slew `{current_target.target_name}`. Assigning new target!'
            new_target = set_slayer_target(character)
            outputString += (f'\n\n`{character.char_name}` was assigned a task to slay `{current_target.display_name}`'
                             f' on <t:{current_target.start_time}:f>.')
            await ctx.reply(outputString)
            return
        else:
            await ctx.reply(f'You have not yet slain `{current_target.target_name}` since it was '
                            f'assigned on <t:{current_target.start_time}:f>.')
            return

    @commands.command(name='verifyslaying', aliases=['verifyquarry', 'vquarry', 'slay', 'vslay'])
    async def verifyslaying(self, ctx):
        """ - Verifies that you killed your quarry after it was assigned.

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

        current_target = get_slayer_target(character)
        if current_target:
            if killed_target(current_target):
                outputString += f'Your quarry, `{current_target.display_name}`, has been slain! Return for your reward!'
                await ctx.reply(outputString)
                return
            else:
                await ctx.reply(f'You have not yet slain `{current_target.display_name}` since it was '
                                f'assigned on <t:{current_target.start_time}:f>.')
                return
        else:
            await ctx.reply(f'`{character.char_name}` does not currently have a Beast Slayer Quarry! '
                            f'Visit the Profession Hub to be assigned one.')
            return



@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Hunter(bot))
