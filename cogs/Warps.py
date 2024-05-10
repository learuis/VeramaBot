from discord.ext import commands
from functions.common import custom_cooldown, flatten_list, is_registered, get_rcon_id, get_bot_config
from functions.externalConnections import db_query, runRcon


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

    @commands.command(name='stuck', aliases=['rescue', 'floor'])
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

        character = is_registered(ctx.author.id)
        destination = get_bot_config('rescue_location')

        if not character:
            await ctx.reply(f'No character registered to player {ctx.author.mention}!')
            return
        else:
            name = character.char_name

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
