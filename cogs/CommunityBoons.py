import time
import sqlite3
import ast

from functions.common import *
from functions.externalConnections import *

from discord.ext import commands

from functions.common import custom_cooldown, checkChannel

class CommunityBoons(commands.Cog):
    """Cog class containing commands related to server status.

    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='boondelete',
                      aliases=['logdel', 'boondel', 'delboon', 'delboons'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
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
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
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
                if x[1] >= x[2]:
                    outputString += f'{x[0]} '

            outputString = outputString[:-1]

            await ctx.send(f'Prepared activation command: `v/boonset activate {outputString}`')
            return
        #add input checking for material type

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

        cur.execute(f'select distinct boon from quotas where material like \'{identifier}%\'')
        boon = cur.fetchone()

        await ctx.send(f'Consuming {remainingConsumption:,} {identifier.capitalize()} to activate Boon of {boon[0]}.')

        for record in boonlog:
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
            #toLog = toLog.split(',')
            cur.execute(f'update boonlog set remaining = {toLog[6]} where record_num = {toLog[0]}')
            con.commit()

        date = time.strftime('%x')

        for toTitle in consumedMaterials:
            toTitle = ast.literal_eval(str(toTitle))
            #toTitle = toTitle.split(',')
            cur.execute(f'insert into titles (date,contributor,item,quantity) values '
                        f'(\'{date}\',\'{toTitle[0]}\',\'{toTitle[1]}\',{toTitle[2]})')
            con.commit()

        cur.execute(f'select contributor, sum(quantity) from titles where date = \'{date}\' and '
                    f'item like \'%{identifier}%\' group by contributor order by sum(quantity) desc limit 1')
        results = cur.fetchone()

        cur.execute(f'select distinct boon from quotas where material like \'{identifier}%\'')
        boon = cur.fetchone()

        await ctx.send(f'Title for the **Boon of {boon[0]}** is awarded to **{results[0]}** with '
                       f'{results[1]:,} {identifier.capitalize()} contributed.\n'
                       f'To activate the boon, use `v/boonset activate {boon[0].casefold()}`')

        con.close()

    @commands.command(name='boonlog',
                      aliases=['log', 'blog', 'boon', 'boons'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def boonlog(self, ctx,
                      name: str = commands.parameter(default='error'),
                      quantity: str = commands.parameter(default=0),
                      material: str = commands.parameter(default='none'),
                      *args):
        """- Logs contributions to the Community Boons system

        Usage: `v/boonlog name qty material [qty] [material] [etc.]...`

        ===============================================

        Valid material options:

        vines | brimstone | flasks | tar | twine | dung

        obsidian | crystal | kits | cochineal | blood

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

        validMaterials = {'vines', 'brimstone', 'flasks', 'tar', 'twine', 'dung',
                          'obsidian', 'crystal', 'kits', 'cochineal', 'blood', 'none'}
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
        outputString += logboon(name.casefold().capitalize(), int(quantity), material.casefold().capitalize())

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
                        outputString += logboon(name.casefold().capitalize(), int(intHelper),
                                                args[x+1].casefold().capitalize())
            else:
                await ctx.send(f'Wrong number of arguments provided. Try again!')
                return

        await ctx.send(f'{outputString}')

    @commands.command(name='booninfo',
                      aliases=['boonr', 'brep', 'binfo', 'boonreport'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def booninfo(self, ctx,
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

        vines | brimstone | flasks | tar | twine | dung

        obsidian | crystal | kits | cochineal | blood

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

                cur.execute(f'select b.item, sum(b.remaining), q.quantity, q.boon from boonlog as b ' +
                            f'left join quotas as q on q.material = b.item group by b.item;')
                res = cur.fetchall()

                outputString = f'__Boon contribution totals:__\n'

                for x in res:
                    if x[1] >= x[2]:
                        outputString += (f'**Boon of {str(x[3])} - {str(x[0]).capitalize()}**:\n{int(x[1]):,} of '
                                         f'{int(x[2]):,} - _Quota Achieved!_\n\n')
                    else:
                        progress = percentage(x[1], x[2])
                        outputString += (f'**Boon of {str(x[3])} - {str(x[0]).capitalize()}**:\n'
                                         f'{int(x[1]):,} of {int(x[2]):,} - {progress}%\n\n')

                await ctx.send(f'{outputString}')

            case 'vines' | 'brimstone' | 'flasks' | 'tar' | 'twine' | 'dung' | \
                 'obsidian' | 'crystal' | 'kits' | 'cochineal' | 'blood':
                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select contributor, sum(remaining) from boonlog '
                            f'where item like \'%{command}%\' group by contributor order by sum(remaining) desc '
                            f'limit 10')
                res = cur.fetchall()

                outputString = f'__Boon contribution totals for item: {command.casefold().capitalize()}__\n'

                for x in res:
                    outputString += f'**{x[0]}** - {int(x[1]):,}\n'

                await ctx.send(outputString)

            case _:
                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select contributor, sum(remaining), item, sum(quantity) from boonlog '
                            f'where contributor like \'%{command}%\' group by item order by sum(remaining) desc')
                res = cur.fetchall()

                outputString = (f'**Boon contribution totals for {command.casefold().capitalize()}:**\n'
                                f'*Current Quota Period - (All of season 4)*\n')

                if res:
                    for x in res:
                        outputString += f'__{str(x[2])}__: {int(x[1]):,} - ({int(x[3]):,})\n'

                await ctx.send(outputString)

    @commands.command(name='boonset',
                      aliases=['setboons', 'setboon'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def setboon(self, ctx, option: str = commands.parameter(default='check'), *args):
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
                                                      'SetServerSetting HarvestAmountMultiplier 2.0',
                                                      'SetServerSetting ResourceRespawnSpeedMultiplier 1.0',
                                                      'SetServerSetting NPCRespawnMultiplier 1.0'])
                                break
                            case 'satiation' | 'hunger':
                                settings_list.extend(['SetServerSetting PlayerActiveHungerMultiplier 1.1',
                                                      'SetServerSetting PlayerIdleHungerMultiplier 1.1'])

                            case 'quenching' | 'thirst':
                                settings_list.extend(['SetServerSetting PlayerActiveThirstMultiplier 1.1',
                                                      'SetServerSetting PlayerIdleThirstMultiplier 1.1'])

                            case 'efficiency' | 'fuelrate':
                                settings_list.extend(['SetServerSetting FuelBurnTimeMultiplier 1.00'])

                            case 'manufacture' | 'craftspeed':
                                settings_list.extend(['SetServerSetting ItemConvertionMultiplier 1.0'])

                            case 'preservation' | 'spoilrate':
                                settings_list.extend(['SetServerSetting ItemSpoilRateScale 1.0'])

                            case 'dominance' | 'thralltime':
                                settings_list.extend(['SetServerSetting ThrallConversionMultiplier 1.0',
                                                      'SetServerSetting AnimalPenCraftingTimeMultiplier 1.0'])

                            case 'training' | 'xp':
                                settings_list.extend(['SetServerSetting PlayerXPKillMultiplier 1.0'])

                            case 'maintenance' | 'durability':
                                settings_list.extend(['SetServerSetting DurabilityMultiplier 1.0'])

                            case 'abundance' | 'harvestrate':
                                settings_list.extend(['SetServerSetting HarvestAmountMultiplier 2.0'])

                            case 'regrowth' | 'resourcerate':
                                settings_list.extend(['SetServerSetting ResourceRespawnSpeedMultiplier 1.0'])

                            case 'proliferation' | 'spawnrate':
                                settings_list.extend(['SetServerSetting NPCRespawnMultiplier 1.0'])
                            case _:
                                await ctx.send(f'Invalid Boon \"{boonName}\" specified.')
                                return

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
                                break
                            case 'Satiation' | 'satiation' | 'hunger':
                                settings_list.extend(['SetServerSetting PlayerActiveHungerMultiplier 0.5',
                                                      'SetServerSetting PlayerIdleHungerMultiplier 0.5'])

                            case 'Quenching' | 'quenching' | 'thirst':
                                settings_list.extend(['SetServerSetting PlayerActiveThirstMultiplier 0.5',
                                                      'SetServerSetting PlayerIdleThirstMultiplier 0.5'])

                            case 'Efficiency' | 'efficiency' | 'fuelrate':
                                settings_list.extend(['SetServerSetting FuelBurnTimeMultiplier 2.00'])

                            case 'Manufacture' | 'manufacture' | 'craftspeed':
                                settings_list.extend(['SetServerSetting ItemConvertionMultiplier 0.5'])

                            case 'Preservation' | 'preservation' | 'spoilrate':
                                settings_list.extend(['SetServerSetting ItemSpoilRateScale 0.5'])

                            case 'Dominance' | 'dominance' | 'thralltime':
                                settings_list.extend(['SetServerSetting ThrallConversionMultiplier 0.5',
                                                      'SetServerSetting AnimalPenCraftingTimeMultiplier 0.5'])

                            case 'Training' | 'training' | 'xp':
                                settings_list.extend(['SetServerSetting PlayerXPKillMultiplier 2.0'])

                            case 'Maintenance' | 'maintenance' | 'durability':
                                settings_list.extend(['SetServerSetting DurabilityMultiplier 0.5'])

                            case 'Abundance' | 'abundance' | 'harvestrate':
                                settings_list.extend(['SetServerSetting HarvestAmountMultiplier 3.0'])

                            case 'Regrowth' | 'regrowth' | 'resourcerate':
                                settings_list.extend(['SetServerSetting ResourceRespawnSpeedMultiplier 2.0'])

                            case 'Proliferation' | 'proliferation' | 'spawnrate':
                                settings_list.extend(['SetServerSetting NPCRespawnMultiplier 0.5'])

                            case _:
                                await ctx.send(f'Invalid Boon \"{boonName}\" specified.')
                                return
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


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(CommunityBoons(bot))
