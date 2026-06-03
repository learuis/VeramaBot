import io
import re
import time
import sqlite3
import os
import inspect
import platform
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

import discord.ext.commands
from discord.ext import commands
from matplotlib.pyplot import legend

from cogs.InnSystem import Character
from functions.externalConnections import runRcon, downloadSave, db_query, rcon_all, send_rcon_command
from functions.common import custom_cooldown, is_registered, get_rcon_id, get_single_registration, \
    get_bot_config, set_bot_config, add_bot_config, int_epoch_time, no_registered_char_reply, \
    run_console_command_by_name, flatten_list, check_channel, Registration
from datetime import datetime
from datetime import timezone
from time import strftime, localtime
from rcon.util import remove_formatting_codes
from rcon import Console

from dotenv import load_dotenv

load_dotenv('data/server.env')
VETERAN_ROLE = int(os.getenv('VETERAN_ROLE'))
RCON_HOST = os.getenv('RCON_HOST')
RCON_PORT = int(os.getenv('RCON_PORT'))
RCON_PASS = str(os.getenv('RCON_PASS'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))
GUILD_ID = int(os.getenv('GUILD_ID'))

class LogServerStats:
    def __init__(self):
        self.uptime = []
        self.mem1 = []
        self.mem2 = []
        self.mem3 = []
        self.mem4 = []
        self.cpu1 = []
        self.cpu2 = []
        self.players = []
        self.frametime_best = []
        self.frametime_avg = []
        self.frametime_worst = []
        self.npc_ailod1 = []
        self.npc_ailod2 = []
        self.npc_ailod3 = []
        self.npc_ailod4 = []
        self.b_ailod1 = []
        self.b_ailod2 = []
        self.b_ailod3 = []
        self.b_ailod4 = []
        self.p_ailod1 = []
        self.p_ailod2 = []
        self.p_ailod3 = []
        self.p_ailod4 = []
        self.sfps_avg = []
        self.startup_offset = 0

def get_population():

    timeOfRecording = []
    population = []

    DB_LOCATION = os.getenv('DB_LOCATION')
    DB_FILE = os.getenv('DB_FILE')
    db_path = f'{DB_LOCATION}/{DB_FILE}'
    connection = sqlite3.connect(f'{db_path}')

    cursor = connection.cursor()

    cursor.execute(f'SELECT * from serverPopulationRecordings order by timeofRecording asc')

    rows = cursor.fetchall()
    connection.close()

    for row in rows:
        timeOfRecording.append(datetime.fromtimestamp(row[0]))
        # timeOfRecording.append(int(row[0]))
        population.append(float(row[1])*40)


    print(timeOfRecording)
    print(population)

    plt.plot(timeOfRecording, population, label='Population', color='blue', marker='o', markersize=1)

    ax = plt.gca()
    y_max = 40
    x_max = datetime.fromtimestamp(int_epoch_time()).day
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=4)
    ax.y_lim = (0, y_max)
    ax.x_lim = (timeOfRecording[0], x_max)
    ax.set_yticks(range(0, y_max + 1))
    # ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    ax.set_xlabel('Time')
    ax.set_ylabel('Players')
    ax.grid(visible=True, axis='y', which='major', color='gray', linestyle='--', alpha=0.5)
    plt.title('Population Recordings')
    plt.legend(bbox_to_anchor=(1.32, 1), loc='upper right')
    # plt.legend()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=720, bbox_inches='tight')
    buffer.seek(0)
    file = discord.File(buffer, filename='population.png')

    plt.close()

    return file

