import io
import random
import re

from discord.ext import commands
from functions.externalConnections import runRcon
from functions.common import custom_cooldown, modChannel, publicChannel, get_rcon_id, is_registered, place_markers


class ServerActions(commands.Cog):
    """Cog class containing commands related to server status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='listplayers',
                      aliases=['list', 'lp'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def listplayers(self, ctx, name: str = None):
        """- Lists connected players

        Uses RCON to run the listplayers command, returning a list of online players.

        Usage: v/listplayers [optional:name]

        Parameters
        ----------
        ctx
        name
            - If a name is specified, only the record matching name will be shown.

        Returns
        -------

        """

        connected_chars = []
        outputlist = ''

        rconResponse = runRcon('listplayers')
        rconResponse.output.pop(0)

        for x in rconResponse.output:
            match = re.findall(r'\s+\d+ | [^|]*', x)
            connected_chars.append(match)
            print(connected_chars)

        if not connected_chars:
            await ctx.send('0 Players connected.')
            return

        for x in connected_chars:
            if name:
                if name.casefold() in x[1].casefold():
                    #outputlist = f'{x[0].strip()} - {x[1].strip()}\n'
                    await ctx.send(f'Player `{x[1].strip()}` is online with rcon ID `{x[0].strip()}`.')
                    return
            else:
                outputlist += f'{x[0].strip()} - {x[1].strip()}\n'

        if outputlist:
            await ctx.send(str(len(connected_chars)) + f' connected player(s):\n{outputlist}')
        else:
            await ctx.send(f'Player \'{name}\' is not currently online.')
        #I could add a lookup for their account ID here also and link back to their character ID.

    @commands.command(name='markers')
    @commands.has_any_role('Admin', 'Moderator', 'Helper')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(publicChannel)
    async def markers(self, ctx):
        """- Place map markers (req 1 player online)

        Silently place map markers using RCON commands on player 0. At least 1 player must be connected.

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        message = await ctx.send(f'Marker placement in progress... (~20 sec)')

        settings_list = []
        rconOutput = []

        marker_output = place_markers()

        if marker_output:
            await message.edit(content=marker_output)

        return

    @commands.command(name='boss')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def boss(self, ctx):
        """- Spawns a random Siptah boss at cursor position.

        Uses RCON to spawn a random Siptah boss at the location your target is currently pointing at

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        monsterlist = []

        character = is_registered(ctx.author.id)

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        file = io.open('data/boss_py.dat', mode='r')

        for line in file:
            monsterlist.append(line)

        file.close()

        monster = random.choice(monsterlist)
        monster = f'dc spawn exact {monster}'

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character {character.char_name} must be online to spawn bosses')
            return
        else:
            runRcon(f'con {rconCharId} {monster}')

            await ctx.send(f'Spawned `{monster}` at `{character.char_name}\'s` position')
            return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(ServerActions(bot))
