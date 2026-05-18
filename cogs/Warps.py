import re
import os

from discord.ext import commands

from functions.common import custom_cooldown, flatten_list, is_registered, get_rcon_id, get_bot_config, \
    no_registered_char_reply, check_channel, eld_transaction, get_balance, sufficient_funds, transform_coordinates, \
    run_console_command_by_name, int_epoch_time
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

    @commands.command(name='home', aliases=['stuck', 'home1', 'home2', 'home3', 'home4', 'homelist'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def stuck(self, ctx, info: str = f''):
        """Teleports you to your bed/bedroll. Consumes Bronze Coins

        v/home1 [info] or v/home2 [info]
            home1 = oldest spawn point
            home2 = latest spawn point
            add 'info' after to see the possible destinations
        v/stuck
            teleports you to the sinkhole
        """
        coordinates = []
        key_list = []
        character = is_registered(ctx.author.id)
        target_x = 0
        target_y = 0
        target_z = 0
        balance = 0
        dest_id = 1
        spawn_type = ''

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to player {ctx.author.mention}! '
            #                 f'Please register here: {channel.mention} ')
            return
        else:
            name = character.char_name

        if 'home' in ctx.invoked_with:

            # hex_name = bytes(name, 'utf8')
            # hex_name = hex_name.hex()
            # print(f'Char name in hex is {hex_name}')

            numbers = {1,2,3,4}
            if info in numbers:
                try:
                    dest_id = int(info)
                except ValueError:
                    await ctx.reply(f'Invalid value in `info`. Use `v/help home`')
                    return
                return

            match ctx.invoked_with:
                case 'home2':
                    dest_id = 2
                case 'home3':
                    dest_id = 3
                case 'home4':
                    dest_id = 4
                case _:
                    dest_id = 1


            commandString = (f'sql select object_id, trim(substr(ap.class,instr(ap.class,\'.BP_PL\')+7),\'_C\'), '
                             f'ap.x,ap.y,ap.z from actor_position ap '
                             f'left join properties p on ap.id = p.object_id '
                             f'where hex(p.value) like '
                             f'( select \'%\' || hex(a.platformId) || \'%\' from account a '
                             f'left join characters c on a.id = c.playerId '
                             f'left join properties p2 on a.id = p2.object_id '
                             f'where c.id = {character.id} ) '
                             f'order by ap.x asc limit 4;')

            # commandString = (f'sql select x,y,z from actor_position where id in '
            #                  f'(select object_id from properties '
            #                  f'where hex(value) like \'%{hex_name}%\' '
            #                  f'and name like \'%BP_BAC_SpawnPoints_C.SpawnOwnerName%\' limit 1)')
            # print(commandString)

            rconResponse = runRcon(f'{commandString}')
            if rconResponse.error:
                print(f'RCON error in hex lookup')
                return
            rconResponse.output.pop(0)
            # print(rconResponse)

            for count, x in enumerate(rconResponse.output, start=1):
                match = re.findall(r'\s+\d+ | [^|]*', x)
                object_id = match[0].strip()
                spawn_type = match[1].strip()
                target_x = match[2].strip()
                print(float(target_x))
                if float(target_x) >= 500000:
                    map_loc = 'Siptah'
                else:
                    map_loc = 'Exiled Lands'
                target_y = match[3].strip()
                target_z = match[4].strip()
                key_list = key_list + [count]
                coordinates.append([object_id, spawn_type, map_loc, target_x, target_y, target_z])

            # print(coordinates)
            if not coordinates:
                print(f'RCON error in parsing')
                await ctx.send(f'Found no spawn points for {character.char_name}!')
                return

            spawn_points = dict(zip(key_list, coordinates))
            print(spawn_points)

            final_target_x = float(spawn_points[dest_id][3])
            final_target_y = float(spawn_points[dest_id][4])
            z_offset = int(get_bot_config(f'home_z_offset'))
            final_target_z = float(spawn_points[dest_id][5]) + z_offset
            final_map_loc = spawn_points[dest_id][2]
            final_spawn_type = spawn_points[dest_id][1]

            sq_x, sq_y, map_loc_b = transform_coordinates(final_target_x, final_target_y)

            if 'list' in info or 'list' in ctx.invoked_with:
                outputString = ''
                for count, coordinate in enumerate(coordinates, start=1):
                    outputString += f'`v/home{count}` - {coordinate}\n'
                await ctx.reply(f'{outputString}')
                return
            elif 'info' in info:
                await ctx.reply(f'`v/{ctx.invoked_with}` will send you to: `{final_spawn_type}` in `{final_map_loc} {sq_x}{sq_y}`')
                return
            elif not info:
                rconCharId = get_rcon_id(character.char_name)
                if not rconCharId:
                    await ctx.reply(f'Character `{name}` must be online to be rescued!')
                    return
                else:
                    if int(get_bot_config(f'EventTeleport')) >= int_epoch_time():
                        home_cost = 0
                        pass
                        # an event is active, do not charge.
                    else:
                        home_cost = int(get_bot_config('home_cost'))
                        if sufficient_funds(character, home_cost):
                            balance = eld_transaction(character, f'Teleport to Home', -home_cost)
                            pass
                        else:
                            balance = int(get_balance(character))
                            await ctx.reply(
                                f'Insufficient funds! Available Bronze Coins: {balance}. Needed: {home_cost}')
                            return
                    # print(f'{home_cost}')
                    if home_cost != 0:
                        run_console_command_by_name(character.char_name,
                                                    f'TeleportPlayer {final_target_x} {final_target_y} {final_target_z}')
                        await ctx.reply(f'Returned `{name}` to `{final_spawn_type}` in `{final_map_loc} {sq_x}{sq_y}`'
                                        f' for `{home_cost}` Bronze Coins.'
                                        f'\nBronze Coin Balance: `{balance}`')
                        return
                    else:
                        run_console_command_by_name(character.char_name,
                                                    f'TeleportPlayer {final_target_x} {final_target_y} {final_target_z}')
                        # runRcon(f'con {rconCharId} TeleportPlayer {target_x} {target_y} {target_z}')
                        await ctx.reply(f'Returned `{name}` to `{final_spawn_type}` in `{final_map_loc} {sq_x}{sq_y}`')
                        return
            else:
                await ctx.reply(f'Invalid value in `info`. Use `v/help home`')
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
                run_console_command_by_name(character.char_name, f'TeleportPlayer {x} {y} {z}')
                await ctx.reply(f'Rescued `{name}` from the floor, teleported to `{description}`.')
                return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Warps(bot))
