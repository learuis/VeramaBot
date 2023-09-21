from discord.ext import commands
from functions.common import custom_cooldown, checkChannel, get_rcon_id, popup_to_player, \
    get_single_registration
from functions.externalConnections import runRcon, db_query

class Rewards(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reward', aliases=['give', 'giveitem', 'prize', 'spawnitem'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def giveReward(self, ctx, itemId: int, quantity: int, name: str, *reason):
        """- Gives a reward to the tagged player

        Parameters
        ----------
        ctx
        itemId
            Item ID number to spawn
        quantity
            How many of the item to spawn
        name
            Character name. Must be registered and linked to char id.
        reason
            A message which will pop up for the character in game.

        Returns
        -------

        """
        itemName = ''

        characters = get_single_registration(name)
        if not characters:
            await ctx.send(f'No character named `{name}` registered!')
            return
        else:
            name = characters[1]

        rconCharId = get_rcon_id(name)

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
                await ctx.send(f'Gave `{quantity} {str(itemName)} (item id {itemId})` to `{name}`.'
                               f'\nRcon command output:{x}\nMessaged {name}: {reasonString}')
                popup_to_player(name, reasonString)


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Rewards(bot))