def parse_log_server_stats(option):
    stat_list = []
    players_series = []
    sfps_series = []
    uptime_series = []
    purge_start_times = []
    purge_end_times = []
    last_restart = 0

    lss = LogServerStats()

    first = True

    DB_LOCATION = os.getenv('DB_LOCATION')
    DB_FILE = os.getenv('DB_FILE')
    log_path = f'{DB_LOCATION}/Logs'
    db_path = f'{DB_LOCATION}/{DB_FILE}'

    log_path = os.path.abspath(log_path)
    db_path = os.path.abspath(db_path)

    if option:
        filename = option
    else:
        filename = 'ConanSandbox'

    system_os = platform.system()
    print(system_os)

    if system_os == 'Windows':
        find_command = 'findstr /l /c:'
        cd_command = 'cd /d'
    else:
        find_command = 'grep'
        cd_command = 'cd'

    os.system(f'{cd_command} {log_path} && {find_command} "LogServerStats" {filename}.log > raw_stats.txt')

    with io.open(f'{log_path}//raw_stats.txt', mode='r') as log:
        for line in log:
            # print(f'starting line in log loop')
            # print(line)
            # if re.search('ServerStatReporter', line):
            if 'ServerStatReporter' in line:
                # skip initial line
                # print(f'initial line')
                continue
            elif 'StartupTime' in line:
                # get startup offset
                # print(f'startup line')
                lss.startup_offset = int(re.search('StartupTime=(\\d+)', line).group(1))
                # print(lss.startup_offset)
                continue
            elif 'Uptime' in line:
                # print('uptime line')
                match = re.findall('Uptime=(\\d*)\\s'
                                   'Mem=(\\d*):(\\d*):(\\d*):(\\d*)\\s'
                                   'CPU=(\\d+\\.\\d+):(\\d+\\.\\d+)\\s'
                                   'Players=(\\d+)\\s'
                                   'FPS=(\\d+\\.\\d+):(\\d+\\.\\d+):(\\d+\\.\\d+)\\s'
                                   'NPC_AILOD=(\\d+):(\\d+):(\\d+):(\\d+)\\s'
                                   'B_AILOD=(\\d+):(\\d+):(\\d+):(\\d+)\\s'
                                   'P_AILOD=(\\d+):(\\d+):(\\d+):(\\d+)', line)
                stat_list.extend(match)
        # print(stat_list)
        for stat in stat_list:
            # print(stat)
            target_lists = [lss.cpu1, lss.cpu2,
             lss.players, lss.frametime_best, lss.frametime_avg, lss.frametime_worst,
             lss.npc_ailod1, lss.npc_ailod2, lss.npc_ailod3, lss.npc_ailod4,
             lss.b_ailod1, lss.b_ailod2, lss.b_ailod3, lss.b_ailod4,
             lss.p_ailod1, lss.p_ailod2, lss.p_ailod3, lss.p_ailod4]

            # print(stat[0])
            lss.uptime.append(int(stat[0])/60)
            lss.mem1.append(float(stat[1]) / 1073741824)
            lss.mem2.append(float(stat[2]) / 1073741824)
            lss.mem3.append(float(stat[3]) / 1073741824)
            lss.mem4.append(float(stat[4]) / 1073741824)
            lss.sfps_avg.append(1000/float(stat[9]))

            for x in range(5, len(stat)):
                target_lists[x-5].append(float(stat[x]))

            # for values, sublist in zip(values, target_lists):
            #     sublist.append(values)

        # print([lss.uptime], [lss.mem1], [lss.mem2], [lss.mem3], [lss.mem4], [lss.cpu1], [lss.cpu2],
        #      [lss.players], [lss.frametime_best], [lss.frametime_avg], [lss.frametime_worst],
        #      [lss.npc_ailod1], [lss.npc_ailod2], [lss.npc_ailod3], [lss.npc_ailod4],
        #      [lss.b_ailod1], [lss.b_ailod2], [lss.b_ailod3], [lss.b_ailod4],
        #      [lss.p_ailod1], [lss.p_ailod2], [lss.p_ailod3], [lss.p_ailod4])

        # uptime_series.append(int(int(stat[0])/60))
        # players_series.append(int(stat[7]))
        # sfps_series.append(sfps)

    connection = sqlite3.connect(f'{db_path}')

    cursor = connection.cursor()
    if option:
        cursor.execute(f'SELECT worldTime, eventType from game_events where eventType in (0,118,119,120) '
                       f'and worldTime >= ( select min(worldTime) from ( select worldTime from game_events where eventType = 0 order by worldTime desc limit 2 ) ) '
                       f'and worldTime < ( select max(worldTime) from game_events where eventType = 0 ) '
                       f'order by worldTime asc')
    else:
        cursor.execute(f'SELECT worldTime, eventType from game_events where eventType in (0,118,119,120) '
                       f'and worldTime >= ( select worldTime from game_events where eventType = 0 order by worldTime desc limit 1 ) '
                       f'order by worldTime asc')
    rows = cursor.fetchall()
    connection.close()

    if rows:
        for row in rows:
            match row[1]:
                case 0:
                    # print(row[0])
                    last_restart = int(row[0])
                case 118:
                    # print(row[0])
                    purge_start_time = (int(row[0]) - last_restart - lss.startup_offset) / 60
                    # print(purge_start_time)
                    purge_start_times.append(purge_start_time)
                case 119 | 120:
                    # print(row[0])
                    purge_end_time = (int(row[0]) - last_restart - lss.startup_offset) / 60
                    # print(purge_end_time)
                    purge_end_times.append(purge_end_time)


        # print(purge_start_times)
        # print(purge_end_times)

    return lss, purge_start_times, purge_end_times


