import math
import sys
import time
import sqlite3
import re
import os

from discord.ext import commands

from time import localtime, strftime

from functions.common import custom_cooldown, ununicode, get_rcon_id, is_registered

from functions.externalConnections import runRcon, db_query

TOKEN = os.getenv('DISCORD_TOKEN')

async def split_message(outputString, author):
    splitOutput = ''
    once = True

    if outputString:
        if len(outputString) > 20000:
            await author.send(f'Too many results!')
            return
        if len(outputString) > 1800:
            workList = outputString.splitlines()
            for items in workList:
                splitOutput += f'{str(items)}\n'
                if len(str(splitOutput)) > 1800:
                    if once:
                        once = False
                        await author.send(str(splitOutput))
                        splitOutput = '(continued)\n'
                    else:
                        await author.send(str(splitOutput))
                        splitOutput = '(continued)\n'
                else:
                    continue
        else:
            await author.send(str(outputString))
class Utilities(commands.Cog):
    """Cog class containing commands related to server status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='eldarium',
                      aliases=['Eldarium', 'eld', 'e'])
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def eldarium(self, ctx, gold_coins: int = 0, gold_bars: int = 0):
        """- Calculated Decaying Eldarium value for a list of materials.

        Returns the spawnitem command for pasting into the game console.

        Example: 3,245 gold coins and 202 gold ingots
        Usage: v/eld 3245 202

        Parameters
        ----------
        ctx
        gold_coins
        gold_bars

        Returns
        -------

        """

        leftover = gold_coins % 10
        print(leftover)
        rounded_gold_coins = math.floor(gold_coins * 10) / 10
        print(rounded_gold_coins)

        converted = int((rounded_gold_coins / 10)) + (int(gold_bars) * 3)
        await ctx.send(f'`{leftover}` gold coins rounded off.\n'
                       f'Decaying Eldarium conversion for `{int(rounded_gold_coins)}` '
                       f'gold coins, `{gold_bars}` gold bars = `{converted}`:\n\n`spawnitem 11499 {converted}`')

    @commands.command(name='s3_eldarium')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def s3_eldarium(self, ctx, stacks: int, heads: int, keys: int, skulls: int):
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

    @commands.command(name='bot')
    @commands.has_any_role('Admin')
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
        await ctx.send(f'Attempting to restart bot... {quittime}.')
        await ctx.bot.close()
        await ctx.bot.login(TOKEN)

    @commands.command(name='namelookup',
                      aliases=['search', 'find'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def namelookup(self, ctx, *args):
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

    @commands.command(name='market')
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def market(self, ctx):
        """- Teleports you to the market.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        if not ctx.bot.market_night:
            await ctx.reply(f'This command can only be used during Market Night!')
            return

        character = is_registered(ctx.author.id)

        if not character:
            await ctx.reply(f'No character registered to player {ctx.author.mention}!')
            return
        else:
            name = character.char_name

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{name}` must be online to teleport to the Market!')
            return
        else:
            #runRcon(f'con {rconCharId} TeleportPlayer -37665.277344 182622.6875 -8276.037109')
            #runRcon(f'con {rconCharId} TeleportPlayer 129890.84375 190925.296875 -19617.917969')
            runRcon(f'con {rconCharId} TeleportPlayer -14452.919922 209139.703125 -17296.822266')
            await ctx.reply(f'Teleported `{name}` to the Market.')
            return

    @commands.command(name='outcastoverview', aliases=['oo', 'overview'])
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def outcastoverview(self, ctx, command: str = 'top', name: str = False):
        """ - Reviews kills for the most recent season


        Usage Examples:

        Top 25 Most Kills

        v/outcastoverview top

        Character's Top 25 Kill Counts by Enemy Type

        v/outcastoverview character Sergio

        Your own full Overview:

        v/outcastoverview me

        Top Kill Counts by Enemy Type:

        v/outcastoverview type

        Top Kill Counts for matching Enemy Types:

        v/outcastoverview type dragon

        Parameters
        ----------
        ctx
        command
            type <name> | character <name> | top | me
        name

        Returns
        -------

        """
        outputString = ''
        splitOutput = ''
        once = True
        place = 0

        command.strip()

        match command:
            case 'type':
                if name:
                    output = db_query(f'select enemy_name, character_name, max(kills) from kill_counter '
                                      f'where kills > 1 and enemy_name like \'%{name}%\' '
                                      f'group by enemy_name order by kills desc, enemy_name desc;')
                    if output:
                        outputString += f'**Most Kills (>=10) of Enemy Types matching `{name}`**:\n'
                    else:
                        outputString += f'No results.'
                else:
                    output = db_query(f'select enemy_name, character_name, max(kills) from kill_counter '
                                      f'where kills >= 10 group by enemy_name order by kills desc , enemy_name desc;')
                    if output:
                        outputString += f'**Most Kills of All Enemy Types**:\n'
                    else:
                        outputString += f'No results.'

                for record in output:
                    (enemy_name, character_name, kills) = record
                    outputString += f'{enemy_name} - {character_name} - {kills}\n'

            case 'me':
                char_info = is_registered(ctx.author.id)
                if not char_info:
                    await ctx.send(f'Your character must be registered in order to see your full Outcast Overview!')
                output = db_query(f'select enemy_name, character_name, count(character_name) from wrapped '
                                  f'where character_name = \'{char_info.char_name}\' '
                                  f'group by enemy_name order by count(character_name) desc;')
                if output:
                    count = db_query(f'select count(character_name) from wrapped '
                                     f'where character_name = \'{char_info.char_name}\'')
                    count = sum(count, ())

                    ranking = db_query(f'select character_name, count(character_name) '
                                       f'from wrapped group by character_name order by count(character_name) desc;')

                    for index, line in enumerate(ranking):
                        if char_info.char_name in line:
                            place = index + 1

                    outputString += f'**Outcast Overview for {char_info.char_name}:**\n'
                    outputString += f'**Total Kills: {count[0]} (Rank: {place})**\n'
                    outputString += f'Detailed information sent via DM.\n'

                    await ctx.reply(f'{outputString}')

                    for record in output:
                        (enemy_name, character_name, kills) = record
                        outputString += f'{enemy_name} - {kills}\n'

                    await split_message(outputString, ctx.message.author)
                    return

            case 'top':
                output = db_query(f'select character_name, count(character_name) '
                                  f'from wrapped group by character_name order by count(character_name) desc limit 25;')
                if output:
                    outputString += f'**Outcast Overview: Top 25 Most Kills**\n\n'
                    for index, record in enumerate(output):
                        (character_name, kills) = record
                        outputString += f'{index+1} - {character_name} - {kills}\n'

            case 'character':
                if name:
                    output = db_query(f'select enemy_name, character_name, count(character_name) from wrapped '
                                      f'where character_name like \'%{name}%\' '
                                      f'group by enemy_name order by count(character_name) desc limit 25;')
                    if output:
                        outputString += (f'**Outcast Overview: Top 25 Enemies Killed by '
                                         f'character names matching `{name}`:**\n\n')
                        for record in output:
                            (enemy_name, character_name, kills) = record
                            outputString += f'{enemy_name} - {kills}\n'
                    else:
                        outputString += f'No character found named {command}'
                else:
                    outputString += f'Character name must be provided! Use `v/help outcastoverview`'

            case _:
                outputString += f'Incorrect command syntax! Use `v/help outcastoverview`'

        if outputString:
            if len(outputString) > 20000:
                await ctx.send(f'Too many results!')
                return
            if len(outputString) > 1800:
                workList = outputString.splitlines()
                for items in workList:
                    splitOutput += f'{str(items)}\n'
                    if len(str(splitOutput)) > 1800:
                        if once:
                            once = False
                            await ctx.author.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                        else:
                            await ctx.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                    else:
                        continue
            else:
                await ctx.send(str(outputString))

        return


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Utilities(bot))
