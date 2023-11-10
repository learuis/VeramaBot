import io
import re
import time
import sqlite3

from discord.ext import commands

from functions.externalConnections import runRcon, downloadSave, db_query
from functions.common import custom_cooldown, modChannel, is_registered, get_rcon_id, get_single_registration
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

    @commands.command(name='charswap')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def charswap(self, ctx, activate_char: str):
        """

        Parameters
        ----------
        ctx
        activate_char
            Select main or alt

        Returns
        -------

        """

        # store account.id and account.user, character.id in a table in the veramambot db
        # check that both characters are offline
        # check if account.user = main account.user
        # if so, change modify main account.user to a temp value
        # set the alt account.user to the main account.user
        # set the main account.user to the alt account.user
        # commit and close

        character = is_registered(ctx.author.id)
        outputString = ''

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return
        else:
            con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
            cur = con.cursor()

            cur.execute(f'select * from char_swap where main_char_id = {character.id};')
            res = cur.fetchone()

            con.close()

            record_num = res[0]
            main_acct_id = res[1]
            main_acct_user = res[2]
            main_char_id = res[3]
            main_char_name = res[4]
            alt_acct_id = res[5]
            alt_acct_user = res[6]
            alt_char_id = res[7]
            alt_char_name = res[8]

            print(f'{res[0]} {res[1]} {res[2]} {res[3]} {res[4]} {res[5]} {res[6]} {res[7]} {res[8]}')

            outputString = (f'Starting character account swap process...\n'
                            f'{res[0]} {res[1]} {res[2]} {res[3]} {res[4]} {res[5]} {res[6]} {res[7]} {res[8]}')
            message = await ctx.reply(f'{outputString}')

        rconMainId = get_rcon_id(main_char_name)
        rconAltId = get_rcon_id(alt_char_name)

        if rconMainId or rconAltId:
            outputString += (f'\n\nCharacter swap failed! Both `{main_char_name}` and `{alt_char_name}` must be '
                             f'offline to swap characters!')
            await message.edit(content=outputString)
            return
        else:
            outputString += (f'\nCharacters `{main_char_name}` and `{alt_char_name}` are offline. '
                             f'Proceeding with character swap.')
            await message.edit(content=outputString)

            match activate_char:
                case 'alt':
                    response = runRcon(f'sql update account set user = \'{main_char_name}\' where id = {main_acct_id}')
                    if response.error == 1:
                        outputString += f'\nRCON command error.'
                        await message.edit(content=outputString)
                        return
                    else:
                        outputString += f'\n{response.output}'
                        await message.edit(content=outputString)

                    response = runRcon(f'sql update account set user = \'{main_acct_user}\' where id = {alt_acct_id}')
                    if response.error == 1:
                        outputString += f'\nRCON command error.'
                        await message.edit(content=outputString)
                        return
                    else:
                        outputString += f'\n{response.output}'
                        await message.edit(content=outputString)

                    response = runRcon(f'sql update account set user = \'{alt_acct_user}\' where id = {main_acct_id}')
                    if response.error == 1:
                        outputString += f'\nRCON command error.'
                        await message.edit(content=outputString)
                        return
                    else:
                        outputString += f'\n{response.output}'
                        await message.edit(content=outputString)

                    outputString += (f'\nCharacter swap from main `{main_char_name}` to alt `{alt_char_name}` '
                                     f'is complete')
                    await message.edit(content=outputString)
                    return

                case 'main':
                    response = runRcon(f'sql update account set user = \'{alt_char_name}\' where id = {alt_acct_id}')
                    if response.error == 1:
                        outputString += f'\nRCON command error.'
                        await message.edit(content=outputString)
                        return
                    else:
                        outputString += f'\n{response.output}'
                        await message.edit(content=outputString)

                    response = runRcon(f'sql update account set user = \'{main_acct_user}\' where id = {main_acct_id}')
                    if response.error == 1:
                        outputString += f'\nRCON command error.'
                        await message.edit(content=outputString)
                        return
                    else:
                        outputString += f'\n{response.output}'
                        await message.edit(content=outputString)

                    response = runRcon(f'sql update account set user = \'{alt_acct_user}\' where id = {alt_acct_id}')
                    if response.error == 1:
                        outputString += f'\nRCON command error.'
                        await message.edit(content=outputString)
                        return
                    else:
                        outputString += f'\n{response.output}'
                        await message.edit(content=outputString)

                    outputString += (f'\nCharacter swap from alt `{alt_char_name}` to main `{main_char_name}` '
                                     f'is complete')
                    await message.edit(content=outputString)
                    return

    @commands.command(name='marketnight')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def marketnight(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        ctx.bot.market_night = not ctx.bot.market_night
        await ctx.send(f'Market Night Teleport Flag has been set to {ctx.bot.market_night}')
        print(ctx.bot.maintenance_flag)

    '''@commands.command(name='fixstatus')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def fixStatus(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        if not VeramaBot.liveStatus.is_running():
            VeramaBot.liveStatus.start()
            await ctx.send(f'Attempting to restart status monitor...')'''

    @commands.command(name='dbquery', aliases=['db', 'query'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def dbQuery(self, ctx, query: str):
        """

        Parameters
        ----------
        ctx
        query

        Returns
        -------

        """
        results = db_query(f'{query}')
        if results:
            for result in results:
                await ctx.send(f'{result}\n')
            return
        else:
            await ctx.send(f'Query returned no rows.')
            return

    @commands.command(name='volcano', aliases=['drop', 'getrekt'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def volcano(self, ctx, name: str):
        """Throws the named player into the volcano.

        Parameters
        ----------
        ctx
        name
            Player name to drop!

        Returns
        -------

        """
        character = get_single_registration(name)

        if not character:
            await ctx.reply(f'No character named `{name}` registered!')
            return
        else:
            name = character[1]

        rconCharId = get_rcon_id(name)
        if not rconCharId:
            await ctx.reply(f'Character `{name}` must be online to throw into the Volcano!')
            return
        else:
            runRcon(f'con {rconCharId} TeleportPlayer -17174.951172 -259672.125 87383.28125')
            await ctx.reply(f'Tossed `{name}` into the Volcano.')
            return

    @commands.command(name='jail', aliases=['capture', 'prison'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def volcano(self, ctx, cell: int, name: str):
        """Sends the named player to Fort Greenwall

        Parameters
        ----------
        ctx
        cell
            Cell number to summon the player to.
        name
            Player name to drop!

        Returns
        -------

        """
        rconCharId = get_rcon_id(name)
        if not rconCharId:
            await ctx.reply(f'Character `{name}` must be online to send to Fort Greenwall!')
            return
        else:
            match cell:
                case 0:
                    runRcon(f'con {rconCharId} TeleportPlayer 218110.859375 -124766.046875 -16443.873047')
                case 1:
                    runRcon(f'con {rconCharId} TeleportPlayer 219121.40625 -126644.085938 -16396.664063')
                case 2:
                    runRcon(f'con {rconCharId} TeleportPlayer 218992.71875 -127653.546875 -16312.618164')
                case 3:
                    runRcon(f'con {rconCharId} TeleportPlayer 217231.015625 -127617.046875 -16296.007813')
                case 4:
                    runRcon(f'con {rconCharId} TeleportPlayer 217324.59375 -126616.6875 -16287.055664')
                case _:
                    await ctx.reply(f'Cell Number must be provided (0-4). 0 = Yard')
                    return

            await ctx.reply(f'Sent `{name}` to Fort Greenwall in cell {cell}.')
            return

async def setup(bot):
    await bot.add_cog(Admin(bot))
