import os
from discord.ext import commands

from cogs.EldariumBank import get_balance, eld_transaction
from functions.common import is_registered, get_rcon_id, last_season_char, get_bot_config

from dotenv import load_dotenv

from functions.externalConnections import runRcon, db_query

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))

class Reroll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reroll')
    @commands.has_any_role('Admin', 'Moderator')
    async def reroll(self, ctx):
        """
        Disassociates your current season character from your account, allowing you to create a new one.

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

        runRcon(f'sql update account set user = \'{character.char_name}\' where id in ( '
                f'select c.playerId from characters as c where c.id = {character.id} )')
        await ctx.reply(f'Removed association to Season {PREVIOUS_SEASON} character `{character.char_name}` '
                        f'from {ctx.author.mention}. '
                        f'You must create and register your new character before transferring feats!')

    @commands.command(name='transferfeats')
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
    async def transferfeats(self, ctx):
        """
        Transfers learned feats from your previous season character to your current season character

        Parameters
        ----------
        ctx

        """
        prev_character = last_season_char(ctx.message.author.id)
        if not prev_character:
            await ctx.reply(f'No season {PREVIOUS_SEASON} character registered to player {ctx.author.mention}! '
                            f'To transfer feats from a previous season character, you must have created a character '
                            f'in the previous season.')
            return
        current_character = is_registered(ctx.message.author.id)
        if not current_character:
            await ctx.reply(f'No season {CURRENT_SEASON} character registered to player {ctx.author.mention}! '
                            f'To transfer feats from a previous season character, you must have first '
                            f'created and registered your Season {CURRENT_SEASON} character.')
        else:
            if get_rcon_id(prev_character.char_name) or get_rcon_id(current_character.char_name):
                outputString = (f'Both characters `{prev_character.char_name}` and `{current_character.char_name}` '
                                f'must be offline to transfer feats!')
                await ctx.reply(outputString)
                return
            else:
                db_query(True, f'insert into featclaim '
                               f'select {CURRENT_SEASON}, {current_character.id}, feat_id from featclaim '
                               f'where char_id = {prev_character.id} and season = {PREVIOUS_SEASON};')
                await ctx.reply(f'Feats have been transferred from `{prev_character.char_name}` '
                                f'to `{current_character.char_name}`. Log in to your new character, '
                                f'then use `v/featrestore` to learn them.')
            return


    @commands.command(name='carryover')
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
    async def carryover(self, ctx):
        """
        Transfers all custom features from your old character to your new one

        Parameters
        ----------
        ctx

        """
        prev_character = last_season_char(ctx.message.author.id)
        if not prev_character:
            await ctx.reply(f'No season {PREVIOUS_SEASON} character registered to player {ctx.author.mention}! '
                            f'To transfer feats from a previous season character, you must have created a character '
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
                db_query(True, f'insert into featclaim '
                               f'select {CURRENT_SEASON}, {current_character.id}, feat_id from featclaim '
                               f'where char_id = {prev_character.id} and season = {PREVIOUS_SEASON};')

                old_balance = get_balance(prev_character.id)
                eld_transaction(current_character.id, f'Season {PREVIOUS_SEASON} Carryover', old_balance)

                db_query(True,f'delete from character_progression '
                               f'where char_id = {current_character.id} and season = {CURRENT_SEASON}')
                db_query(True,f'delete from factions '
                               f'where char_id = {current_character.id} and season = {CURRENT_SEASON}')

                db_query(True,
                         f'insert into character_progression '
                               f'select char_id, {CURRENT_SEASON}, profession, tier, current_experience, '
                               f'turn_ins_this_cycle from character_progression '
                               f'where char_id = {current_character.id} and season = {PREVIOUS_SEASON}')
                db_query(True,
                         f'insert into factions '
                               f'select char_id, {CURRENT_SEASON}, faction, current_favor, lifetime_favor '
                               f'from factions '
                               f'where char_id = {current_character.id} and season = {PREVIOUS_SEASON}')

                await ctx.reply(f'{old_balance} Decaying Eldarium has been transferred from Season {PREVIOUS_SEASON} character `{prev_character.char_name}` '
                                f'to Season {CURRENT_SEASON} character `{current_character.char_name}`.\n\n'
                                f'Feats learned from FOMO Events and Professions have been transferred from '
                                f'Season {PREVIOUS_SEASON} character `{prev_character.char_name}` '
                                f'to Season {CURRENT_SEASON} character `{current_character.char_name}`. '
                                f'Log in to your new character, then use `v/featrestore` to learn them.')
            return


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
