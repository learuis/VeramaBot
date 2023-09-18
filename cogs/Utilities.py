import sqlite3
import sys

from discord.ext import commands

from time import strftime, localtime

from functions.common import *

class Utilities(commands.Cog):
    """Cog class containing commands related to server status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='eldarium',
                      aliases=['Eldarium', 'eld', 'e'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def eldarium(self, ctx, stacks: int, heads: int, keys: int, skulls: int):
        """- Calculates Eldarium value for a list of materials.

        Returns the spawnitem command for pasting into the game console.

        ===============================================

        Example: For 10 Stacks of materials, 3 Dragon Heads, 6 Skeleton Keys, and 72 Sorcerer Skulls

        Usage: v/eld 10 3 6 72

        Parameters
        ----------
        ctx
        stacks
            - Stacks of Materials (worth 25)
        heads
            - Dragon Heads (worth 25)
        keys
            - Skeleton Keys (worth 5)
        skulls
            - Sorcerer Skulls (worth 1)

        Returns
        -------

        """

        converted = str((stacks * 25) + (heads * 25) + (keys * 5) + skulls)
        await ctx.send(f'Eldarium conversion for {stacks} stacks, {heads} heads, {keys} keys, {skulls} skulls:' +
                       f'\n`spawnitem 11498 {str(converted)}`')

    @commands.command(name='bye')
    @commands.has_any_role('Admin')
    @commands.check(checkChannel)
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

    @commands.command(name='who',
                      aliases=['search', 'find'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def who(self, ctx, *args):
        """- Search for a player name in various places

        Searches lobby, registration channel, archived-registration channel, and game logs for a player name.

        Try to use full names, as short search terms may return a ton of results.

        Make take up to 1 minute to return results. Please don't spam this command!

        Parameters
        ----------
        ctx
        args
            - Player name string to search for

        Returns
        -------

        """
        searchTerm = ''

        if args:
            for x in args:
                searchTerm += f'{str(x)} '
            searchTerm = searchTerm.rstrip(searchTerm[-1])

        searchTerm = searchTerm.casefold()
        returnList = []
        queryOutput = []
        outputString = ''

        if len(searchTerm) < 3:
            await ctx.send(f'Please enter a longer search string.')
            return

        message = await ctx.send('Search started...')

        channel = self.bot.get_channel(1078407672589734088)
        # 1078407672589734088 reg
        # 1144882044552364093 test
        # 1033801560427335750 lobby
        # 1053076840207634442 old-reg
        await message.edit(content='Searching Registration...')
        messages = [message async for message in channel.history(limit=None)]
        for x in messages:
            if searchTerm in x.content.casefold():
                returnList.append(['__Posted in Registration__', x.content, x.author, x.created_at])

        await message.edit(content='Searching Archived-Registration...')
        channel = self.bot.get_channel(1053076840207634442)
        messages = [message async for message in channel.history(limit=None)]

        for x in messages:
            if searchTerm in x.content.casefold():
                returnList.append(['__Posted in Archived-Registration__', x.content, x.author, x.created_at])

        await message.edit(content='Searching Lobby...')
        channel = self.bot.get_channel(1033801560427335750)
        messages = [message async for message in channel.history(limit=None)]

        for x in messages:
            if searchTerm in x.content.casefold():
                returnList.append(['__Posted in Lobby__', x.content, x.author, x.created_at])

        await message.edit(content='Searching Server Logs...')
        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        processSearchTerm = ununicode(searchTerm)

        cur.execute(f'select distinct characterName, platformId, beGUID, funcomId from Players where '
                    f'characterName like \'%{processSearchTerm}%\' or funcomId like \'%{processSearchTerm}%\'')
        queryList = cur.fetchall()

        if queryList:
            for x in queryList:
                platformId = x[1]
                characterName = x[0]
                beGUID = x[2]
                funcomId = x[3]
                queryOutput.append(['__Match in Logs__', platformId, characterName, beGUID, funcomId])

        if returnList:
            for x in returnList:
                x[1] = re.sub('<@&1024017048935874581>', '', x[1])
                x[1] = re.sub('<@&1060426379025457213>', '', x[1])

                outputString += f'\n{x[0]}\nPosted on: {x[3]}\nPosted by: {x[2].mention} ({x[2]})\n{x[1]}\n=========='

        if queryOutput:
            for x in queryOutput:
                outputString += (f'\n{x[0]}\nPlatform ID: {x[1]}\nCharacter Name: {x[2]}\nBE GUID: {x[3]}\n'
                                 f'Funcom ID: {x[4]}')

        splitOutput = ''
        once = True

        if outputString:
            if len(outputString) > 10000:
                await message.edit(content=f'Too many results ({len(outputString)} characters!) '
                                           f'Try a more specific search string!')
                return
            if len(outputString) > 1800:
                workList = outputString.splitlines()
                for items in workList:
                    splitOutput += f'{str(items)}\n'
                    if len(str(splitOutput)) > 1800:
                        if once:
                            once = False
                            await message.edit(content=str(splitOutput))
                            splitOutput = '(continued)\n'
                        else:
                            await ctx.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                    else:
                        continue
                await ctx.send(str(splitOutput))
            else:
                await message.edit(content=str(outputString))
        else:
            await message.edit(content=f'No matching entries found.')

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Utilities(bot))
