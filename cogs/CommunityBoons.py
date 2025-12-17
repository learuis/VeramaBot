import time
import sqlite3
import ast
import os
from datetime import datetime

import discord

from functions.common import isInt, percentage, get_single_registration, is_registered, \
    set_bot_config, get_bot_config, int_epoch_time, flatten_list, no_registered_char_reply, check_channel, update_boons
from functions.externalConnections import runRcon, db_query, multi_rcon

from discord.ext import commands

from functions.common import custom_cooldown

from dotenv import load_dotenv

load_dotenv('data/server.env')
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))

class CommunityBoons(commands.Cog):
    """Cog class containing commands related to server status.

    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='boondelete',
                      aliases=['logdel', 'boondel', 'delboon', 'delboons'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def deleteboonlog(self, ctx,
                            command: str = commands.parameter(default='error'),
                            target: int = commands.parameter(default=-1)):
        """- Deletes entries from the Boon logs

        Deletes selected entries from the Boon logs by record number, or the last entered record.

        Usage: v/boondelete record 34

        Parameters
        ----------
        self
        ctx
        command
            record | undo | last
        target
            Which record should be deleted

        Returns
        -------

        """

        def delboon(record_num):
            del_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
            del_cur = del_con.cursor()

            del_cur.execute(f'select * from boonlog where record_num = {record_num}')
            del_res = del_cur.fetchone()

            del_cur.execute(f'delete from boonlog where record_num = {record_num}')
            del_con.commit()

            return del_res

        try:
            isInt(target)
        except ValueError:
            await ctx.send(f'You must specify a record number to delete. Use `v/boonlog list`')
        else:
            pass

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        match command:
            case 'undo' | 'last':
                cur.execute(f'select max(record_num) from boonlog')
                res = cur.fetchone()

                target = int(res[0])
                res = delboon(target)
                await ctx.send(f'The following record was deleted: {res}')

            case 'record':
                if target == -1:
                    await ctx.send(f'You must specify a record number to delete. Use `v/boonlog list`')
                else:
                    res = delboon(target)
                    await ctx.send(f'The following record was deleted: {res}')

            case 'error':
                await ctx.send(f'You must specify a command. Use `v/help boondelete`')

    @commands.command(name='boonconsume',
                      aliases=['bcon', 'bconsume', 'booncon'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def boonconsume(self, ctx,
                          identifier: str):
        """- Consumes materials for boon activation

        Reduces the "remaining" value starting with the oldest records.

        If prep option is used, it prepares the boon activation command

        for all boon quotas that have been achieved.

        Parameters
        ----------
        ctx
        identifier
            <material> | prep

        Returns
        -------

        """

        updateList = []
        consumedMaterials = []

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        if identifier == 'prep':
            cur.execute(f'select b.item, sum(b.remaining), q.quantity from boonlog as b left join quotas as q '
                        f'on q.material = b.item group by b.item')
            res = cur.fetchall()

            outputString = f''

            for x in res:
                # print(x)
                if x[1] >= x[2]:
                    outputString += f'{x[0].casefold()} '

            outputString = outputString[:-1]

            await ctx.send(f'Prepared activation command: `v/boonset activate {outputString}`')
            return
        #add input checking for material type

        validMaterials = {'chitin', 'brimstone', 'resin', 'tar', 'twine', 'dung',
                          'compositeobsidian', 'crystal', 'kits', 'cochineal', 'blood', 'demonblood'}
        if identifier not in validMaterials:
            await ctx.send(f'Invalid item in material selection. Check your input!')
            return

        cur.execute(f'select * from boonlog where remaining > 0 and item like \'{identifier}\'')
        boonlog = cur.fetchall()

        cur.execute(f'select sum(remaining) from boonlog where item like \'{identifier}\'')
        currentTotal = cur.fetchone()

        cur.execute(f'select quantity from quotas where material like \'{identifier}\'')
        quota = cur.fetchone()

        if currentTotal < quota:
            await ctx.send(f'Not enough {identifier.capitalize()} have been collected to achieve this boon.')
            return

        remainingConsumption = quota[0]

        cur.execute(f'select distinct boon, tier from quotas where material like \'{identifier}%\'')
        boon = cur.fetchone()

        await ctx.send(f'Consuming {remainingConsumption:,} {identifier.capitalize()} to activate {boon[1]} '
                       f'Boon of {boon[0]}.')

        for record in boonlog:
            # print(f'remaining: {remainingConsumption}')
            if remainingConsumption == 0:
                break
            elif record[6] <= remainingConsumption:
                updateList.append(f'[{record[0]},\'{record[1]}\',\'{record[2]}\',{record[3]},\'{record[4]}\','
                                  f'\'{record[5]}\',0]')
                remainingConsumption -= record[6]
                consumedMaterials.append(f'[\'{record[2]}\',\'{identifier}\',{record[6]}]')
            elif record[6] > remainingConsumption:
                reducedValue = record[6] - remainingConsumption
                updateList.append(f'[{record[0]},\'{record[1]}\',\'{record[2]}\',{record[3]},\'{record[4]}\','
                                  f'\'{record[5]}\',{reducedValue}]')
                consumedMaterials.append(f'[\'{record[2]}\',\'{identifier}\',{remainingConsumption}]')
                remainingConsumption = 0

        for toLog in updateList:
            toLog = ast.literal_eval(str(toLog))
            # print(toLog)
            #toLog = toLog.split(',')
            cur.execute(f'update boonlog set remaining = {toLog[6]} where record_num = {toLog[0]}')
            con.commit()

        date = time.strftime('%x_%X')

        for toTitle in consumedMaterials:
            toTitle = ast.literal_eval(str(toTitle))
            #toTitle = toTitle.split(',')
            cur.execute(f'insert into boon_consumption (date,contributor,item,quantity) values '
                        f'(\'{date}\',\'{toTitle[0]}\',\'{toTitle[1]}\',{toTitle[2]})')
            con.commit()

        cur.execute(f'select contributor, sum(quantity) from boon_consumption where date = \'{date}\' and '
                    f'item like \'%{identifier}%\' group by contributor order by sum(quantity) desc limit 1')
        results = cur.fetchone()

        cur.execute(f'select distinct boon, title, tier from quotas where material like \'{identifier}%\'')
        boon = cur.fetchone()

        regInfo = get_single_registration(results[0])
        discord_id = regInfo[2]

        cur.execute(f'insert or ignore into earned_titles (contributor,title,season) '
                    f'values (\'{discord_id}\',\'{boon[1]}\',\'{CURRENT_SEASON}\')')
        con.commit()

        await ctx.send(f'Title \'{boon[1]}\' for the ** {boon[2]} Boon of {boon[0]}** is awarded '
                       f'to **{results[0]}** with {results[1]:,} {identifier.capitalize()} contributed.\n'
                       f'To activate the boon, use `v/boonset activate {boon[0].casefold()}`')

        con.close()

    @commands.command(name='boonlog',
                      aliases=['log', 'blog', 'boon', 'boons'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def boonlog(self, ctx,
                      name: str = commands.parameter(default='error'),
                      quantity: str = commands.parameter(default=0),
                      material: str = commands.parameter(default='none'),
                      *args):
        """- Logs contributions to the Community Boons system

        Usage: `v/boonlog name qty material [qty] [material] [etc.]...`

        ===============================================

        Valid material options:

        chitin | brimstone | resin | tar | twine | dung

        compositeobsidian | crystal | kits | cochineal | blood | demonblood

        ===============================================

        Parameters
        ----------
        ctx
        name
            - The name of the contributor
        quantity
            - How much of the material was contributed
        material
            - Which type of material was contributed
        args
            - any number of additional quantity + material combinations

        Returns
        -------

        """

        def logboon(add_name, add_quantity, add_material):
            add_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
            add_cur = add_con.cursor()

            date = time.strftime('%x')
            add_cur.execute(f'insert into boonlog (date,contributor,quantity,item,recorded_by,remaining) \
                        values (\'{date}\',\'{add_name}\',\'{add_quantity}\',\'{add_material}\',\
                        \'{ctx.message.author}\', \'{add_quantity}\')')
            add_con.commit()

            output = f'{add_name} turned in {int(add_quantity):,} {add_material} on {date}.\n'

            return output

        characters = get_single_registration(name)
        if not characters:
            await ctx.send(f'No character named `{name}` registered!')
            return
        else:
            # print(characters)
            name = characters[1]

        validMaterials = {'chitin', 'brimstone', 'resin', 'tar', 'twine', 'dung',
                          'compositeobsidian', 'crystal', 'kits', 'cochineal', 'blood', 'demonblood', 'none'}
        delCommands = {'del', 'undo', 'delete', 'last', 'record'}
        infoCommands = {'report', 'all', 'raw', 'report', 'total'}

        if name.casefold() in delCommands:
            await ctx.send(f'Wrong command type. Did you mean to use `v/boondelete`?\n')
            return

        if name.casefold() in infoCommands:
            await ctx.send(f'Wrong command type. Did you mean to use `v/booninfo`?\n')
            return

        if isInt(name):
            await ctx.send(f'Invalid name `{name}`.\n' +
                           f'Must be in the format v/boonlog add name qty material qty ' +
                           f'material qty material (etc)...')
            return

        if material.casefold() not in validMaterials:
            await ctx.send(f'Invalid material type `{material}`\n' +
                           f'Must be in the format `v/boonlog add name qty material qty ' +
                           f'material qty material (etc)...`')
            return

        if quantity:
            quantity = quantity.replace(',', '')

        outputString = f'Recorded the following Boon contributions:\n'
        outputString += logboon(name, int(quantity), material.casefold().capitalize())

        if args:
            if (len(args) % 2) == 0:
                for x in range(0, len(args), 2):
                    intHelper = args[x].replace(',', '')
                    if not isInt(intHelper):
                        await ctx.send(f'Cannot parse provided quantities as integers.\n' +
                                       f'`Must be in the format v/boonlog add name qty material qty ' +
                                       f'material qty material (etc)...`')
                        return
                    else:
                        outputString += logboon(name, int(intHelper),
                                                args[x+1].casefold().capitalize())
            else:
                await ctx.send(f'Wrong number of arguments provided. Try again!')
                return

        await ctx.send(f'{outputString}')

    @commands.command(name='booninfo',
                      aliases=['binfo'])
    @commands.has_any_role('Admin', 'Outcasts')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def booninfo(self, ctx):
        """- Reports on current boon status

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputString = f'**Boon Status as of {datetime.fromtimestamp(float(int_epoch_time()))}**\n'
        settings_list = [['Blood (Experience Multiplier)', 'PlayerXPRateMultiplier', 'Heart of a Hero'],
                         ['Abundance (Harvest Amount)', 'HarvestAmountMultiplier', 'Tablet of Derketo'],
                         ['Proliferation (NPC Respawn)', 'NPCRespawnMultiplier', 'Skull of Yog'],
                         ['Regrowth (Resource Respawn)', 'ResourceRespawnSpeedMultiplier', 'Heart of Nordheimer'],
                         ['Finesse (Stamina Cost)', 'StaminaCostMultiplier', 'Molten Heart'],
                         ['Returning (v/home Discount)', 'BoonOfReturning', 'Eye of Set'],]

        #['Manufacture (Crafting Speed)', 'ItemConvertionMultiplier'],
        #['Preservation (Item Spoil Rate)', 'ItemSpoilRateScale'],
        #['Training (XP From Kills)', 'PlayerXPKillMultiplier'],
        #['Maintenance (Durability)', 'DurabilityMultiplier'],
        #['Abundance (Harvest Amount)', 'HarvestAmountMultiplier'],
        #['Regrowth (Resource Respawn)', 'ResourceRespawnSpeedMultiplier'],
        #['Proliferation (NPC Respawn)', 'NPCRespawnMultiplier'],
        #['Starfall (Meteor Shower)', 'dc meteor spawn'],
        #['Freedom (Thrallable Patron)', 'AddPatron Patron_Thrallable 0']]

        for setting in settings_list:
            (boon_name, setting_name, item) = setting
            value = get_bot_config(f'{setting_name}')

            if 'Starfall' in boon_name or 'Freedom' in boon_name:
                if int(value) >= int_epoch_time():
                    #current_expiration = datetime.fromtimestamp(float(value))
                    outputString += f'Boon of {boon_name} will be available at: <t:{int(value)}> in your time zone.\n'
                else:
                    outputString += f'Boon of {boon_name} is available to be triggered.\n'
                continue

            if int(value) >= int_epoch_time():
                #current_expiration = datetime.fromtimestamp(float(value))
                #{current_expiration}
                outputString += (f'Boon of {boon_name} is active until: <t:{int(value)}> in your time zone. '
                                 f'Turn in a `{item}` at the Profession Hub to extend it.\n')
            else:
                outputString += (f'Boon of {boon_name} is not currently active. '
                                 f'Turn in a `{item}` at the Profession Hub to activate it.\n')

        await ctx.reply(f'{outputString}')

    @commands.command(name='old_booninfo',
                      aliases=['old_boonrep', 'old_brep', 'old_binfo', 'old_boonreport'])
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def old_booninfo(self, ctx,
                           command: str = commands.parameter(default='report')):
        """- Reports on boon contributions

        Accesses the VeramaBot database to report on boon contributions. If no arguments

        are provided, the standard report of all boons will be displayed.

       Use v/booninfo all to see all records.

        Usage:

        v/booninfo vines

        v/booninfo Verama

        v/booninfo all

        v/booninfo report

        ===============================================

        Valid material options:

        chitin | brimstone | resin | tar | twine | dung

        compositeobsidian | crystal | kits | cochineal | blood | demonblood

        Parameters
        ----------
        ctx
        command
            Specify report | material | player | all

        Returns
        -------

        """

        if isInt(command):
            await ctx.send(f'Invalid command `{command}`.')
            return

        match command:
            case 'data' | 'all' | 'raw':
                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select * from boonlog')
                res = cur.fetchall()

                outputString = f'__Record Number, Date, Contributor, Quantity, Material, Recorded By, Remaining__\n'

                for x in res:
                    outputString += f'{str(x)}\n'

                splitOutput = ''

                if len(outputString) > 1800:
                    workList = outputString.splitlines()
                    for items in workList:
                        splitOutput += f'{str(items)}\n'
                        if len(str(splitOutput)) > 1800:
                            await ctx.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                        else:
                            continue
                    await ctx.send(str(splitOutput))
                else:
                    await ctx.send(str(outputString))

            case 'report' | 'total':
                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select b.item, sum(b.remaining), q.quantity, q.boon, q.title, q.tier, q.effect, q.status'
                            f' from boonlog as b left join quotas as q on q.material = b.item group by b.item;')
                res = cur.fetchall()

                outputString = f'__Boon contribution totals:__\n'

                for x in res:
                    # print(x)
                    try:
                        int(x[1])
                    except ValueError:
                        x[1] = 0

                    # print(f'{x[1]} >= {x[2]}')
                    if x[1] >= x[2]:
                        outputString += (f'**{x[5]} Boon of {str(x[3])} - {str(x[0]).capitalize()}**:\n'
                                         f'**Effect:** {x[6]} **Status:** {x[7]}\n*Title: {x[4]}*\n'
                                         f'{int(x[1]):,} of {int(x[2]):,} - _Quota Achieved!_\n\n')
                    else:
                        progress = percentage(x[1], x[2])
                        outputString += (f'**{x[5]} Boon of {str(x[3])} - {str(x[0]).capitalize()}**:\n'
                                         f'**Effect:** {x[6]} **Status:** {x[7]}\n*Title: {x[4]}*\n'
                                         f'{int(x[1]):,} of {int(x[2]):,} - {progress}%\n\n')

                await ctx.send(f'{outputString}')

            case 'chitin' | 'brimstone' | 'resin' | 'tar' | 'twine' | 'dung' | \
                 'compositeobsidian' | 'crystal' | 'kits' | 'cochineal' | 'blood' | 'demonblood':
                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select contributor, sum(remaining) from boonlog '
                            f'where item like \'%{command}%\' group by contributor order by sum(remaining) desc '
                            f'limit 10')
                res = cur.fetchall()

                outputString = (f'__Boon contribution totals for item in Current Quota Period: '
                                f'{command.casefold().capitalize()}__\n')

                for x in res:
                    outputString += f'**{x[0]}** - {int(x[1]):,}\n'

                await ctx.send(outputString)

            case _:
                characters = get_single_registration(command)
                if not characters:
                    await ctx.send(f'No character named `{command}` registered!')
                    return
                else:
                    # print(characters)
                    command = characters[1]

                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select contributor, sum(remaining), item, sum(quantity) from boonlog '
                            f'where contributor like \'%{command}%\' group by item order by sum(remaining) desc')
                res = cur.fetchall()

                outputString = f'**Boon contribution totals for character {command}:**\n'

                if res:
                    for x in res:
                        outputString += (f'__{str(x[2])}__: Current Quota Period: {int(x[1]):,} - '
                                         f'All of Season {CURRENT_SEASON}: {int(x[3]):,}\n')

                await ctx.send(outputString)

    @commands.command(name='boonset')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def setboon(self, ctx, boon_name: str, expiration_time: int):
        """

        Parameters
        ----------
        ctx
        boon_name
        expiration_time

        Returns
        -------

        """
        settings_list = ['ItemConvertionMultiplier', 'ItemSpoilRateScale', 'PlayerXPKillMultiplier',
                         'DurabilityMultiplier', 'HarvestAmountMultiplier', 'ResourceRespawnSpeedMultiplier',
                         'NPCRespawnMultiplier', 'PlayerXPRateMultiplier']
        if boon_name in settings_list:
            set_bot_config(f'{boon_name}', str(expiration_time))
            await ctx.reply(f'Setting {boon_name} expiration time to {expiration_time}')
            update_boons()
        else:
            await ctx.reply(f'Invalid boon specified')

    @commands.command(name='old_boonset',
                      aliases=['old_setboons', 'old_setboon'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def old_setboon(self, ctx, option: str = commands.parameter(default='check'), *args):
        """- Modify Boon settings

        Checks, activates or deactivates a list of boons, or all of them at once.

        ===========

        Usage:
        v/setboon [activate|deactivate|check] [all|boon name] [boon name] [boon name] etc...

        ===========

        Boon names:
        hunger | thirst | fuelrate | craftspeed | spoilrate | thralltime
        xp | durability | harvestrate | resourceRate | spawnrate

        ===========

        Parameters
        ----------
        ctx
        option
            - activate | deactivate | check
        *args:
            - Provide as many as desired
        """

        option = option.casefold()
        if args:
            for x in args:
                x.casefold()

        rconOutput = []
        settings_list = []

        message = await ctx.send(f'`{option}` command execution started... (~20 sec)')

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        match option:
            case 'deactivate' | 'd' | 'off':
                if not args:
                    await message.edit(content=f'Boon name to deactivate must be provided.')
                else:
                    for boonName in args:
                        match boonName:
                            case 'all' | '*':
                                settings_list.extend(['SetServerSetting PlayerActiveHungerMultiplier 1.1',
                                                      'SetServerSetting PlayerIdleHungerMultiplier 1.1',
                                                      'SetServerSetting PlayerActiveThirstMultiplier 1.1',
                                                      'SetServerSetting PlayerIdleThirstMultiplier 1.1',
                                                      'SetServerSetting FuelBurnTimeMultiplier 1.00',
                                                      'SetServerSetting ItemConvertionMultiplier 1.0',
                                                      'SetServerSetting ItemSpoilRateScale 1.0',
                                                      'SetServerSetting ThrallConversionMultiplier 1.0',
                                                      'SetServerSetting AnimalPenCraftingTimeMultiplier 1.0',
                                                      'SetServerSetting PlayerXPKillMultiplier 1.0',
                                                      'SetServerSetting DurabilityMultiplier 1.0',
                                                      'SetServerSetting HarvestAmountMultiplier 1.5',
                                                      'SetServerSetting ResourceRespawnSpeedMultiplier 1.0',
                                                      'SetServerSetting NPCRespawnMultiplier 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\'')
                                break
                            case 'satiation' | 'hunger' | 'chitin':
                                settings_list.extend(['SetServerSetting PlayerActiveHungerMultiplier 1.1',
                                                      'SetServerSetting PlayerIdleHungerMultiplier 1.1'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'quenching' | 'thirst' | 'resin':
                                settings_list.extend(['SetServerSetting PlayerActiveThirstMultiplier 1.1',
                                                      'SetServerSetting PlayerIdleThirstMultiplier 1.1'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'efficiency' | 'fuelrate' | 'tar':
                                settings_list.extend(['SetServerSetting FuelBurnTimeMultiplier 1.00'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'manufacture' | 'craftspeed' | 'twine':
                                settings_list.extend(['SetServerSetting ItemConvertionMultiplier 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'preservation' | 'spoilrate' | 'brimstone':
                                settings_list.extend(['SetServerSetting ItemSpoilRateScale 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'dominance' | 'thralltime' | 'dung':
                                settings_list.extend(['SetServerSetting ThrallConversionMultiplier 1.0',
                                                      'SetServerSetting AnimalPenCraftingTimeMultiplier 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'training' | 'xp' | 'demonblood':
                                settings_list.extend(['SetServerSetting PlayerXPKillMultiplier 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'maintenance' | 'durability' | 'kits':
                                settings_list.extend(['SetServerSetting DurabilityMultiplier 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'abundance' | 'harvestrate' 'crystal':
                                settings_list.extend(['SetServerSetting HarvestAmountMultiplier 1.5'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'regrowth' | 'resourcerate' | 'cochineal':
                                settings_list.extend(['SetServerSetting ResourceRespawnSpeedMultiplier 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'proliferation' | 'spawnrate' | 'blood':
                                settings_list.extend(['SetServerSetting NPCRespawnMultiplier 1.0'])
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'smithing' | 'godforge' | 'compositeobdisian':
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')
                            case _:
                                await ctx.send(f'Invalid Boon \"{boonName}\" specified.')
                                return
                    con.commit()
                    con.close()

            case 'activate' | 'a' | 'on':
                if not args:
                    await message.edit(content=f'Boon name to activate must be provided.')
                else:
                    for boonName in args:
                        match boonName:
                            case 'all' | '*':
                                settings_list.extend(['SetServerSetting PlayerActiveHungerMultiplier 0.5',
                                                      'SetServerSetting PlayerIdleHungerMultiplier 0.5',
                                                      'SetServerSetting PlayerActiveThirstMultiplier 0.5',
                                                      'SetServerSetting PlayerIdleThirstMultiplier 0.5',
                                                      'SetServerSetting FuelBurnTimeMultiplier 2.00',
                                                      'SetServerSetting ItemConvertionMultiplier 0.5',
                                                      'SetServerSetting ItemSpoilRateScale 0.5',
                                                      'SetServerSetting ThrallConversionMultiplier 0.5',
                                                      'SetServerSetting AnimalPenCraftingTimeMultiplier 0.5',
                                                      'SetServerSetting PlayerXPKillMultiplier 2.0',
                                                      'SetServerSetting DurabilityMultiplier 0.5',
                                                      'SetServerSetting HarvestAmountMultiplier 3.0',
                                                      'SetServerSetting ResourceRespawnSpeedMultiplier 2.0',
                                                      'SetServerSetting NPCRespawnMultiplier 0.5'])
                                cur.execute(f'update quotas set status = \'Active\'')
                                break
                            case 'satiation' | 'satiation' | 'hunger' | 'chitin':
                                settings_list.extend(['SetServerSetting PlayerActiveHungerMultiplier 0.5',
                                                      'SetServerSetting PlayerIdleHungerMultiplier 0.5'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'quenching' | 'quenching' | 'thirst' | 'resin':
                                settings_list.extend(['SetServerSetting PlayerActiveThirstMultiplier 0.5',
                                                      'SetServerSetting PlayerIdleThirstMultiplier 0.5'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'efficiency' | 'efficiency' | 'fuelrate' | 'tar':
                                settings_list.extend(['SetServerSetting FuelBurnTimeMultiplier 2.00'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'manufacture' | 'manufacture' | 'craftspeed' | 'twine':
                                settings_list.extend(['SetServerSetting ItemConvertionMultiplier 0.5'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'preservation' | 'preservation' | 'spoilrate' | 'brimstone':
                                settings_list.extend(['SetServerSetting ItemSpoilRateScale 0.5'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'dominance' | 'dominance' | 'thralltime' | 'dung':
                                settings_list.extend(['SetServerSetting ThrallConversionMultiplier 0.5',
                                                      'SetServerSetting AnimalPenCraftingTimeMultiplier 0.5'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'training' | 'training' | 'xp' | 'demonblood':
                                settings_list.extend(['SetServerSetting PlayerXPKillMultiplier 2.0'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material = \'Demonblood\'')

                            case 'maintenance' | 'maintenance' | 'durability' | 'kits':
                                settings_list.extend(['SetServerSetting DurabilityMultiplier 0.5'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'abundance' | 'abundance' | 'harvestrate' | 'crystal':
                                settings_list.extend(['SetServerSetting HarvestAmountMultiplier 3.0'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'regrowth' | 'regrowth' | 'resourcerate' | 'cochineal':
                                settings_list.extend(['SetServerSetting ResourceRespawnSpeedMultiplier 2.0'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material like \'%{boonName}%\'')

                            case 'proliferation' | 'proliferation' | 'spawnrate' | 'blood':
                                settings_list.extend(['SetServerSetting NPCRespawnMultiplier 0.5'])
                                cur.execute(f'update quotas set status = \'Active\' '
                                            f'where material = \'Blood\'')

                            case 'smithing' | 'godforge' | 'compositeobsidian':
                                cur.execute(f'update quotas set status = \'Inactive\' '
                                            f'where material like \'%{boonName}%\'')
                            case _:
                                await ctx.send(f'Invalid Boon \"{boonName}\" specified.')
                                return
                    con.commit()
                    con.close()

            case 'check' | 'c':
                settings_list.extend(['GetServerSetting PlayerActiveHungerMultiplier',
                                      'GetServerSetting PlayerIdleHungerMultiplier',
                                      'GetServerSetting PlayerActiveThirstMultiplier',
                                      'GetServerSetting PlayerIdleThirstMultiplier',
                                      'GetServerSetting FuelBurnTimeMultiplier',
                                      'GetServerSetting ItemConvertionMultiplier',
                                      'GetServerSetting ItemSpoilRateScale',
                                      'GetServerSetting ThrallConversionMultiplier',
                                      'GetServerSetting AnimalPenCraftingTimeMultiplier',
                                      'GetServerSetting PlayerXPKillMultiplier',
                                      'GetServerSetting DurabilityMultiplier',
                                      'GetServerSetting HarvestAmountMultiplier',
                                      'GetServerSetting ResourceRespawnSpeedMultiplier',
                                      'GetServerSetting NPCRespawnMultiplier'])
            case _:
                await message.edit(content=f'Invalid option specified.')
                return

        for command in settings_list:
            rconResponse = runRcon(command)
            if rconResponse.error == 1:
                rconResponse.output = f'Authentication error on {command}'
            rconOutput.extend(rconResponse.output)

        if option == 'check':
            await message.edit(content=f'List of current Boon settings:\n' + '\n'.join(rconOutput))
        else:
            await message.edit(content=f'Boon command completed. Settings have been updated! \n' +
                                       '\n'.join(rconOutput))
        return

    @commands.command(name='titleclear', aliases=['cleartitle'])
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def titleClear(self, ctx):
        """- Removes your current title

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        character = is_registered(ctx.author.id)

        if character:
            try:
                await ctx.author.edit(nick=f'{character.char_name}')
            except discord.errors.Forbidden:
                await ctx.reply(f'Missing persmissions to change nickname on {ctx.author.name}')
                return
            await ctx.reply(f'Your title has been removed, {character.char_name}')
            return
        else:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}!')
            return

    @commands.command(name='title')
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def title(self, ctx, set_title: int = 0):
        """- Check titles you have earned or set your title.

        Parameters
        ----------
        ctx
        set_title

        Returns
        -------

        """
        outputString = (f'To set one of the listed titles, use `v/title #`.\nTo remove your title, use v/titleclear.'
                        f'\nAvailable Titles:\n')

        character = is_registered(ctx.author.id)
        if character:
            results = db_query(False, f'select title from earned_titles where contributor = \'{ctx.author.id}\'')
        else:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}!')
            return

        if results:
            if set_title:
                titleRecord = results.pop(int(set_title)-1)

                try:
                    await ctx.author.edit(nick=f'{character.char_name} {titleRecord[0]}')
                except discord.errors.Forbidden:
                    await ctx.reply(f'Missing persmissions to change nickname on {ctx.author.name}')
                    return

                await ctx.reply(f'Your title has been set to `{titleRecord[0]}`!')
                return
            else:
                for index, result in enumerate(results):
                    outputString += f'{index+1} - {result[0]}\n'

                await ctx.reply(f'{outputString}')
                return
        else:
            await ctx.reply(f'You have not earned any titles this season.')
            return

    #
    # else:
    #     if int(get_bot_config(f'ItemConvertionMultiplier')) >= currentTime:
    #         command_prep.append(['ItemConvertionMultiplier', '0.7'])
    #     else:
    #         command_prep.append(['ItemConvertionMultiplier', '1.0'])
    #
    #     if int(get_bot_config(f'ItemSpoilRateScale')) >= currentTime:
    #         command_prep.append(['ItemSpoilRateScale', '0.7'])
    #     else:
    #         command_prep.append(['ItemSpoilRateScale', '1.0'])
    #
    #     value = int(get_bot_config(f'PlayerXPKillMultiplier'))
    #     print(f'{value} - {currentTime}')
    #     if int(get_bot_config(f'PlayerXPKillMultiplier')) >= currentTime:
    #         command_prep.append(['PlayerXPKillMultiplier', '1.5'])
    #     else:
    #         command_prep.append(['PlayerXPKillMultiplier', '1.0'])
    #
    #     if int(get_bot_config(f'PlayerXPRateMultiplier')) >= currentTime:
    #         command_prep.append(['PlayerXPRateMultiplier', '1.5'])
    #     else:
    #         command_prep.append(['PlayerXPRateMultiplier', '1.0'])
    #
    #     if int(get_bot_config(f'DurabilityMultiplier')) >= currentTime:
    #         command_prep.append(['DurabilityMultiplier', '0.7'])
    #     else:
    #         command_prep.append(['DurabilityMultiplier', '1.0'])
    #
    #     if int(get_bot_config(f'HarvestAmountMultiplier')) >= currentTime:
    #         command_prep.append(['HarvestAmountMultiplier', '1.5'])
    #     else:
    #         command_prep.append(['HarvestAmountMultiplier', '1.0'])
    #
    #     if int(get_bot_config(f'ResourceRespawnSpeedMultiplier')) >= currentTime:
    #         command_prep.append(['ResourceRespawnSpeedMultiplier', '0.7'])
    #     else:
    #         command_prep.append(['ResourceRespawnSpeedMultiplier', '1.0'])
    #
    #     if int(get_bot_config(f'NPCRespawnMultiplier')) >= currentTime:
    #         command_prep.append(['NPCRespawnMultiplier', '0.7'])
    #     else:
    #         command_prep.append(['NPCRespawnMultiplier', '1.0'])
    #


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(CommunityBoons(bot))
