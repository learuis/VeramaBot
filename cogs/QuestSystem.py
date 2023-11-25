import re

from discord.ext import commands
from functions.common import custom_cooldown, is_registered
from functions.externalConnections import runRcon


async def questUpdate():

    connected_chars = []

    rconResponse = runRcon(f'sql select a.id, c.char_name from actor_position as a where x >= -189430 '
                           f'and y >= 104557 and x <= -184930 and y <= 106557 '
                           f'and a.class like \'%BasePlayerChar_C%\' '
                           f'left join characters as c on c.id = a.id limit 1')
    for x in rconResponse.output:
        rconResponse.output.pop(0)
        match = re.findall(r'\s+\d+ | [^|]*', x)
        connected_chars.append(match)
        print(connected_chars)

    if not connected_chars:
        print(f'No one is in the box.')
        return

    for x in connected_chars:
        print(f'Player `{x[1].strip()}` is in the box with rcon ID `{x[0].strip()}`.')
        return

    # if not character:
    #     await ctx.reply(f'**Proving Grounds Testing**\n'
    #                     f'Could not find a character registered to {ctx.author.mention}.')
    #     return
    #
    # rconCharId = get_rcon_id(character.char_name)
    # if not rconCharId:
    #     await ctx.reply(f'**Proving Grounds Testing**\n'
    #                     f'Character {character.char_name} must be online to begin the Proving Grounds.')
    #     return


class QuestSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='checkprogress')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def checkProgress(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(QuestSystem(bot))
