import os
import random
import re

from discord.ext import commands

from functions.common import is_registered, int_epoch_time, flatten_list, get_bot_config
from dotenv import load_dotenv

from functions.externalConnections import runRcon, db_query

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))


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


def set_slayer_target(character):
    my_target = SlayerTarget()
    my_target.char_id = character.id
    my_target.start_time = int_epoch_time()
    randomizer = random.randint(1, int(get_bot_config('beast_slayer_target_count')))
    query_result = db_query(False, f'select target_name, target_display_name from beast_slayer_target_list '
                                   f'where id = {randomizer}')
    # print(query_result)
    (my_target.target_name, my_target.display_name) = flatten_list(query_result)
    db_query(True, f'insert or replace into beast_slayers '
                   f'(char_id, target_name, target_display_name, start_time) '
                   f'values ({my_target.char_id}, \'{my_target.target_name}\', '
                   f'\'{my_target.display_name}\', {my_target.start_time})')
    return my_target

def clear_slayer_target(character):
    db_query(True, f'delete from beast_slayers where char_id = {character.id}')
    return

def get_slayer_target(character):
    my_target = SlayerTarget()
    query_result = db_query(False, f'select char_id, target_name, target_display_name, start_time from beast_slayers'
                                   f' where char_id = {character.id}')
    if query_result:
        print(query_result)
        (my_target.char_id, my_target.target_name,
         my_target.display_name, my_target.start_time) = flatten_list(query_result)
    # print(f'My target {my_target}')
    return my_target


class Hunter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='quarry')
    @commands.has_any_role('Admin', 'Moderator')
    async def quarry(self, ctx, option: str = ''):
        """ - Assigns a Beast Slayer task
        
        Parameters
        ----------
        ctx
        option
    
        Returns
        -------
    
        """
        character = is_registered(ctx.author.id)

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


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Hunter(bot))
