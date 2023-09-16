import discord
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel, is_registered, get_rcon_id, popup_to_player
from functions.externalConnections import runRcon, db_query

class Rewards(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reward', aliases=['give', 'giveitem', 'prize', 'spawnitem'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def giveReward(self, ctx, itemId: int, quantity: int, discord_user: discord.Member, *reason):
        """

        Parameters
        ----------
        ctx
        itemId
        quantity
        discord_user
        reason

        Returns
        -------

        """
        itemName = ''

        charId = is_registered(discord_user.name)
        rconCharId = get_rcon_id(charId.char_name)

        result = db_query(f'select name from cust_item_xref where template_id = {itemId} limit 1')

        for x in result:
            itemName = x[0]

        reasonString = f'You have been granted {quantity} {itemName} for: '
        for word in reason:
            reasonString += f'{word} '

        rconCommand = f'con {rconCharId} spawnitem {itemId} {quantity}'
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            await ctx.send(f'Authentication error on {rconCommand}')
        else:
            for x in rconResponse.output:
                await ctx.send(f'Gave `{quantity} {str(itemName)} (item id {itemId})` to `{charId.char_name}`.'
                               f'\nRcon command output:{x}\nMessaged {charId.char_name}: {reasonString}')
                popup_to_player(charId.char_name, reasonString)


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Rewards(bot))
