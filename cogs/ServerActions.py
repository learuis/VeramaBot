import io
import random
import re

from discord.ext import commands
from functions.externalConnections import runRcon
from functions.common import custom_cooldown, checkChannel

class ServerActions(commands.Cog):
    """Cog class containing commands related to server status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='listplayers',
                      aliases=['list', 'lp'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
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
        string = ''

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
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
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

        file = io.open('data/markers.dat', mode='r')
        for line in file:
            settings_list.append(f'{line}')

        for command in settings_list:
            rconResponse = runRcon(command)
            if rconResponse.error == 1:
                rconResponse.output = f'Authentication error on {command}'
            rconOutput.extend(rconResponse.output)

        await message.edit(content=f'{len(settings_list)} markers have been placed!\n' +
                                   '\n'.join(rconOutput))
        await message.edit(suppress=True)

    @commands.command(name='boss')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def boss(self, ctx, charName: str,
                   numberToSpawn: int = commands.parameter(default=1)):
        """- Spawns a random Siptah boss at cursor position.

        Uses RCON to spawn a random Siptah boss at the location your target is currently pointing at

        Parameters
        ----------
        ctx
        charName
            - Character name to run command as
        numberToSpawn
            - Number of enemies to spawn
        Returns
        -------

        """

        monsterlist = []
        monsterOutput = []
        checkName = ''
        commandTarget = 99

        for counter in range(numberToSpawn):

            file = io.open('boss_py.dat', mode='r')

            for line in file:
                monsterlist.append(line)

            monster = random.choice(monsterlist)
            monsterOutput.append(monster)
            monster = f'dc spawn exact {monster}'

            rconResponse = runRcon('listplayers')

            del rconResponse[0]
            for x in rconResponse:
                if x[1] == charName:
                    # later, contains
                    commandTarget = x[0]
                    checkName = x[1]
            if charName == checkName:
                runRcon(f'con {commandTarget} {monster}')
            file.close()

        await ctx.send(f'Spawned {numberToSpawn} random bosses at {charName}\'s location.\n' + ''.join(monsterOutput))

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(ServerActions(bot))
