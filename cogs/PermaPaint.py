from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id
from functions.externalConnections import runRcon


class PermaPaint(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='warpaint')
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def warpaint(self, ctx, option: str = commands.parameter(default='apply')):
        """- Modifies your active warpaint so that it is not removed upon death.

        Character must be offline to use this command. A normal warpaint must be applied before using this command.

        Parameters
        ----------
        ctx
        option
            remove | apply

        Returns
        -------

        """

        outputString = f'Commencing warpaint death persistence process:\n'
        message = await ctx.reply(content=outputString)

        charId = is_registered(ctx.message.author.id)

        if not charId:
            outputString = f'No character registered to {ctx.message.author.mention}!'
            await message.edit(content=outputString)
            return

        if get_rcon_id(charId.char_name):
            outputString = f'Character `{charId.char_name}` must be offline to modify permanent warpaints!'
            await message.edit(content=outputString)
            return

        rconCommand = f'sql delete from item_inventory where item_id = 25 and owner_id = {charId.id} and inv_type = 1'
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            outputString = f'Error on {rconCommand}'
            await message.edit(content=outputString)
            return
        else:
            for x in rconResponse.output:
                print(f'{x}')
                outputString = f'Removed all persistent warpaints applied to `{charId.char_name}`.\n'
                await message.edit(content=outputString)
                if 'remove' in option.casefold():
                    outputString += f'You may need to use Sloughing Fluid to fully remove the warpaint or tattoo.\n'
                    await message.edit(content=outputString)
                    return

        rconCommand = (f'sql update or ignore item_inventory set item_id = 25 '
                       f'where item_id = 11 and owner_id = {charId.id} and inv_type = 1')
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            outputString = f'Error on {rconCommand}'
            await message.edit(content=outputString)
            return
        else:
            for x in rconResponse.output:
                print(f'{x}')
                outputString += (f'Successfully made the warpaint of `{charId.char_name}` persist through death.\n'
                                 f'Warpaints still expire after 1-4 hours. Log in and then use `v/tattoo` to make '
                                 f'it permanent.')
                await message.edit(content=outputString)

    @commands.command(name='tattoo')
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def tattoo(self, ctx, option: str = commands.parameter(default='apply')):
        """- Convert your death-persistent warpaint into a tattoo that will not expire over time

        Character must be online to use this command, and must have a persistent warpaint from v/warpaint

        Parameters
        ----------
        ctx
        option
            remove | apply

        Returns
        -------

        """
        outputString = f'Commencing tattoo process:\n'
        message = await ctx.reply(content=outputString)

        charId = is_registered(ctx.message.author.id)

        if not charId:
            outputString = f'No character registered to {ctx.message.author.mention}!'
            await message.edit(content=outputString)
            return

        if not get_rcon_id(charId.char_name):
            outputString = f'Character `{charId.char_name}` must be online to convert warpaint into a tattoo!'
            await message.edit(content=outputString)
            return

        rconId = get_rcon_id(charId.char_name)

        if 'remove' in option.casefold():
            outputString += f'Please log out and use `v/warpaint` to remove tattoos.\n'
            await message.edit(content=outputString)
            return

        #rconCommand = f'con {rconId} setinventoryitemfloatstat 25 12 -1 1'
        rconCommand = f'con {rconId} setinventoryitemfloatstat 25 7 100000000 1'
        rconResponse1 = runRcon(rconCommand)
        rconCommand = f'con {rconId} setinventoryitemfloatstat 25 8 100000000 1'
        rconResponse2 = runRcon(rconCommand)

        if rconResponse1.error == 1 or rconResponse2.error == 1:
            outputString = f'Error on {rconCommand}'
            await message.edit(content=outputString)
            return
        else:
            for x in rconResponse1.output:
                print(f'{x}')
                outputString = f'Converted warpaint to tattoo for `{charId.char_name}`.\n'
                await message.edit(content=outputString)

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(PermaPaint(bot))
