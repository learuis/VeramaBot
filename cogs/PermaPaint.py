from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id
from functions.externalConnections import runRcon


class PermaPaint(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='warpaint')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def warpaint(self, ctx, ):
        """- Modifies your active warpaint so that it is not removed upon death.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        #player crafts whatever warpaint they want to be permanent
        """
            player applies the warpaint
            player logs out
            player runs command on discord while offline
            bot verifies character is offline
            bot moves warpaint from slot 11 to slot 25
            player logs in
            player runs command on discord while online
            bot sets perishrate to -1 on the item in slot 25.
        """
        #check if the item in slot 0 / type 0 is a warpaint
        #if it is, run command to change it to equip into slot 25
        #setinventoryitemintstat 0 17 25 0
        #wait
        #setinventoryitemfloatstat 25 12 -1 1

        charId = is_registered(ctx.message.author.id)

        if not charId:
            outputString = f'No character registered to {ctx.message.author.mention}!'
            await ctx.reply(content=outputString)
            return

        if get_rcon_id(charId.char_name):
            await ctx.reply(f'Character `{charId.char_name}` must be offline to modify permanent warpaints!')
            return

        rconCommand = f'delete from item_inventory where item_id = 25 and owner_id = {charId.id} and inv_type = 1'
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            await ctx.send(f'Error on {rconCommand}')
            return
        else:
            for x in rconResponse.output:
                print(f'{x}')
                outputString = f'Removed all persistent warpaints applied to {charId.char_name}.'
                await ctx.reply(content=outputString)

        rconCommand = (f'sql update or ignore item_inventory set item_id = 25 '
                       f'where item_id = 11 and owner_id = {charId.id} and inv_type = 1')
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            await ctx.send(f'Authentication error on {rconCommand}')
            return
        else:
            for x in rconResponse.output:
                print(f'{x}')
                outputString = f'Successfully made the warpaint of {charId.char_name} persist through death.'
                await ctx.reply(content=outputString)

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(PermaPaint(bot))
