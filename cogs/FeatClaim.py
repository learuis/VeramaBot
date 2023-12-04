import sqlite3

from discord.ext import commands
from functions.common import custom_cooldown, modChannel, get_rcon_id, is_registered, get_single_registration, \
    publicChannel
from functions.externalConnections import runRcon, db_query, db_delete_single_record


def has_feat(charId: int, featId: int):
    rconResponse = runRcon(f'sql select template_id from item_inventory where owner_id = {charId} '
                           f'and template_id = {featId} and inv_type = 6')
    #we should only ever get one record back.
    #error handling?

    print(rconResponse.output)

    #drop first record (success statement)
    rconResponse.output.pop(0)

    print(rconResponse.output)

    if not rconResponse.output:
        print('no more records')
        return False

    for x in rconResponse.output:
        if str(featId) in x:
            print(f'eval true')
            return True
        else:
            print('eval false')
            return False

def get_feat_list(charId: int):
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()
    cur.execute(f'select char_id, feat_id from featclaim where char_id = {charId}')
    featList = cur.fetchall()
    con.close()

    return featList

class FeatClaim(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='featrestore', aliases=['feats', 'restore', 'knowledge', 'restorefeats'])
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(publicChannel)
    async def featRestore(self, ctx):
        """- Restore all feats that were previously granted to you

        Parameters
        ----------
        ctx
        Returns
        -------

        """
        charId = is_registered(ctx.message.author.id)

        hasFeatString = ''
        missingFeatString = ''
        missingFeatList = []
        featDict = {}

        if not charId:
            outputString = f'No character registered to {ctx.message.author.mention}!'
            await ctx.reply(content=outputString)
            return

        if not get_rcon_id(charId.char_name):
            await ctx.reply(f'Character `{charId.char_name}` must be online to restore feats!')
            return

        outputString = f'Starting feat restore process... (~20 sec)'
        message = await ctx.reply(outputString)

        featList = get_feat_list(charId.id)

        lookup_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        lookup_cur = lookup_con.cursor()
        lookup_cur.execute(f'select feat_id, feat_name from valid_feats')
        featLookupList = lookup_cur.fetchall()
        lookup_con.close()

        for record in featLookupList:
            featDict[record[0]] = record[1]

        print(featDict)

        if has_feat(charId.id, 576):
            hasFeatString = f'576, '
        else:
            missingFeatList.append(576)
            missingFeatString = f'576, '

        for record in featList:
            feat = record[1]
            if has_feat(charId.id, feat):
                hasFeatString += f'{feat}, '
            else:
                missingFeatList.append(feat)
                missingFeatString += f'{feat}, '

        outputString = ''

        if not missingFeatString:
            outputString += f'Character {charId.char_name} (id {charId.id}) already knows all of '\
                            f'the Siptah feats currently available to them.'
            await message.edit(content=outputString)
            return

        if hasFeatString:
            outputString += f'\nCharacter {charId.char_name} (id {charId.id}) already knows feats: ' \
                            f'[{hasFeatString[:-2]}]'
            await message.edit(content=outputString)

        if missingFeatString:
            outputString += f'\nCharacter {charId.char_name} (id {charId.id}) is missing feats: '\
                            f'[{missingFeatString[:-2]}]'
            await message.edit(content=outputString)

            for missingFeat in missingFeatList:
                target = get_rcon_id(charId.char_name)
                try:
                    runRcon(f'con {target} learnfeat {missingFeat}')
                    feat_name = featDict.get(int(missingFeat))
                    outputString += f'\nGranted feat {feat_name}.'
                except TimeoutError:
                    outputString += f'\nRCON Timeout when trying to grant feat {feat_name}.'

                await message.edit(content=outputString)

        outputString += f'\nFeats restored for {charId.char_name} {ctx.message.author.mention}.'
        await message.edit(content=outputString)

    @commands.command(name='featadd', aliases=['addfeats', 'addfeat'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def addFeat(self, ctx, feat: int, name: str):
        """- Adds a feat to the list granted to a player

        Parameters
        ----------
        ctx
        feat
            The feat number to add (int)
        name
            Which character to grant the feat to
        Returns
        -------

        """
        #(id,name)

        characters = get_single_registration(name)
        if not characters:
            await ctx.reply(f'No character named `{name}` registered!')
            return
        else:
            name = characters[1]
            charId = characters[0]

        #check if feat being added is valid
        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()
        cur.execute(f'select 1 from valid_feats where feat_id = {feat}')
        result = cur.fetchone()
        con.close()

        if not result:
            await ctx.reply(f'Feat `{feat}` is not permitted to be added to Feat Claim table.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()
        cur.execute(f'insert or ignore into featclaim (char_id,feat_id) values ({charId},{feat})')
        con.commit()
        con.close()

        await ctx.reply(f'Added Feat `{feat}` to Feat Claim table for character `{name}` (id `{charId}`)')

    @commands.command(name='featlist', aliases=['listfeats', 'listfeat'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def featList(self, ctx, name: str):
        """- List all feats that have been granted to a player

        Parameters
        ----------
        ctx
        name
            Which character to check
        Returns
        -------

        """
        if name == 'all':
            outputString = ''
            splitOutput = ''
            once = True
            results = db_query(f'select * from featclaim')

            for result in results:
                outputString += f'{result}\n'

            if outputString:
                if len(outputString) > 10000:
                    await ctx.send(f'Too many results!')
                    return
                if len(outputString) > 1800:
                    workList = outputString.splitlines()
                    for items in workList:
                        splitOutput += f'{str(items)}\n'
                        if len(str(splitOutput)) > 1800:
                            if once:
                                once = False
                                await ctx.send(content=str(splitOutput))
                                splitOutput = '(continued)\n'
                            else:
                                await ctx.send(str(splitOutput))
                                splitOutput = '(continued)\n'
                        else:
                            continue
                    await ctx.send(str(splitOutput))
                else:
                    await ctx.send(str(outputString))
            return

        characters = get_single_registration(name)
        if not characters:
            await ctx.reply(f'No character named `{name}` registered!')
            return
        else:
            name = characters[1]
            charId = characters[0]

        featList = get_feat_list(charId)

        hasFeatString = f'Character `{name}` (id `{charId}`) is entitled to feats: `[576, '

        for feat in featList:
            hasFeatString += f'{feat[1]}, '
        await ctx.reply(f'{hasFeatString[:-2]}]`')

    @commands.command(name='featlibrary', aliases=['viewfeats', 'validfeats', 'featlib'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def featLibrary(self, ctx):
        """- Prints the list of feats that can be granted with v/featadd

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputString = '__Valid feats for use with v/featadd:__\n'
        results = db_query('select * from valid_feats order by feat_name asc')
        splitOutput = ''
        once = True

        for result in results:
            outputString += f'{result}\n'

        if outputString:
            if len(outputString) > 10000:
                await ctx.send(f'Too many results!')
                return
            if len(outputString) > 1800:
                workList = outputString.splitlines()
                for items in workList:
                    splitOutput += f'{str(items)}\n'
                    if len(str(splitOutput)) > 1800:
                        if once:
                            once = False
                            await ctx.send(content=str(splitOutput))
                            splitOutput = '(continued)\n'
                        else:
                            await ctx.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                    else:
                        continue
                await ctx.send(str(splitOutput))
            else:
                await ctx.send(str(outputString))

    @commands.command(name='featdelete', aliases=['featdel', 'delfeat'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def featDelete(self, ctx, recordToDelete: int = commands.parameter(default=0)):
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
                res = db_delete_single_record('featclaim', 'record_num', recordToDelete)

                await ctx.send(f'Deleted record:\n{res}')
@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(FeatClaim(bot))
