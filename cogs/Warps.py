import re
import os

from discord.ext import commands

from functions.common import custom_cooldown, flatten_list, is_registered, get_rcon_id, get_bot_config, \
    no_registered_char_reply, check_channel, eld_transaction, get_balance, sufficient_funds
from functions.externalConnections import db_query, runRcon

from dotenv import load_dotenv

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))

class Warps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='warp')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def warp(self, ctx, destination: str, quest_id: int = commands.parameter(default=None)):
        """

        Parameters
        ----------
        ctx
        destination
        quest_id

        Returns
        -------

        """
        outputString = 'List of Available Warps: '

        if 'list' in destination.casefold():
            output = db_query(False, f'select warp_name from warp_locations')
            output = flatten_list(output)
            for warp_name in output:
                outputString += f'{warp_name}, '
            await ctx.send(f'{outputString}')
            return

        if 'quest' in destination.casefold():
            if not quest_id:
                await ctx.reply(f'You must specify a quest ID in order to teleport there.!')
                return

            query_command = (f'select 0, quest_name, 0, 0, trigger_x, trigger_y, trigger_z, 0 '
                             f'from one_step_quests where quest_id = {quest_id} limit 1')
        else:
            query_command = f'select * from warp_locations where warp_name like \'%{destination.casefold()}%\' limit 1'

        output = db_query(False, f'{query_command}')

        warp_entry = flatten_list(output)
        (warp_id, description, warp_name, marker_label, x, y, z, marker_flag) = warp_entry

        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'No character registered to player {ctx.author.mention}!')
            return
        else:
            name = character.char_name

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{name}` must be online to warp to `{description}`!')
            return
        else:
            runRcon(f'con {rconCharId} TeleportPlayer {x} {y} {z}')
            await ctx.reply(f'Teleported `{name}` to {description}.')
            return

    @commands.command(name='home', aliases=['stuck'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def stuck(self, ctx, option: int = 1):
        """- Use if you're stuck in the floor. Warps you to the Sinkhole.

        Parameters
        ----------
        ctx
        option
            1 = oldest spawn point 2 = latest spawn point

        Returns
        -------

        """
        coordinates = []
        character = is_registered(ctx.author.id)
        target_x = 0
        target_y = 0
        target_z = 0

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to player {ctx.author.mention}! '
            #                 f'Please register here: {channel.mention} ')
            return
        else:
            name = character.char_name

        if 'home' in ctx.invoked_with:
            location = get_bot_config('event_location')
            if location != '0':
                home_cost = 0
                pass
                # an event is active, do not charge.
                # await ctx.reply(f'This command can only be used during an event!')
                # return
            else:
                home_cost = int(get_bot_config('home_cost'))
                if sufficient_funds(character, home_cost):
                    eld_transaction(character, f'Teleport to Home', -home_cost)
                    pass
                else:
                    balance = int(get_balance(character))
                    await ctx.reply(f'Insufficient funds! Available decaying eldarium: {balance}. Needed: {home_cost}')
                    return

            # hex_name = bytes(name, 'utf8')
            # hex_name = hex_name.hex()
            # print(f'Char name in hex is {hex_name}')

            if option == 2:
                order_by = f'desc'
            else:
                order_by = f'asc'

            commandString = (f'sql select ap.x,ap.y,ap.z from actor_position ap '
                             f'left join properties p on ap.id = p.object_id '
                             f'where hex(p.value) like '
                             f'( select \'%\' || hex(a.platformId) || \'%\' from account a '
                             f'left join characters c on a.id = c.playerId '
                             f'left join properties p2 on a.id = p2.object_id '
                             f'where c.id = {character.id} ) '
                             f'order by p.object_id {order_by} limit 1;')

            # commandString = (f'sql select x,y,z from actor_position where id in '
            #                  f'(select object_id from properties '
            #                  f'where hex(value) like \'%{hex_name}%\' '
            #                  f'and name like \'%BP_BAC_SpawnPoints_C.SpawnOwnerName%\' limit 1)')
            # print(commandString)

            rconResponse = runRcon(f'{commandString}')
            if rconResponse.error:
                print(f'RCON error in hex lookup')
                return False
            rconResponse.output.pop(0)
            # print(rconResponse)

            for x in rconResponse.output:
                match = re.findall(r'\s+\d+ | [^|]*', x)
                coordinates.append(match)

            # print(coordinates)
            if not coordinates:
                print(f'RCON error in parsing')
                await ctx.send(f'Found no spawn points for {character.char_name}!')
                return False

            for record in coordinates:
                target_x = record[0].strip()
                target_y = record[1].strip()
                target_z = record[2].strip()

            rconCharId = get_rcon_id(character.char_name)
            if not rconCharId:
                await ctx.reply(f'Character `{name}` must be online to be rescued!')
                return
            else:
                runRcon(f'con {rconCharId} TeleportPlayer {target_x} {target_y} {target_z}')
                # print(f'{home_cost}')
                if home_cost != 0:
                    await ctx.reply(f'Returned `{name}` to their spawn for {home_cost} decaying eldarium.')
                    return
                else:
                    await ctx.reply(f'Returned `{name}` to their spawn.')
                    return
        else:
            destination = get_bot_config('rescue_location')

            rconCharId = get_rcon_id(character.char_name)
            if not rconCharId:
                await ctx.reply(f'Character `{name}` must be online to be rescued!')
                return
            else:
                query_command = (f'select description, x, y, z from warp_locations where warp_name like '
                                 f'\'%{destination.casefold()}%\' limit 1')

                output = db_query(False, f'{query_command}')

                warp_entry = flatten_list(output)
                (description, x, y, z) = warp_entry
                runRcon(f'con {rconCharId} TeleportPlayer {x} {y} {z}')
                await ctx.reply(f'Rescued `{name}` from the floor, teleported to `{description}`.')
                return


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Warps(bot))
