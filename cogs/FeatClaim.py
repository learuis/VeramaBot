import sqlite3

import discord
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel, get_rcon_id, is_registered
from functions.externalConnections import runRcon

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

    @commands.command(name='restorefeats', aliases=['feats', 'restore', 'knowledge'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def restoreFeats(self, ctx, discord_user: discord.Member = None):
        """- Restore all feats that were previously granted

        Parameters
        ----------
        ctx
        discord_user
            Optional. Mention (@ tag) a user to target them, otherwise targets self. Must be registered and linked.
        Returns
        -------

        """
        if discord_user:
            charId = is_registered(discord_user.name)
        else:
            charId = is_registered(ctx.message.author)

        hasFeatString = ''
        missingFeatString = ''
        missingFeatList = []

        if not get_rcon_id(charId.char_name):
            await ctx.send(f'Character `{charId.char_name}` must be online to restore feats!')
            return

        outputString = f'Starting feat restore process... (~20 sec)'

        message = await ctx.send(outputString)

        if not charId:
            outputString = f'No character registered to {charId.char_name}!'
            await message.edit(content=outputString)
        else:
            featList = get_feat_list(charId.id)

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
                    rconResponse = runRcon(f'con {target} learnfeat {missingFeat}')
                    outputString += f'\n{rconResponse.output}'
                    await message.edit(content=outputString)

            if discord_user:
                outputString += f'\nFeats restored for {charId.char_name} {discord_user.mention}.'
            else:
                outputString += f'\nFeats restored for {charId.char_name} {ctx.message.author.mention}.'

            await message.edit(content=outputString)

    @commands.command(name='featadd', aliases=['addfeats', 'addfeat'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def addFeat(self, ctx, feat: int, discord_user: discord.Member):
        """- Adds a feat to the list granted to a player

        Parameters
        ----------
        ctx
        feat
            The feat number to add (int)
        discord_user
            Mention (@ tag) a user to target them. Must be registered and linked.
        Returns
        -------

        """
        #(id,name)

        charId = is_registered(discord_user.name)

        if not charId:
            await ctx.send(f'No character registered to {charId}!')
            return

        #check if feat being added is valid
        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()
        cur.execute(f'select 1 from valid_feats where feat_id = {feat}')
        result = cur.fetchone()
        con.close()

        if not result:
            await ctx.send(f'Feat `{feat}` is not permitted to be added to Feat Claim table.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()
        cur.execute(f'insert or ignore into featclaim (char_id,feat_id) values ({charId.id},{feat})')
        con.commit()
        con.close()

        await ctx.send(f'Added Feat `{feat}` to Feat Claim table for character {charId.char_name} (id {charId.id})')

    @commands.command(name='featlist', aliases=['listfeats', 'listfeat'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def featList(self, ctx, discord_user: discord.Member):
        """- List all feats that have been granted to a player

        Parameters
        ----------
        ctx
        discord_user
            Mention (@ tag) a user to target them. Must be registered and linked.
        Returns
        -------

        """

        charId = is_registered(discord_user.name)
        if not charId:
            await ctx.send(f'No character registered to {charId}!')
            return

        featList = get_feat_list(charId.id)

        hasFeatString = f'Character {charId.char_name} (id {charId.id}) is entitled to feats: [576, '

        for feat in featList:
            hasFeatString += f'{feat[1]}, '
        await ctx.send(f'{hasFeatString[:-2]}]')


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(FeatClaim(bot))