def draw_performance_chart(lss, purge_start_times, purge_end_times):

    plt.plot(lss.uptime, lss.players, label='Players', color='blue', marker='o', markersize=1)
    plt.plot(lss.uptime, lss.sfps_avg, label='SFPS', color='orange', marker='o', markersize=1)
    plt.plot(lss.uptime, lss.mem3, label='Memory (GB)', color='purple', marker='o', markersize=1)

    if purge_start_times:
        for index, start_time in enumerate(purge_start_times):
            if index == 0:
                label = 'Purge Start'
            else:
                label = '_nolegend_'
            plt.axvline(x=start_time, color='red', linestyle='--', label=label)
    if purge_end_times:
        for index, end_time in enumerate(purge_end_times):
            if index == 0:
                label = 'Purge End'
            else:
                label = '_nolegend_'
            plt.axvline(x=end_time, color='black', linestyle='--', label=label)

    ax = plt.gca()
    y_max = int(round(max(max(lss.players),max(lss.sfps_avg)),0))
    x_max = int(max(lss.uptime))
    ax.tick_params(axis='y', labelsize=7)
    ax.tick_params(axis='x', labelsize=7)
    ax.y_lim = (0, y_max)
    ax.x_lim = (0, x_max)
    ax.set_yticks(range(0, y_max + 1))
    # ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
    ax.xaxis.set_major_locator(plt.MaxNLocator(10))
    ax.set_xlabel('Uptime (minutes)')
    ax.set_ylabel('Value')
    ax.grid(visible=True, axis='y', which='major', color='gray', linestyle='--', alpha=0.5)
    plt.title('Players:SFPS')
    plt.legend(bbox_to_anchor=(1.32, 1), loc='upper right')
    # plt.legend()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=720, bbox_inches='tight')
    buffer.seek(0)
    file = discord.File(buffer, filename='performance.png')

    plt.close()

    return file


