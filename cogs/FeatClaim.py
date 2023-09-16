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
    async def restoreFeats(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        charId = is_registered(ctx.message.author)
        hasFeatString = ''
        missingFeatString = ''
        missingFeatList = []

        if not charId:
            await ctx.send(f'No character registered to {ctx.message.author}!')
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

            if missingFeatString:
                await ctx.send(f'Character {charId.char_name} (id {charId.id}) is missing feats: '
                               f'[{missingFeatString[:-2]}]')

                for missingFeat in missingFeatList:
                    target = get_rcon_id(charId.char_name)
                    rconResponse = runRcon(f'con {target} learnfeat {missingFeat}')
                    await ctx.send(rconResponse.output)
            else:
                await ctx.send(f'Character {charId.char_name} (id {charId.id}) already knows all of the Siptah '
                               f'feats currently available to them.')
                return

            if hasFeatString:
                await ctx.send(f'Character {charId.char_name} (id {charId.id}) already knows feats: '
                               f'[{hasFeatString[:-2]}]')
                #run rcon to see if they are online?
                #kick them offline
                #warn them that it won't work if they are online
                #insert the record into their item_inventory (confirmed blob can be left alone)
                #insert into item_inventory set (item_id,owner_id,inv_type,template_id) values ( ) where
                #select max(item_id)+1 from item_inventory where owner_id = charId
                #not going to work because I cant write
                #or, run learnfeat command

    @commands.command(name='featadd', aliases=['addfeats', 'addfeat'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def addFeat(self, ctx, feat: int, discord_user: discord.Member):
        """

        Parameters
        ----------
        ctx
        feat
            The feat number to add (int)
        discord_user

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
        """

        Parameters
        ----------
        ctx
        discord_user

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
