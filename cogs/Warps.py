from discord.ext import commands
from functions.common import custom_cooldown, flatten_list, is_registered, get_rcon_id
from functions.externalConnections import db_query, runRcon


class Warps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='warp')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def warp(self, ctx, destination: str):
        """

        Parameters
        ----------
        ctx
        destination

        Returns
        -------

        """
        output = db_query(f'select * from warp_locations where warp_name like \'%{destination.casefold()}%\' limit 1')

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
            await ctx.reply(f'Teleported `{name}` to the {description}.')
            return

        # #output_list = list(sum(output, ()))
        #
        # for location in output:
        #     (warp_id, description, warp_name, marker_label, x, y, z, marker_flag) = location

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Warps(bot))