class Admin(commands.Cog):
    """Cog class containing commands related to server status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class RconFlags(commands.FlagConverter):
        command: str

    @commands.command(name='command_sync')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    async def command_sync(self, ctx):
        await self.bot.tree.sync()
        await ctx.reply(f'Command sync completed.')
        return


    @commands.command(name='restart')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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

    @commands.command(name='help_test')
    @commands.is_owner()
    @commands.check(check_channel)
    async def help_test(self, ctx, command_name: str):
        output = ''
        title = ''

        for cog in self.bot.cogs:
            command_list = self.bot.get_cog(cog).get_commands()
            for command in command_list:
                if command_name.lower() == command.name.lower():
                    title = f'**{command.name.lower()}**'
                    output += f'{command.description}\n'
                    signature = inspect.signature(self.bot.get_command(command.name).callback)
                    docstring = self.bot.get_command(command.name).callback.__doc__
                    output += f'{docstring}\n'
                    # for name, parameter in signature.parameters.items():
                    #     if parameter.name == 'self' or parameter.name == 'ctx':
                    #         continue
                    #     output += f'{parameter.name}\n{parameter}'
                    # for key in parameter_dict:
                    #     output+= f'**{key}**\n{parameter_dict.get(key)}\n'
                # output += self.bot.get_command(command.name).help

        embed = discord.Embed(title=f'{title}',
                              description=f'{output}',
                              colour=0x00b0f4)
        await ctx.reply(embed=embed)
        return

    @commands.command(name='status_prepare')
    @commands.is_owner()
    @commands.check(check_channel)
    async def status_prepare(self, ctx: commands.Context):
        await ctx.send(f'This message will be updated with status information!')

    @commands.command(name='rcon')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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
            # print(f'{arg}')
            command += f'{arg} '

        command = re.sub(';', '\'', command)

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
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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

    @commands.command(name='welcome')
    @commands.has_any_role('Moderator', 'Helper', 'Admin')
    @commands.check(check_channel)
    async def welcome(self, ctx, char_name: str):
        """ - Sends a welcome message to a new player

        Parameters
        ----------
        ctx
        char_name
            Character name. Use double quotes if there are spaces

        Returns
        -------

        """
        rconCharId = get_rcon_id(char_name)
        if rconCharId:
            runRcon(f'con {rconCharId} testfifo 7 Welcome Rules and Gear at G3/G4')
            await ctx.send(f'Sent a welcome message to `{char_name}`!')
            return
        else:
            await ctx.send(f'No character named {char_name} is online!')
            return




    @commands.command(name='veteran2')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def veteran2(self, ctx):
        """
        Adds the Veteran Outcast role to everyone who registered in the previous season

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        vet_role = ctx.author.guild.get_role(VETERAN_ROLE)

        user_list = db_query(False, f'select discord_user from registration '
                                    f'where season = {PREVIOUS_SEASON}')

        users = list(sum(user_list, ()))
        new_vets = f''

        for user in users:
            #print(f'{user}')
            try:
                member = await ctx.author.guild.fetch_member(user)
            except discord.errors.NotFound:
                continue
            if member.get_role(VETERAN_ROLE):
                #print(f'{member.name} already is a veteran')
                continue
            else:
                print(f'{member.name} is not a veteran')
                new_vets += f'{member.name} '
                await member.add_roles(vet_role)
                continue

            await ctx.reply(f'New Veterans: {new_vets}')
        return

    @commands.command(name='veteran', aliases=['vet', 'vets'])
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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
        # print(0)
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
                # print(splitOutput)
                if len(str(splitOutput)) > 1800:
                    await ctx.send(splitOutput)
                    splitOutput = ''
            await ctx.send(str(splitOutput))
        else:
            await ctx.send(outputString)

    @commands.command(name='maintenance')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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

    @commands.command(name='getconfig')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def getConfig(self, ctx, item: str):
        """

        Parameters
        ----------
        ctx
        item

        Returns
        -------

        """

        value = get_bot_config(f'{item.casefold()}')

        await ctx.send(f'Current: {item.casefold()} = {value}')

    @commands.command(name='setconfig')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def setConfig(self, ctx, item: str, value: str):
        """

        Parameters
        ----------
        ctx
        item
        value

        Returns
        -------

        """

        if get_bot_config(item.casefold()):
            set_bot_config(item.casefold(), value.casefold())
        else:
            add_bot_config(item.casefold(), value.casefold())

        await ctx.send(f'Set {item.casefold()} = {value.casefold()}')

    @commands.command(name='charswap')
    @commands.has_any_role('Admin', 'Moderator', 'BuildHelper')
    @commands.check(check_channel)
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

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
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

            # print(f'{res[0]} {res[1]} {res[2]} {res[3]} {res[4]} {res[5]} {res[6]} {res[7]} {res[8]}')

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
                    response = runRcon(f'sql update account set user = \'{int_epoch_time()}\' where id = {main_acct_id}')
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

                    # response = runRcon(f'sql update account set user = \'{alt_acct_user}\' where id = {main_acct_id}')
                    # if response.error == 1:
                    #     outputString += f'\nRCON command error.'
                    #     await message.edit(content=outputString)
                    #     return
                    # else:
                    #     outputString += f'\n{response.output}'
                    #     await message.edit(content=outputString)

                    outputString += (f'\nCharacter swap from main `{main_char_name}` to alt `{alt_char_name}` '
                                     f'is complete')
                    await message.edit(content=outputString)
                    return

                case 'main':
                    response = runRcon(f'sql update account set user = \'{int_epoch_time()}\' where id = {alt_acct_id}')
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

                    # response = runRcon(f'sql update account set user = \'{alt_acct_user}\' where id = {alt_acct_id}')
                    # if response.error == 1:
                    #     outputString += f'\nRCON command error.'
                    #     await message.edit(content=outputString)
                    #     return
                    # else:
                    #     outputString += f'\n{response.output}'
                    #     await message.edit(content=outputString)

                    outputString += (f'\nCharacter swap from alt `{alt_char_name}` to main `{main_char_name}` '
                                     f'is complete')
                    await message.edit(content=outputString)
                    return


    @commands.command(name='buildeverywhere')
    @commands.has_any_role('BuildHelper')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def buildeverywhere(self, ctx):
        """ Enables build anywhere.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        # print(f'{character}')

        alt_char_name = db_query(False, f'select alt_char_name from char_swap '
                                        f'where main_char_id = \'{character.id}\' limit 1')
        alt_char_name = flatten_list(alt_char_name)
        # print(f'{alt_char_name}')
        check = run_console_command_by_name(f'{alt_char_name[0]}', f'PlayerCanBuildEverywhere {alt_char_name[0]}')
        if not check:
            await ctx.reply(f'Character `{alt_char_name[0]}` is not online.')
            return
        check = run_console_command_by_name(f'{alt_char_name[0]}', f'CreativeMode')
        if not check:
            await ctx.reply(f'Character `{alt_char_name[0]}` is not online.')
            return

        await  ctx.reply(f'Character `{alt_char_name[0]}` has been put into '
                         f'Creative Mode and has PlayerCanBuildEverywhere enabled.')
        return

    @commands.command(name='dbquery', aliases=['db', 'query'])
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def dbQuery(self, ctx, commit_query: bool, query: str):
        """

        Parameters
        ----------
        ctx
        commit_query
        query

        Returns
        -------

        """
        if commit_query:
            results = db_query(True, f'{query}')
            if results:
                await ctx.send(f'Executed query: {query}')
                return
            return

        results = db_query(False, f'{query}')
        if results:
            for result in results:
                await ctx.send(f'{result}\n')
            return
        else:
            await ctx.send(f'Query returned no rows.')
            return


    @commands.command(name='volcano', aliases=['drop', 'getrekt'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
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
        reg = get_single_registration(name)
        character = Registration()

        if not reg:
            await ctx.reply(f'No character named `{name}` registered!')
            return
        else:
            character.id = reg[0]
            character.name = reg[1]
            character.discord_id = reg[2]

        backup_target = is_registered(ctx.author.id)

        destination = f'TeleportPlayer -17174.951172 -259672.125 87383.28125'

        rconCharId = get_rcon_id(character.name)
        if not rconCharId:
            await ctx.reply(f'Character `{character.name}` must be online to throw into the Volcano!')
            return
        else:
            if 'Verama' in name.lower():
                rconCharId2 = get_rcon_id(backup_target.char_name)
                if not rconCharId2:
                    await ctx.reply(f'Volcano-ing while offline? Naughty!')
                    return
                run_console_command_by_name(backup_target.char_name, destination)
                await ctx.reply(f'Tossed `{backup_target.char_name}` into the Volcano. LOL')
                return
            else:
                run_console_command_by_name(character.name, destination)
                await ctx.reply(f'Tossed `{character.name}` into the Volcano.')
                return

    @commands.command(name='shame', aliases=['prison', 'capture', 'jail'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def shame(self, ctx, name: str):
        """- Sends the named player to jail

        Parameters
        ----------
        ctx
        name
            Player name, use double quotes with there are spaces

        Returns
        -------

        """
        rconCharId = get_rcon_id(name)
        if not rconCharId:
            await ctx.reply(f'Character `{name}` must be online to send to jail!')
            return
        else:
            run_console_command_by_name(name, f'TeleportPlayer 319908.40625 -63563.578125 -5586.727539')
            await ctx.reply(f'Sent `{name}` to the shame chamber.')
            return

    @commands.command(name='offlineroom')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def jail(self, ctx, char_id: int = 0, target: str = None, x: str  = 0, y: str = 0, z: str = 0):
        """- Moves an offline character to the chamber of offline notifications

        Parameters
        ----------
        ctx
        char_id
            Character ID to move. Check with v/idlookup
        target
            Which room to send them to. namechange | theft | custom
        x
        y
        z


        Returns
        -------

        """
        try:
            float(x)
            float(y)
            float(z)
        except ValueError:
            await ctx.reply(f'Coordinates must be numbers.')
            return
        if char_id == 0:
            await ctx.reply(f'Must provide a valid character ID.')
            return
        if not target:
            await ctx.reply(f'Must provide a valid target room, `namechange` or `theft`')
            return
        match target.lower():
            case 'namechange':
                x = 271509.5625
                y = -110983.726563
                z = -9680.095703
            case 'theft':
                x = 272334.5
                y = -111998.367188
                z = -9549.048828
            case 'custom':
                pass
            case _:
                await ctx.reply(f'Must provide a valid target room, `namechange` | `theft` | `custom`')
                return

        runRcon(f'sql update actor_position set x = {x}, y = {y}, z = {z} where id = {char_id}')
        await ctx.reply(f'Moved `{char_id}` to `{target}` chamber.')
        return


    @commands.command(name='rcon_all')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def rcon_all(self, ctx, command: str):
        """
        - Sends an alert to all online players

        Parameters
        ----------
        ctx
        command

        Returns
        -------

        """
        try:
            str(command)
        except TypeError:
            await ctx.send(f'Command formatted incorrectly.')
        rcon_all(command)

    @commands.command(name='lastonline')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def lastonline(self, ctx, char_name:str):
        """- Checks when a player was last online.

        Parameters
        ----------
        ctx
        char_name

        Returns
        -------

        """
        outputString = ''
        last_time_online = ''

        response = runRcon(f'sql select lastTimeOnline from characters where char_name like \'{char_name}\' limit 1')
        if response.output:
            response.output.pop(0)

            for record in response.output:
                match = re.findall(r'\s+\d+ | [^|]*', record)
                last_time_online = ''.join(str(timestamp) for timestamp in match)
        else:
            outputString = f'Character `{char_name}` could not be found.\n'
            await ctx.reply(content=outputString)

        # last_time_online = strftime('%Y-%m-%d %H:%M:%S %Z', localtime(int(last_time_online)))
        if response.error == 1:
            outputString += f'\n\nRCON Error.'
            await ctx.reply(content=outputString)
            return
        else:
            outputString = f'Character `{char_name}` was last online at: <t:{last_time_online.strip()}:f>\n'
            await ctx.reply(content=outputString)

            return

    @commands.command(name='rcontest')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def rcontest(self, ctx, *args):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        command = ''
        formattedOutput = ''

        for arg in args:
            print(f'{arg}')
            command += f'{arg} '

        command = re.sub(';', '\"', command)

        # rconResponse = send_rcon_command(command)
        class RconResponse:
            def __init__(self):
                self.output = []
                self.error = 0

            def __bool__(self):
                return self.output != []

        returnValue = RconResponse()

        commandOutput = []
        connection_failures = 0
        command_failures = 0

        while connection_failures < 6:
            try:
                # print(f'{RCON_HOST}:{RCON_PORT}')
                console = Console(host='172.31.240.1', port=int(RCON_PORT), password=RCON_PASS)
                break
            except Exception:
                connection_failures += 1

        if connection_failures == 6:
            returnValue.output = ['Authentication failed 5 times in a row.']
            returnValue.error = 1
            return returnValue

        while command_failures < 6:
            try:
                res_body = console.command(command)
                break
            except Exception:
                command_failures += 1
                print(f'RCON Failure #{command_failures}')

        if command_failures == 6:
            returnValue.output = ['Received few bytes exception 5x in a row']
            returnValue.error = 1
            return returnValue

        console.close()

        res_body = remove_formatting_codes(res_body)

        if not res_body.endswith('\n'):
            res_body += '\n'

        res_list = res_body.splitlines()

        for x in res_list:
            commandOutput.append(x)

        returnValue.output = commandOutput

        await ctx.reply(f'{returnValue.output}')
        return False

    @commands.command(name='performance', aliases=['perf','sfps','fps'])
    @commands.has_any_role('Admin', 'Moderator')
    async def performance(self, ctx, option: str = None):
        """

        Parameters
        ----------
        ctx
        option
            Filename

        Returns
        -------

        """

        lss, purge_start_times, purge_end_times = parse_log_server_stats(option)
        if not lss:
            await ctx.reply('No data returned.')
            return
        # print(players_series)
        # print(sfps_series)
        # print(uptime_series)
        # print(uptime_series[-1])

        file = draw_performance_chart(lss, purge_start_times, purge_end_times)
        await ctx.reply(f'Performance Graph has been generated.', file=file)

    @commands.command(name='population', aliases=['pop'])
    @commands.has_any_role('Admin', 'Moderator')
    async def population(self, ctx, option: str = None):
        """

        Parameters
        ----------
        ctx
        option
            Filename

        Returns
        -------

        """
        file = get_population()
        await ctx.reply(f'Population Graph has been generated.', file=file)
        return

async def setup(bot):
    await bot.add_cog(Admin(bot))
