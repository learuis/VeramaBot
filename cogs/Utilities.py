import math
import sqlite3
import re
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from cogs.QuestSystem import pull_online_character_info_new
from functions.common import custom_cooldown, ununicode, is_registered, get_single_registration, get_rcon_id, \
    flatten_list, get_bot_config, check_channel, no_registered_char_reply, get_clan

from functions.externalConnections import db_query, runRcon

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
SUPPORT_CHANNEL = int(os.getenv('SUPPORT_CHANNEL'))

async def is_character_online(channel):
    connected_chars = []
    outputlist = ''
    name = str(get_bot_config(f'online_alert'))
    mention = str(get_bot_config(f'online_alert_tag'))

    rconResponse = runRcon('listplayers')
    rconResponse.output.pop(0)

    for x in rconResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', x)
        connected_chars.append(match)
        # print(connected_chars)

    if not connected_chars:
        # no one is online
        return False

    for x in connected_chars:
        if name:
            if name.casefold() in x[1].casefold():
                await channel.send(f'<@{mention}> `{x[1].strip()}` is online with rcon ID `{x[0].strip()}`.')
                return True
    return False


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

    @commands.command(name='barkeeper')
    @commands.has_any_role('Moderator')
    async def barkeeper(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        # query = (f'sql select \'TeleportPlayerExact \' || ap.x || \' \' || ap.y || \' \' || ap.z as TP '
        #          f'from actor_position ap where ap.class like \'%barkeeper%\' '
        #          f'and ( ( (x + 72484) * (x + 72484) + (y + 48923) * (y + 48923) ) <= 4000000) '
        #          f'or ( (x + 225023) * (x + 225023) + (y + 107668) * (y + 107668) ) <= 4000000 '
        #          f'or ( (x - 79674 ) * (x - 79674 ) + (y - 97265 ) * (y - 97265 ) ) <= 4000000 '
        #          f'or ( (x + 97817) * (x + 97817) + (y - 16127) * (y - 16127) ) <= 4000000 '
        #          f'or ( (x - 19780) * (x - 19780 ) + (y - 167375 ) * (y - 167375 ) ) <= 4000000 '
        #          f'or ( (x - (-74956) ) * (x - (-74956) ) + (y - (209237) ) * (y - (209237) ) ) <= 4000000 '
        #          f'or ( (x - (-41916) ) * (x - (-41916) ) + (y - (163761) ) * (y - (163761) ) ) <= 4000000 '
        #          f'or ( (x - (70979) ) * (x - (70979) ) + (y - (234910) ) * (y - (234910) ) ) <= 4000000 '
        #          f'or ( (x - (15517) ) * (x - (15517) ) + (y - (121419) ) * (y - (121419) ) ) <= 4000000 '
        #          f'or ( (x - (81180) ) * (x - (81180) ) + (y - (172818) ) * (y - (172818) ) ) <= 4000000 '
        #          f'or ( (x - (15730) ) * (x - (15730) ) + (y - (161356) ) * (y - (161356) ) ) <= 4000000 '
        #          f'or ( (x - (-100212) ) * (x - (-100212) ) + (y - (24473) ) * (y - (24473) ) ) <= 4000000 '
        #          f'or ( (x - (-14660) ) * (x - (-14660) ) + (y - (54857) ) * (y - (54857) ) ) <= 4000000 '
        #          f'or ( (x - (-2590) ) * (x - (-2590) ) + (y - (94356) ) * (y - (94356) ) ) <= 4000000 '
        #          f'or ( (x - (92860) ) * (x - (92860) ) + (y - (96662) ) * (y - (96662) ) ) <= 4000000 '
        #          f'or ( (x - (92623) ) * (x - (92623) ) + (y - (140533) ) * (y - (140533) ) ) <= 4000000 '
        #          f'or ( (x - (64504) ) * (x - (64504) ) + (y - (52837) ) * (y - (52837) ) ) <= 4000000 '
        #          f'or ( (x - (127985) ) * (x - (127985) ) + (y - (156375) ) * (y - (156375) ) ) <= 4000000 '
        #          f'or ( (x - (121219) ) * (x - (121219) ) + (y - (122648) ) * (y - (122648) ) ) <= 4000000 '
        #          f'or ( (x - (180477) ) * (x - (180477) ) + (y - (102628) ) * (y - (102628) ) ) <= 4000000 '
        #          f'or ( (x - (214243) ) * (x - (214243) ) + (y - (62534) ) * (y - (62534) ) ) <= 4000000 '
        #          f'or ( (x - (262755) ) * (x - (262755) ) + (y - (17598) ) * (y - (17598) ) ) <= 4000000 '
        #          f'or ( (x - (316207) ) * (x - (316207) ) + (y - (72432) ) * (y - (72432) ) ) <= 4000000 '
        #          f'or ( (x - (-75306) ) * (x - (-75306) ) + (y - (-45341) ) * (y - (-45341) ) ) <= 4000000 '
        #          f'or ( (x - (-162692) ) * (x - (-162692) ) + (y - (-47910) ) * (y - (-47910) ) ) <= 4000000 '
        #          f'or ( (x - (-25704) ) * (x - (-25704) ) + (y - (-3144) ) * (y - (-3144) ) ) <= 4000000 '
        #          f'or ( (x - (-53386) ) * (x - (-53386) ) + (y - (-17478) ) * (y - (-17478) ) ) <= 4000000 '
        #          f'or ( (x - (-28271) ) * (x - (-28271) ) + (y - (-52575) ) * (y - (-52575) ) ) <= 4000000 '
        #          f'or ( (x - (-218999) ) * (x - (-218999) ) + (y - (-114313) ) * (y - (-114313) ) ) <= 4000000 '
        #          f'or ( (x - (-196341) ) * (x - (-196341) ) + (y - (-124761) ) * (y - (-124761) ) ) <= 4000000 )')

        output_string = '__Found Barkeepers__\n'
        barkeeper_list = []
        query = (f'sql select \'TeleportPlayerExact \' || ap.x || \' \' || ap.y || \' \' || ap.z as TP '
                 f'from actor_position ap where ap.class like \'%barkeeper%\' '
                 f'and ( ( (x + 72484) * (x + 72484) + (y + 48923) * (y + 48923) ) <= 4000000 '
                 f'or ( (x + 225023) * (x + 225023) + (y + 107668) * (y + 107668) ) <= 4000000 '
                 f'or ( (x - 79674 ) * (x - 79674 ) + (y - 97265 ) * (y - 97265 ) ) <= 4000000 '
                 f'or ( (x + 97817) * (x + 97817) + (y - 16127) * (y - 16127) ) <= 4000000 '
                 f'or ( (x - 19780) * (x - 19780 ) + (y - 167375 ) * (y - 167375 ) ) <= 4000000 '
                 f'or ( (x - (-74956) ) * (x - (-74956) ) + (y - (209237) ) * (y - (209237) ) ) <= 4000000 '
                 f'or ( (x - (-41916) ) * (x - (-41916) ) + (y - (163761) ) * (y - (163761) ) ) <= 4000000 '
                 f'or ( (x - (70979) ) * (x - (70979) ) + (y - (234910) ) * (y - (234910) ) ) <= 4000000 '
                 f'or ( (x - (15517) ) * (x - (15517) ) + (y - (121419) ) * (y - (121419) ) ) <= 4000000 '
                 f'or ( (x - (81180) ) * (x - (81180) ) + (y - (172818) ) * (y - (172818) ) ) <= 4000000 '
                 f'or ( (x - (15730) ) * (x - (15730) ) + (y - (161356) ) * (y - (161356) ) ) <= 4000000 '
                 f'or ( (x - (-100212) ) * (x - (-100212) ) + (y - (24473) ) * (y - (24473) ) ) <= 4000000 '
                 f'or ( (x - (-14660) ) * (x - (-14660) ) + (y - (54857) ) * (y - (54857) ) ) <= 4000000 '
                 f'or ( (x - (-2590) ) * (x - (-2590) ) + (y - (94356) ) * (y - (94356) ) ) <= 4000000 '
                 f'or ( (x - (92860) ) * (x - (92860) ) + (y - (96662) ) * (y - (96662) ) ) <= 4000000 '
                 f'or ( (x - (92623) ) * (x - (92623) ) + (y - (140533) ) * (y - (140533) ) ) <= 4000000 '
                 f'or ( (x - (64504) ) * (x - (64504) ) + (y - (52837) ) * (y - (52837) ) ) <= 4000000 '
                 f'or ( (x - (127985) ) * (x - (127985) ) + (y - (156375) ) * (y - (156375) ) ) <= 4000000 '
                 f'or ( (x - (121219) ) * (x - (121219) ) + (y - (122648) ) * (y - (122648) ) ) <= 4000000 '
                 f'or ( (x - (180477) ) * (x - (180477) ) + (y - (102628) ) * (y - (102628) ) ) <= 4000000 '
                 f'or ( (x - (214243) ) * (x - (214243) ) + (y - (62534) ) * (y - (62534) ) ) <= 4000000 '
                 f'or ( (x - (262755) ) * (x - (262755) ) + (y - (17598) ) * (y - (17598) ) ) <= 4000000 '
                 f'or ( (x - (316207) ) * (x - (316207) ) + (y - (72432) ) * (y - (72432) ) ) <= 4000000 '
                 f'or ( (x - (-75306) ) * (x - (-75306) ) + (y - (-45341) ) * (y - (-45341) ) ) <= 4000000 '
                 f'or ( (x - (-162692) ) * (x - (-162692) ) + (y - (-47910) ) * (y - (-47910) ) ) <= 4000000 '
                 f'or ( (x - (-25704) ) * (x - (-25704) ) + (y - (-3144) ) * (y - (-3144) ) ) <= 4000000 '
                 f'or ( (x - (-53386) ) * (x - (-53386) ) + (y - (-17478) ) * (y - (-17478) ) ) <= 4000000 '
                 f'or ( (x - (-28271) ) * (x - (-28271) ) + (y - (-52575) ) * (y - (-52575) ) ) <= 4000000 '
                 f'or ( (x - (-218999) ) * (x - (-218999) ) + (y - (-114313) ) * (y - (-114313) ) ) <= 4000000 '
                 f'or ( (x - (-196341) ) * (x - (-196341) ) + (y - (-124761) ) * (y - (-124761) ) ) <= 4000000 )')
        results = runRcon(query)
        if results.output:
            results.output.pop(0)
            for x in results.output:
                match = re.search(r'\s+\d+ | [^|]*', x)
                barkeeper_list.append(match.group(0))
            for barkeeper in barkeeper_list:
                output_string += f'```{barkeeper.strip()}``` \n'
            await ctx.reply(f'{output_string}')
        else:
            await ctx.reply(f'No orphaned barkeepers.')

        return

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

    @commands.command(name='channeltest')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def channeltest(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        await ctx.reply(f'Good to go!')

    @commands.command(name='outcastoverview', aliases=['oo', 'overview'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
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
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
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
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
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

    @commands.command(name='locateobject', aliases=['lo', 'shrink'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def locateobject(self, ctx, target_object: str = None, size: float = 1.0):
        """ - Requests a size change of a nearby object

        Parameters
        ----------
        ctx
        object

        Returns
        -------

        """
        x_coord = 0
        y_coord = 0
        search_term = f''
        key_str = ''
        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        target_object = target_object.lower()

        valid_options = {'map': 'BP_PL_Maproom',
                         'maproom': 'BP_PL_Maproom',
                         'vault': 'BP_PL_Chest_Vault',
                         'stable': 'BP_PL_Crafting_Station_AnimalPen_Stables',
                         'bigpen': 'BP_PL_Crafting_Station_AnimalPen_Tier',
                         'smallpen': 'BP_PL_Crafting_Station_AnimalPen_Small',
                         'wheel': 'BP_PL_CraftingStation_WheelOfPain',
                         'plinth': 'BP_PL_Trophy_IronPlinth',
                         't2tannertable': 'BP_PL_WorkStation_Tanner_T2_C'}
        try:
            search_term = valid_options[target_object]
        except KeyError:
            for key in valid_options:
                key_str += f'{key}|'
            key_str = key_str[:-1]
            await ctx.reply(f'Invalid option. Use `v/lo {key_str}`')
            return

        try:
            float(size)
            if 0.3 <= size <= 1.5:
                size = round(size,2)
                pass
            else:
                await ctx.reply(f'Size must be a value between 0.3 and 1.5')
                return
        except ValueError:
            await ctx.reply(f'Size must be a value between 0.3 and 1.5')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'select x, y from online_character_info '
                    f'where char_id = {character.id} limit 1')
        results = cur.fetchone()

        con.commit()
        con.close()

        if results:
            x_coord, y_coord = results

        clan_id, clan_name = get_clan(character)
        if not clan_id:
            clan_id = character.id
            clan_name = character.char_name

        where_clause = f'where class like \'%{search_term}%\' and owner_id = {clan_id} '
        join_clause = f'left join buildings on actor_position.id = buildings.object_id '

        results = runRcon(f'sql select id, class, x, y, '
                          f'((x - {x_coord}) * (x - {x_coord})) + ((y - {y_coord}) * (y- {y_coord})) as distance from actor_position '
                          f'{join_clause}{where_clause}order by distance asc limit 1')
        # print(f'{results.output}')
        results.output.pop(0)
        if not results.output:
            await ctx.reply(f'No matching object found.')
            return
        for record in results.output:
            # match = re.search(r'#\d+\s+(\d+)\s+[|]\s+(.+)\s+[|]\s+(\d+.\d+)\s+[|]\s+(\d+.\d+)\s+[|]\s+(\d+.\d+)', record)
            match = re.search(r'\d+\s+(\d+)\s+[|]\s+([a-zA-Z0-9\/_\.]+)\s+[|]\s+([\-\.\d]+)\s+[|]\s+([\-\.\d]+)\s+[|]\s+([\-\.\d]+)',
                              record)
            print(f'{match.group(1)} {match.group(2)} {match.group(3)} {match.group(4)} {match.group(5)}')
            object_id, class_name, x_result, y_result, distance = match.groups()

        sizechange_price = get_bot_config(f'sizechange_price')

        await ctx.reply(f'The bot sees your location as: `{x_coord} {y_coord}`\n\n'
                        f'**Found object:**\nid: `{object_id}`\nclass: `{class_name}`\n'
                        f'x-coordinate: `{x_result}`\ny-coordinate: `{y_result}`\n'
                        f'owned by: `{clan_id}` Owner Name: `{clan_name}`\n\n'
                        f'If this is the object you want to resize, copy/paste the following template into  <#{SUPPORT_CHANNEL}> to request a size change:')
        await ctx.reply(f'```\n__Size Change Request__\nOwner: `{clan_id}` | `{character.char_name}` (`{clan_name}`)\nObject Type: `{class_name}`\n'
                        f'Object ID: `{object_id}`\nSize: `{size}`\n\n'
                        f'`update actor_position set sx = {size}, sy = {size}, sz = {size} where id in ({object_id});`\n'
                        f'`v/tx <@{character.discord_id}> SizeChange {sizechange_price}` ```')
        return

        await ctx.reply(f'The bot sees your location as: '
                        f'`TeleportPlayer {results[0]} {results[1]} {results[2]}`')
        return

    @commands.command(name='clearmyquests', aliases=['questclear', 'questfix'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def clearmyquests(self, ctx, confirm: str = 'False'):
        """- Erases your Liu Fei and Freya quest progress.

        Parameters
        ----------
        ctx
        confirm
            Type confirm to execute the command

        Returns
        -------

        """
        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will completely erase your quest progress for BOTH Liu Fei and Freya. '
                f'It cannot be restored by any means (even by Verama!) after being erased.'
                f'\n\nIf you are sure you want to proceed, use `v/clearmyquests confirm`')
            return

        message = await ctx.reply(f'Erasing Liu Fei and Freya quest progress for `{character.char_name}`...')

        if get_rcon_id(character.char_name):
            await message.edit(content=f'Character {character.char_name} must be offline to erase quest progress.')
            return

        rconCommand = (f'sql delete from properties '
                       f'where name like \'%BP_AC_PlayerQuestState_C.m_ActiveQuests%\' '
                       f'and object_id = {character.id}')

        rconResponse = runRcon(rconCommand)
        if rconResponse.error == 1:
            await message.edit(f'Authentication error on {rconCommand}')
            return
        else:
            await message.edit(content=f'Erased all Liu Fei and Freya quest progress for `{character.char_name}`')
            return

    @commands.command(name='journey', aliases=['fixjourney'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def journey(self, ctx, confirm: str = 'False'):
        """- Fix your stuck journey step. Please do not abuse this command!

        Parameters
        ----------
        ctx
        confirm
            Type confirm to execute the command

        Returns
        -------

        """

        character = is_registered(ctx.author.id)
        # character = get_single_registration(name)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will complete your current active journey step. Only use this command if you '
                f'have completed a journey step but the game did not recognize it. Common reasons for this '
                f'are group dungeon runs and thrall placement. Abuse of this command will result in '
                f'a trip to the volcano and loss of permission to use the command.'
                f'\n\nIf you are sure you want to proceed, use `v/journey confirm`')
            return

        message = await ctx.reply(f'Fixing current journey step for `{character.char_name}`...')

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await message.edit(content=f'Character {character.char_name} must be online to fix a journey step.')
            return

        rconCommand = f'con {rconCharId} JourneyCompleteStepForCurrent'
        rconResponse = runRcon(rconCommand)
        if rconResponse.error == 1:
            await message.edit(f'Authentication error on {rconCommand}')
            return
        else:
            await message.edit(content=f'Stuck Journey step for `{character.char_name}` has been completed.')
            return

    @commands.command(name='thralldeath')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
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

    @commands.command(name='adminlocateobject', aliases=['adminlo'])
    @commands.has_any_role('Moderator')
    @commands.check(check_channel)
    async def adminlocateobject(self, ctx, x_coord: str, y_coord: str, owner: int = None, search:str = '', pet = False):
        """

        Parameters
        ----------
        ctx
        x_coord
        y_coord
        owner
        search
        pet

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        if not owner:
            clan_id, clan_name = get_clan(character)
            if not clan_id:
                clan_id = character.id
        else:
            clan_id = owner
            clan_name = 'Manual'

        try:
            x = float(x_coord)
            y = float(y_coord)
            # size = float(desired_size)
        except ValueError:
            await ctx.reply(f'Coordinates must be numbers!')
            return

        if pet:
            where_clause = 'where class not like \'%player%\' '
            join_clause = ''
        else:
            if search:
                where_clause = f'where class like \'%{search}%\' and owner_id = {clan_id} '
                join_clause = f'left join buildings on actor_position.id = buildings.object_id '
            else:
                where_clause = f'where owner_id = {clan_id} '
                join_clause = f'left join buildings on actor_position.id = buildings.object_id '

        results = runRcon(f'sql select id, class, x, y, '
                          f'((x - {x}) * (x - {x})) + ((y - {y}) * (y- {y})) as distance from actor_position '
                          f'{join_clause}{where_clause}order by distance asc limit 1')
        # print(f'{results.output}')
        results.output.pop(0)
        if not results.output:
            await ctx.reply(f'No records found.')
            return
        for record in results.output:
            # match = re.search(r'#\d+\s+(\d+)\s+[|]\s+(.+)\s+[|]\s+(\d+.\d+)\s+[|]\s+(\d+.\d+)\s+[|]\s+(\d+.\d+)', record)
            match = re.search(r'\d+\s+(\d+)\s+[|]\s+([a-zA-Z0-9\/_\.]+)\s+[|]\s+([\-\.\d]+)\s+[|]\s+([\-\.\d]+)\s+[|]\s+([\-\.\d]+)',
                              record)
            print(f'{match.group(1)} {match.group(2)} {match.group(3)} {match.group(4)} {match.group(5)}')
            object_id, class_name, x_result, y_result, distance = match.groups()

        await ctx.reply(f'Found object:\nid: `{object_id}`\nclass: `{class_name}`\n'
                        f'x-coordinate: `{x_result}`\ny-coordinate: `{y_result}`\n'
                        f'distance: `{distance}`\nowned by: `{clan_id}` name: `{clan_name}`\n\n'
                        f'If this is correct, run the command again, adding `confirm`')
        return

    @commands.command(name='itemlookup')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def itemlookup(self, ctx, search_term: str, confirm: str = ''):
        """

        Parameters
        ----------
        ctx
        search_term
        confirm

        Returns
        -------

        """
        output_string = ''

        if len(search_term) < 4:
            if 'confirm' in confirm:
                pass
            else:
                await ctx.reply(f'This may return a lot of results, are you sure? add `confirm`')
                return

        query = f'select template_id, name from cust_item_xref where name like \'%{search_term}%\''
        output_list = db_query(False, f'{query}')
        print(output_list)
        if output_list:
            for item in output_list:
                output_string += f'`{item[0]}` `{item[1]}`\n'

            await ctx.reply(f'Found `{len(output_list)}` items matching `{search_term}`.\n{output_string}')
            return
        else:
            await ctx.reply(f'No results for `{search_term}` found.')
            return

    @commands.command(name='test1')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
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
