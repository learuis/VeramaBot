import io
import re
import time
import sqlite3

from discord.ext import commands
from functions.externalConnections import runRcon, downloadSave
from functions.common import custom_cooldown, modChannel
from datetime import datetime
from datetime import timezone
from time import strftime

class Admin(commands.Cog):
    """Cog class containing commands related to server status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='restart')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def restart(self, ctx, sure: bool):
        """- Immediately restarts the Conan Exiles server.

        No restart warning is broadcast in game when using this command.

        The server will be automatically restarted by G-portal.

        Parameters
        ----------
        ctx
        sure: bool
            Are you sure? y | n

        Returns
        -------

        """

        if sure != 'y':
            await ctx.send(f'Command must be confirmed using with v/restart y')

        rconResponse = runRcon('exit')

        if rconResponse.error == 1:
            rconResponse.output = f'Authentication error on exit command.'
        else:
            rconResponse.output = f'Server will restart immediately.'

        await ctx.send(rconResponse.output)
        # I could add a lookup for their account ID here also and link back to their character ID.

    @commands.command(name='rcon')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def rcon(self, ctx, *args):
        """- Use RCON to run a single command

        Uses RCON to run any single desired command, returns raw output.

        Parameters
        ----------
        ctx
        args
            - Single rcon command (can contain spaces)

        Returns
        -------

        """
        command = ''
        formattedOutput = ''

        for arg in args:
            command += f'{arg} '

        command = re.sub(';', '\"', command)

        rconResponse = runRcon(command)

        # for x in rconResponse.output:
        # if x[0]!='Idx':
        # connected_chars.append(x[1])

        for x in rconResponse.output:
            formattedOutput += str(x) + '\n'

        await ctx.send(formattedOutput)
        # I could add a lookup for their account ID here also and link back to their character ID.

    @commands.command(name='gamechat')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def gamechat(self, ctx):
        """- Parses in-game chat and posts to Discord

        Parses the active log file for all ChatWindow lines, writes them to

        the database, then outputs any lines which have not yet been output to Discord.

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        lineCounter = 0
        outputString = ''
        splitOutput = ''

        log = downloadSave()

        file = io.open(log.name, 'r')

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        for line in file:
            if 'ChatWindow' in line:
                lineCounter += 1
                line = line.replace('\'', '')
                cur.execute(f'insert or ignore into chatlog (message_content) values (\'{line}\')')
                con.commit()

        await ctx.send(f'Parsed {lineCounter} chat messages from logs.')

        cur.execute(f'select message_id, message_content from chatlog where sent_to_discord is null')
        res = cur.fetchall()

        if res:
            if len(res) > 1:
                highestLine = res[-1]
            else:
                highestLine = res[0]
        else:
            await ctx.send(f'No new records to output.')
            return

        highest = highestLine[0]

        cur.execute(f'update chatlog set sent_to_discord = 1 where message_id <= {highest}')
        con.commit()
        con.close()

        await ctx.send(f'Writing {len(res)} lines out to Discord.')
        for line in res:
            line = re.sub(r'^.*Character ', '', str(line))
            line = line[:-4]
            outputString += f'{line}\n'

        if outputString:
            if len(outputString) > 1800:
                workList = outputString.splitlines()
                for items in workList:
                    splitOutput += f'{str(items)}\n'
                    if len(str(splitOutput)) > 1800:
                        await ctx.send(str(splitOutput))
                        splitOutput = ''
                    else:
                        continue
                await ctx.send(str(splitOutput))
            else:
                await ctx.send(str(outputString))

    @commands.command(name='veteran', aliases=['vet', 'vets'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def veteran(self, ctx):
        """- Creates a list of Veteran Outcast candidates

        Searches for members who joined before 6/29/23 and posted in player-registration
        after 6/22/23. Tags the member and links their registration post

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        print(0)
        outputString = ('__Members that joined before 6/29/23 that do not have Veteran Role and '
                        'registered a character:__\n')
        splitOutput = ''

        channel = self.bot.get_channel(1023741745810378837)

        members = channel.members

        channel = self.bot.get_channel(1078407672589734088)
        # 1078407672589734088 reg
        messages = [message async for message in channel.history(limit=None)]

        for member in members:
            if member.get_role(1060693908503400489):
                continue

            if time.mktime(datetime.utctimetuple(member.joined_at)) < float(1687996799):
                for message in messages:
                    if str(message.author) in outputString:
                        continue
                    if (message.author == member and
                            message.created_at > datetime.fromtimestamp(1687406401, timezone.utc)):
                        joindate = strftime('%m/%d/%y at %H:%M:%S', datetime.utctimetuple(member.joined_at))
                        outputString += (f'{message.author} {member.mention} joined on {joindate} and '
                                         f'registered on {message.created_at} {message.jump_url}\n')

        if not outputString:
            await ctx.send(f'No members meet the criteria for Veteran Status')
            return

        # make this a function returning a list of strings with ~1800 characters each, then loop the list to output
        if len(outputString) > 1800:
            workList = outputString.splitlines()
            for items in workList:
                splitOutput += f'{str(items)}\n'
                print(splitOutput)
                if len(str(splitOutput)) > 1800:
                    await ctx.send(splitOutput)
                    splitOutput = ''
            await ctx.send(str(splitOutput))
        else:
            await ctx.send(outputString)

    @commands.command(name='maintenance')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def maintenance(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        ctx.bot.maintenance_flag = not ctx.bot.maintenance_flag
        await ctx.send(f'Maintenance Flag: {ctx.bot.maintenance_flag}')
        print(ctx.bot.maintenance_flag)

async def setup(bot):
    await bot.add_cog(Admin(bot))
