import re
import os
import sys
import time
from time import strftime, localtime

from discord.ext import commands
from functions.externalConnections import runRcon
from functions.common import custom_cooldown, place_markers, set_bot_config, check_channel

TOKEN = os.getenv('DISCORD_TOKEN')

class ServerActions(commands.Cog):
    """Cog class containing commands related to server status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='bye')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    async def bye(self, ctx):
        """- Shut down VeramaBot

        Gracefully exits VeramaBot.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        quittime = strftime('%m/%d/%y at %H:%M:%S', localtime(time.time()))
        await ctx.send(f'Later! VeramaBot shut down on {quittime}.')
        sys.exit(0)

    @commands.command(name='listplayers',
                      aliases=['list', 'lp'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
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
            # print(connected_chars)

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
    @commands.check(check_channel)
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
        set_bot_config(f'markers_last_placed', f'0')

        marker_output = place_markers()

        if marker_output:
            await message.edit(content=marker_output)

        return

    @commands.command(name='bot')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    async def bot(self, ctx):
        """- Restarts down VeramaBot

        Gracefully exits VeramaBot.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        quittime = strftime('%m/%d/%y at %H:%M:%S', localtime(time.time()))
        await ctx.send(f'Attempting to restart stopped bot services... {quittime}.')
        await ctx.bot.close()
        await ctx.bot.login(TOKEN)

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(ServerActions(bot))
