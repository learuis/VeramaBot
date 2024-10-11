import re
import os

from discord.ext import commands
from functions.common import custom_cooldown, flatten_list, is_registered, get_rcon_id, get_bot_config
from functions.externalConnections import db_query, runRcon

from dotenv import load_dotenv

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))

class Warps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='warp')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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
            await ctx.reply(f'No character registered to player {ctx.author.mention}!')
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

    @commands.command(name='stuck', aliases=['rescue', 'floor', 'home', 'unstuck'])
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def stuck(self, ctx):
        """- Use if you're stuck in the floor. Warps you to the Sinkhole.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        coordinates = []
        character = is_registered(ctx.author.id)
        target_x = 0
        target_y = 0
        target_z = 0

        if not character:
            channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to player {ctx.author.mention}! '
                            f'Please register here: {channel.mention} ')
            return
        else:
            name = character.char_name

        if 'home' in ctx.invoked_with:
            location = get_bot_config('event_location')
            if location == '0':
                await ctx.reply(f'This command can only be used during an event!')
                return

            hex_name = bytes(name, 'utf8')
            hex_name = hex_name.hex()
            print(f'Char name in hex is {hex_name}')

            commandString = (f'sql select x,y,z from actor_position where id in '
                             f'(select object_id from properties '
                             f'where hex(value) like \'%{hex_name}%\' '
                             f'and name like \'%BP_BAC_SpawnPoints_C.SpawnOwnerName%\' limit 1)')
            print(commandString)

            rconResponse = runRcon(f'{commandString}')
            if rconResponse.error:
                print(f'RCON error in hex lookup')
                return False
            rconResponse.output.pop(0)
            print(rconResponse)

            for x in rconResponse.output:
                match = re.findall(r'\s+\d+ | [^|]*', x)
                coordinates.append(match)

            print(coordinates)
            if not coordinates:
                print(f'RCON error in parsing')
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
                await ctx.reply(f'Returned `{name}` to their spawn.')
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
