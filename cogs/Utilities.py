import sqlite3
import re
import os

from discord.ext import commands
from dotenv import load_dotenv

from cogs.QuestSystem import pull_online_character_info_new
from functions.common import custom_cooldown, ununicode, is_registered, get_single_registration, get_rcon_id, \
    flatten_list

from functions.externalConnections import db_query, runRcon

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))


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
                    # output = db_query(False, f'select enemy_name, character_name, max(kills) from kill_counter '
                    #                   f'where kills > 1 and enemy_name like \'%{name}%\' '
                    #                   f'group by enemy_name order by kills desc, enemy_name desc;')
                    output = db_query(False, f'select enemy_name, character_name, kills from kill_counter '
                                             f'where kills > 10 and enemy_name like \'%{name}%\' '
                                             f'order by kills desc, character_name desc limit 10;')
                    if output:
                        outputString += f'**Top 10 Killers of Enemy Types matching `{name}`**:\n'
                    else:
                        outputString += f'No results.'
                else:
                    output = db_query(False, f'select enemy_name, character_name, max(kills) from kill_counter '
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
                output = db_query(False, f'select enemy_name, character_name, count(character_name) from wrapped '
                                         f'where character_name = \'{char_info.char_name}\' '
                                         f'group by enemy_name order by count(character_name) desc;')
                if output:
                    count = db_query(False, f'select count(character_name) from wrapped '
                                            f'where character_name = \'{char_info.char_name}\'')
                    count = sum(count, ())

                    ranking = db_query(False, f'select character_name, count(character_name) '
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
                output = db_query(False, f'select character_name, count(character_name) '
                                         f'from wrapped group by character_name order by count(character_name) desc limit 25;')
                if output:
                    outputString += f'**Outcast Overview: Top 25 Most Kills**\n\n'
                    for index, record in enumerate(output):
                        (character_name, kills) = record
                        outputString += f'{index + 1} - {character_name} - {kills}\n'

            case 'character':
                if name:
                    output = db_query(False, f'select enemy_name, character_name, count(character_name) from wrapped '
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
                            await ctx.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                        else:
                            await ctx.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                    else:
                        continue
            else:
                await ctx.send(str(outputString))

        return

    @commands.command(name='where', aliases=['location', 'loc', 'whereami'])
    async def where(self, ctx):
        """ - Checks where the bot thinks you're located

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'select x, y, z from online_character_info '
                    f'where char_id = {character.id} limit 1')
        results = cur.fetchone()

        con.commit()
        con.close()

        await ctx.reply(f'The bot sees your location as: '
                        f'`TeleportPlayer {results[0]} {results[1]} {results[2]}`')
        return

    @commands.command(name='journey', aliases=['fixjourney'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def journey(self, ctx, name: str):
        """- Fix a stuck journey step. Verify that they have completed the requirement before using.

        Parameters
        ----------
        ctx
        name
            Provide the full character name, using quotes if there are spaces.

        Returns
        -------

        """
        message = await ctx.reply(f'Fixing current journey step for `{name}`...')

        character = get_single_registration(name)

        if not character:
            await message.edit(content=f'No character named `{name}` registered!')
            return
        else:
            (char_id, char_name, discord_id) = character

        rconCharId = get_rcon_id(char_name)
        if not rconCharId:
            await message.edit(content=f'Character {char_name} must be online to fix a journey step.')
            return

        rconCommand = f'con {rconCharId} JourneyCompleteStepForCurrent'
        rconResponse = runRcon(rconCommand)
        if rconResponse.error == 1:
            await message.edit(f'Authentication error on {rconCommand}')
            return
        else:
            await message.edit(content=f'Stuck Journey step for `{char_name}` has been completed.')

    @commands.command(name='thralldeath')
    @commands.has_any_role('Admin', 'Moderator')
    async def thralldeath(self, ctx, owner: str):
        """

        Parameters
        ----------
        ctx
        owner
            Partial clan name or solo player name

        Returns
        -------

        """
        outputString = ''

        response = runRcon(f'sql select distinct datetime(worldTime,\'unixepoch\'), '
                           f'\'TeleportPlayer \' || x || \' \' || y || \' \' || z as Coordinates, objectName, objectId, '
                           f'ownerId, ownerName, ownerGuildId, ownerGuildName from game_events where '
                           f'worldTime >= 1729166400 and eventType = 86 and objectId <> 0 '
                           f'and length(argsMap) = 4 and ( z > 1000000000 or z < -500000 )'
                           f'and ownerGuildName like \'%{owner}%\' group by objectId order by worldTime desc;')
        response.output.pop(0)
        if response.output:
            for record in response.output:
                outputString += f'{record}\n'
            await ctx.reply(f'{outputString}')
        else:
            await ctx.reply(f'No under-mesh thrall deaths found matching `{owner}`')

    @commands.command(name='test1')
    @commands.has_any_role('Admin', 'Moderator')
    async def test1(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        pull_online_character_info_new()
        return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Utilities(bot))
