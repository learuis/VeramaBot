import io
import sqlite3
import time
import asyncio

from discord.ext import commands
from functions.externalConnections import *
from functions.common import custom_cooldown, checkChannel
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
    @commands.check(checkChannel)
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
    @commands.check(checkChannel)
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

        if len(args) > 1:
            for arg in args:
                command += arg + ' '
        else:
            command = args[0]

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
    @commands.check(checkChannel)
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
    @commands.check(checkChannel)
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

    @commands.command(name='god')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def god(self, ctx):
        """- Presents God selection reaction dialog

        Test only for now. Maybe replace this with a modal?

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        sentMessage = await ctx.send(f'Choose your god:\n\N{peach} = Derketo \N{snowflake} = Ymir \N{latin cross} '
                                     f'= Mitra \N{snake} = Set \N{spider web} = Zath \N{wolf face}) = Jhebbal Sag'
                                     f' \N{octopus} = Yog \N{drop of blood} = Crom')

        print(ctx.bot.emojis)

        #reactionEmoji = discord.utils.get(ctx.bot.emojis, name='peach')
        #1101538132270256189
        await sentMessage.add_reaction(f'\N{peach}')
        await sentMessage.add_reaction(f'\N{snowflake}')
        await sentMessage.add_reaction(f'\N{latin cross}')
        await sentMessage.add_reaction(f'\N{snake}')
        await sentMessage.add_reaction(f'\N{spider web}')
        await sentMessage.add_reaction(f'\N{wolf face}')
        await sentMessage.add_reaction(f'\N{octopus}')
        await sentMessage.add_reaction(f'\N{drop of blood}')

        #u'\U0001F351')  #ctx.bot.get_emoji('peach'))  #reactionEmoji.id))

        def check(reaction, user):
            return user == ctx.message.author  # and str(reaction.emoji) == f'\N{peach}'

        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await sentMessage.delete_message()
        else:
            await sentMessage.edit(content=f'{user} has chosen {reaction}')
            await sentMessage.clear_reactions()

    @commands.command(name='registrationlist', aliases=['reglist'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def register(self, ctx):
        """- Lists all registered characters

        Queries the VeramaBot database for all registered characters.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputString = ''

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()
        cur.execute(f'select * from registration')
        res = cur.fetchall()

        for x in res:
            outputString += f'{x}\n'
        await ctx.send(outputString)
        return

    @commands.command(name='registrationdelete', aliases=['regdelete', 'regdel'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def registrationdelete(self, ctx,
                                 recordToDelete: int = commands.parameter(default=0)):
        """- Delete a record from the registration database

        Deletes a selected record from the VeramaBot database table 'registration'.

        Does not delete the entry in the registration channel.

        Parameters
        ----------
        ctx
        recordToDelete
            Specify which record number should be deleted.
        Returns
        -------

        """
        if recordToDelete == 0:
            await ctx.send(f'Record to delete must be specified. Use `v/help registrationdelete`')
        else:
            try:
                int(recordToDelete)
            except ValueError:
                await ctx.send(f'Invalid record number')
            else:
                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select * from registration where id = {recordToDelete}')
                res = cur.fetchone()

                cur.execute(f'delete from registration where id = {recordToDelete}')
                con.commit()

                await ctx.send(f'Deleted record:\n{res}')

async def setup(bot):
    await bot.add_cog(Admin(bot))
