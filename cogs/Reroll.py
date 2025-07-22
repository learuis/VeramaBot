import os
import re

from discord.ext import commands

from cogs.EldariumBank import get_balance, eld_transaction
from functions.common import is_registered, get_rcon_id, last_season_char, get_bot_config, no_registered_char_reply, \
    flatten_list, run_console_command_by_name

from dotenv import load_dotenv

from functions.externalConnections import runRcon, db_query

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))

def get_prestige_points(character):
    points = []
    points = db_query(False, f'select sum(points) from prestige where discord_id = {character.discord_id}')
    if points:
        print(points)
        points = flatten_list(points)
        if points[0]:
            return int(points[0])
        else:
            return 0
    else:
        return 0

class Reroll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reroll')
    @commands.has_any_role('Admin', 'Moderator', 'BuildHelper')
    async def reroll(self, ctx):
        """
        Disassociates your previous season character from your account, allowing you to create a new one.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = last_season_char(ctx.message.author.id)
        if not character:
            channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No Season {PREVIOUS_SEASON} character registered to player {ctx.author.mention}! '
                            f'To roll over a character to Season {CURRENT_SEASON}, '
                            f'you must have registered a character in Season {PREVIOUS_SEASON} {channel.mention} ')
            return
        else:
            if get_rcon_id(character.char_name):
                outputString = f'Character `{character.char_name}` must be offline to reroll!'
                await ctx.reply(outputString)
                return

        runRcon(f'sql update account set user = \'{ctx.author.id}_S{PREVIOUS_SEASON}\' where id in ( '
                f'select c.playerId from characters as c where c.id = {character.id} )')
        runRcon(f'sql update characters set char_name = \'{ctx.author.id}_S{PREVIOUS_SEASON}\' '
                f'where id = {character.id}')

        reroll_points = int(get_bot_config(f'reroll_points'))

        query_string = (f'insert or replace into prestige (discord_id, reason, points) values ({character.discord_id}, '
                        f'\'Reroll Season {PREVIOUS_SEASON} to {CURRENT_SEASON}\', {reroll_points})')
        print(query_string)

        db_query(True, f'{query_string}')

        await ctx.reply(f'Removed association to Season {PREVIOUS_SEASON} character `{character.char_name}` '
                        f'from {ctx.author.mention}. \nYou have been granted 5 Prestige Points for rerolling!\n'
                        f'You must create and register your new character before transferring feats!')
    #
    # @commands.command(name='fomofeats')
    # @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
    # async def fomofeats(self, ctx):
    #     """
    #     Transfers learned feats from your previous season character to your current season character
    #
    #     Parameters
    #     ----------
    #     ctx
    #
    #     """
    #     prev_character = last_season_char(ctx.message.author.id)
    #     if not prev_character:
    #         await ctx.reply(f'No season {PREVIOUS_SEASON} character registered to player {ctx.author.mention}! '
    #                         f'To transfer FOMO feats from a previous season character, you must have created a character '
    #                         f'in the previous season.')
    #         return
    #     current_character = is_registered(ctx.message.author.id)
    #     if not current_character:
    #         await ctx.reply(f'No season {CURRENT_SEASON} character registered to player {ctx.author.mention}! '
    #                         f'To transfer FOMO feats from a previous season character, you must have first '
    #                         f'created and registered your Season {CURRENT_SEASON} character.')
    #     else:
    #         if get_rcon_id(prev_character.char_name) or get_rcon_id(current_character.char_name):
    #             outputString = (f'Both characters `{prev_character.char_name}` and `{current_character.char_name}` '
    #                             f'must be offline to transfer feats!')
    #             await ctx.reply(outputString)
    #             return
    #         else:
    #             db_query(True, f'insert or replace into featclaim '
    #                            f'select {CURRENT_SEASON}, {current_character.id}, feat_id from featclaim '
    #                            f'where char_id = {prev_character.id} and season = {PREVIOUS_SEASON} '
    #                            f'and feat_id in ( select feat_id from fomo_feats );')
    #             restored_feats = db_query(False, f'select featclaim.feat_id, valid_feats.feat_name '
    #                                              f'from featclaim '
    #                                              f'left join valid_feats on featclaim.feat_id = valid_feats.feat_id '
    #                                              f'where featclaim.char_id = {current_character.id} '
    #                                              f'and featclaim.season = {CURRENT_SEASON} '
    #                                              f'and featclaim.feat_id in ( select feat_id from fomo_feats )')
    #             await ctx.reply(f'FOMO Feats `{restored_feats}` have been transferred from `{prev_character.char_name}` '
    #                             f'to `{current_character.char_name}`. Log in to your new character, '
    #                             f'then use `v/featrestore` to learn them.')
    #         return
    #
    @commands.command(name='prestige')
    @commands.has_any_role('Admin', 'Moderator', 'BuildHelper')
    async def prestige(self, ctx):
        """
        Grants you earned prestige points

        Parameters
        ----------
        ctx

        """
        distributed_points = ''
        undistributed_points = ''
        total_points = ''
        character = is_registered(ctx.author.id)
        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        rconCharId = get_rcon_id(character.char_name)
        if rconCharId:
            await ctx.reply(f'Character `{character.char_name}` must be offline to be claim prestige points!')
            return

        results = runRcon(f'sql select substr(hex(value),9,2) from properties where object_id = {character.id} '
                          f'and name = \'BP_ProgressionSystem_C.AttributePointsDistributed\'')
        results.output.pop(0)
        if len(results.output) == 1:
            distributed_points = re.search(r'[0-9a-fA-F]{2}', results.output[0]).group()
            print(f'Dist: {distributed_points}')
        else:
            await ctx.reply(f'You must allocate all attribute points in order to claim prestige points! (Missing Dist)')
            return

        results = runRcon(f'sql select substr(hex(value),9,2) from properties where object_id = {character.id} '
                          f'and name = \'BP_ProgressionSystem_C.AttributePointsTotal\'')
        results.output.pop(0)
        if len(results.output) == 1:
            total_points = re.search(r'[0-9a-fA-F]{2}', results.output[0]).group()
            print(f'Total: {total_points}')
        else:
            await ctx.reply(f'You must allocate all attribute points in order to claim prestige points! (Missing Total)')
            return

        results = runRcon(f'sql select substr(hex(value),9,2) from properties where object_id = {character.id} '
                          f'and name = \'BP_ProgressionSystem_C.AttributePointsUndistributed\'')
        print(f'Undist result: {results.output}')
        results.output.pop(0)
        print(f'Len: {len(results.output)} Popped: {results.output}')
        if len(results.output) == 1:
            undistributed_points = re.search(r'[0-9a-fA-F]{2}', results.output[0]).group()
            print(f'Undist: {undistributed_points}')
            if int(undistributed_points, 16) > 0:
                await ctx.reply(f'You must allocate all attribute points in order to claim prestige points! (Undist Points)')
                return
        else:
            await ctx.reply(f'You must allocate all attribute points in order to claim prestige points! (Missing Undist)')
            return

        points = get_prestige_points(character)
        if not points:
            await ctx.reply(f'`{character.char_name}` has no prestige points to claim!\n')
            return

        if int(distributed_points, 16) > int(total_points, 16):
            await ctx.reply(f'`{character.char_name}` is entitled to `{points}` total prestige points.\n\n'
                            f'To claim them, you must use a Potion of Bestial Memory to reset your attributes '
                            f'and then distribute all of the points!')
            return

        if distributed_points == total_points and undistributed_points == '00':
            query = (f'sql update properties set value = x\'00000000{points:02x}000000\' '
                     f'where object_id = {character.id} and name = \'BP_ProgressionSystem_C.AttributePointsUndistributed\'')
            print(query)
            runRcon(query)
            # run_console_command_by_name(character.char_name, f'addundistributedattributepoints {points}')
            # print(f'You have {get_prestige_points(character)} prestige points in total.')
            await ctx.reply(f'`{character.char_name}` claimed `{points}` extra attribute points from Prestige!.\n')
            return
        return

    @commands.command(name='carryover')
    @commands.has_any_role('Admin', 'Moderator', 'BuildHelper')
    async def carryover(self, ctx, feature: str):
        """
        Transfers all custom features from your old character to your new one

        Parameters
        ----------
        ctx
        feature
            bank | fomo | professions

        """

        prev_character = last_season_char(ctx.message.author.id)
        if not prev_character:
            await ctx.reply(f'No season {PREVIOUS_SEASON} character registered to player {ctx.author.mention}! '
                            f'To carry over from a previous season character, you must have created a character '
                            f'in the previous season.')
            return
        current_character = is_registered(ctx.message.author.id)
        if not current_character:
            await ctx.reply(f'No season {CURRENT_SEASON} character registered to player {ctx.author.mention}! '
                            f'To carry over from a previous season character, you must have first '
                            f'created and registered your Season {CURRENT_SEASON} character.')
        else:
            if get_rcon_id(prev_character.char_name) or get_rcon_id(current_character.char_name):
                outputString = (f'Both characters `{prev_character.char_name}` and `{current_character.char_name}` '
                                f'must be offline to transfer feats!')
                await ctx.reply(outputString)
                return
            else:
                match feature.lower():
                    case 'bank' | 'eldarium':
                        old_balance = get_balance(prev_character, PREVIOUS_SEASON)
                        if old_balance:
                            eld_transaction(prev_character, f'Season {PREVIOUS_SEASON} Carryover Withdrawal',
                                            -old_balance, season=PREVIOUS_SEASON)
                            eld_transaction(current_character, f'Season {PREVIOUS_SEASON} Carryover Deposit',
                                            old_balance, season=CURRENT_SEASON)
                            await ctx.reply(f'`{old_balance}` Decaying Eldarium has been transferred from '
                                            f'Season {PREVIOUS_SEASON} character `{prev_character.char_name}` '
                                            f'to Season {CURRENT_SEASON} character `{current_character.char_name}`.\n\n')
                        else:
                            await ctx.reply(f'Season {PREVIOUS_SEASON} character `{prev_character.char_name}` has '
                                            f'`0` Decaying Eldarium in their bank.')
                            return
                    case 'fomo' | 'feats' | 'feat' | 'fomofeats':
                        db_query(True, f'insert or replace into featclaim '
                                       f'select {CURRENT_SEASON}, {current_character.id}, feat_id from featclaim '
                                       f'where char_id = {prev_character.id} and season = {PREVIOUS_SEASON} '
                                       f'and feat_id in ( select feat_id from fomo_feats );')
                        restored_feats = db_query(False, f'select featclaim.feat_id, valid_feats.feat_name '
                                                         f'from featclaim '
                                                         f'left join valid_feats on featclaim.feat_id = valid_feats.feat_id '
                                                         f'where featclaim.char_id = {current_character.id} '
                                                         f'and featclaim.season = {CURRENT_SEASON} '
                                                         f'and featclaim.feat_id in ( select feat_id from fomo_feats )')
                        await ctx.reply(f'FOMO Feats `{restored_feats}` have been transferred from '
                                        f'`{prev_character.char_name}` to `{current_character.char_name}`. '
                                        f'Log in to your new character, then use `v/featrestore` to learn them.')
                        return
                    case 'professions' | 'profession':
                        db_query(True,f'delete from character_progression '
                                       f'where char_id = {current_character.id} and season = {CURRENT_SEASON}')
                        db_query(True,f'delete from factions '
                                       f'where char_id = {current_character.id} and season = {CURRENT_SEASON}')

                        query = (f'insert or replace into character_progression '
                                 f'select {current_character.id}, {CURRENT_SEASON}, profession, tier, current_experience, '
                                 f'turn_ins_this_cycle from character_progression '
                                 f'where char_id = {prev_character.id} and season = {PREVIOUS_SEASON}')
                        print(f'query: {query}')
                        db_query(True, f'{query}')

                        query = (f'insert or replace into factions '
                                 f'select {current_character.id}, {CURRENT_SEASON}, faction, current_favor, lifetime_favor '
                                 f'from factions '
                                 f'where char_id = {prev_character.id} and season = {PREVIOUS_SEASON}')
                        db_query(True,f'{query}')

                        await ctx.send(f'Transferred Profession experience and tiers from Season {PREVIOUS_SEASON} '
                                       f'to Season {CURRENT_SEASON} for `{current_character.char_name}`\n\n'
                                       f'T4 and T5 abilities that were unlocked can be used immediately. '
                                       f'To get crafting recipes back, you must turn in one item to each profession,'
                                       f' then use `v/featrestore`.')
                        return
            return
    #
    # @commands.command(name='carryoverprofessions')
    # @commands.has_any_role('Admin', 'Moderator')
    # async def carryoverprofessions(self, ctx):
    #     """
    #
    #     Parameters
    #     ----------
    #     ctx
    #
    #     Returns
    #     -------
    #
    #     """
    #     character = is_registered(ctx.author.id)
    #
    #     results = db_query(True,
    #                        f'insert or replace into character_progression '
    #                        f'select char_id, {CURRENT_SEASON}, profession, tier, current_experience, '
    #                        f'turn_ins_this_cycle from character_progression '
    #                        f'where char_id = {character.id} and season = {PREVIOUS_SEASON}')
    #
    #     if results:
    #         await ctx.send(f'Transferred Profession experience and tiers from Season {PREVIOUS_SEASON} '
    #                        f'to Season {CURRENT_SEASON} for `{character.char_name}`\n\n'
    #                        f'T4 and T5 abilities that were unlocked can be used immediately. To get crafting recipes '
    #                        f'back, you must turn in one item to each profession then use `v/featrestore`.')
    #     else:
    #         await ctx.send(f'Error updating Profession details for {character.char_name}')
    #     return

# runRcon(f'sql insert into item_inventory where (select ')

# Check if account has a registered character in season 7
#if so:
# write season, source character ID and discord ID to rollover_characters table, target character ID blank
# prepare list of feats that can be rolled over
# rcon sql query for inv_type 6 matching character ID
# parse response and write matching feats to the rollover_feats table (discord ID + feat ID)
# disassociate the character from the player's account
# end
#
# player creates new character
# player registers new character, selects REROLL option
# registration finds character ID as normal, handles registration as normal
# writes target character ID to rollover_characters table
# writes new entries in character_progression table to carryover progress old to new
# duplicates the old character's entries in feat_claim to the target character's ID
# writes entries from rollover_feats into feat_claim table for the new target character ID

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Reroll(bot))
