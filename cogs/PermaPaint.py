from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id
from functions.externalConnections import runRcon

class PermaPaint(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='tattoo', aliases=['warpaint'])
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def tat2(self, ctx):
        """- Converts your active warpaint to a permanent tattoo that lasts through death

        Character must be offline to use this command. A normal warpaint must be applied before using this command.

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        outputString = f'Converting warpaint to tattoo:\n'
        message = await ctx.reply(content=outputString)

        charId = is_registered(ctx.message.author.id)

        if not charId:
            outputString = f'No character registered to {ctx.message.author.mention}!'
            await message.edit(content=outputString)
            return

        if get_rcon_id(charId.char_name):
            outputString = f'Character `{charId.char_name}` must be offline to convert warpaint to a tattoo!'
            await message.edit(content=outputString)
            return

        rconCommand = f'sql delete from item_inventory where item_id = 11 and owner_id = {charId.id} and inv_type = 1'
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            outputString = f'Error on {rconCommand}'
        else:
            outputString = f'Converted warpaint to tattoo for character `{charId.char_name}`.\n'
        await message.edit(content=outputString)
        return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(PermaPaint(bot))
