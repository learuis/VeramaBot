import discord
from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id
from functions.externalConnections import runRcon

class CharacterMods(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='shrink', aliases=['grow'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def small(self, ctx, discord_user: discord.Member):
        """
        Use with v/shrink or v/grow

        Parameters
        ----------
        ctx
        discord_user
            Mention the user to change size

        Returns
        -------

        """

        if 'shrink' in ctx.invoked_with:
            size_value = f'0000403f'
        elif 'grow' in ctx.invoked_with:
            size_value = f'0000a03f'
        else:
            outputString = f'Must specify desired size. Use `v/shrink` or `v/grow`!'
            await ctx.reply(content=outputString)
            return

        message = await ctx.reply(f'Altering height...\n')

        character = is_registered(discord_user.id)

        if not character:
            outputString = f'No character registered to {ctx.message.author.mention}!'
            await message.edit(content=outputString)
            return

        if get_rcon_id(character.char_name):
            outputString = f'Character `{character.char_name}` must be offline to change size'
            await message.edit(content=outputString)
            return

        outputString = f'Altering height of {character.char_name}\n'
        await message.edit(content=outputString)

        rconCommand = (f'sql update properties set value = ( select substr(value,1,1857) || x\'{size_value}\' || '
                       f'substr(value,1862) from properties where name = \'BasePlayerChar_C.CharacterLayout\' '
                       f'and object_id = {character.id} ) where name = \'BasePlayerChar_C.CharacterLayout\' '
                       f'and object_id = {character.id}')
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            outputString = f'Error on {rconCommand}'
        else:
            outputString = (f'`{ctx.invoked_with}` on `{character.char_name}` has been applied.\n'
                            f'IMPORTANT: The character MUST log in before attempting to change size again.')
        await message.edit(content=outputString)
        return

    @commands.command(name='tattoo', aliases=['warpaint'])
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def tattoo(self, ctx):
        """- Converts your active warpaint to a permanent tattoo that lasts through death

        Character must be offline to use this command. A normal warpaint must be applied before using this command.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        message = await ctx.reply(f'Converting warpaint to tattoo:\n')

        character = is_registered(ctx.message.author.id)

        if not character:
            outputString = f'No character registered to {ctx.message.author.mention}!'
            await message.edit(content=outputString)
            return

        if get_rcon_id(character.char_name):
            outputString = f'Character `{character.char_name}` must be offline to convert warpaint to a tattoo!'
            await message.edit(content=outputString)
            return

        rconCommand = (f'sql delete from item_inventory where item_id = 11 '
                       f'and owner_id = {character.id} and inv_type = 1')
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            outputString = f'Error on {rconCommand}'
        else:
            outputString = f'Converted warpaint to tattoo for character `{character.char_name}`.\n'
        await message.edit(content=outputString)
        return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(CharacterMods(bot))
