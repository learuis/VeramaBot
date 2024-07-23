import os

from discord.ext import commands

from functions.common import int_epoch_time, get_bot_config, set_bot_config, is_registered
from functions.externalConnections import db_query
from dotenv import load_dotenv

load_dotenv('data/server.env')
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))


class ProfessionTier:
    def __init__(self):
        self.char_id = 0
        self.profession = ''
        self.tier = 0
        self.current_experience = 0

class ProfessionObjective:
    def __init__(self):
        self.profession = ''
        self.tier = 0
        self.item_id = 0
        self.item_name = ''

def get_current_objective(profession, tier):

    objective = ProfessionObjective()

    print(f'Getting objective for {profession} / tier {tier}')
    current_objective = db_query(False,
                                 f'select item_id, item_name from profession_objectives '
                                 f'where profession = \'{profession}\' and tier = {tier} limit 1')
    for item in current_objective:
        objective.profession = profession
        objective.tier = tier
        (objective.item_id, objective.item_name) = item

    return objective


def get_profession_tier(char_id, profession):

    player_profession_tier = ProfessionTier()

    query = db_query(False,
                     f'select char_id, profession, tier, current_experience from character_progression '
                     f'where char_id = {char_id} '
                     f'and profession = \'{profession}\' '
                     f'and season = {CURRENT_SEASON} '
                     f'limit 1')
    if not query:
        db_query(True,
                 f'insert into character_progression '
                 f'(char_id, season, profession, tier, current_experience) '
                 f'values ({char_id},{CURRENT_SEASON}, \'{profession}\', 1, 0)')
        print(f'Created progression record for {char_id} / {profession}')
        player_profession_tier.char_id = char_id
        player_profession_tier.profession = profession
        player_profession_tier.tier = 1
        player_profession_tier.current_experience = 0
        return player_profession_tier

    for record in query:
        (player_profession_tier.char_id,
         player_profession_tier.profession,
         player_profession_tier.tier,
         player_profession_tier.current_experience) = record

    return player_profession_tier


def give_profession_xp(char_id, profession):
    db_query(True,
             f'update character_progression set current_experience = ( '
             f'select current_experience + 1 from character_progression '
             f'where char_id = {char_id} and profession = \'{profession}\') '
             f'where char_id = {char_id} and profession = \'{profession}\'')
    results = db_query(False,
                       f'select current_experience from character_progression '
                       f'where char_id = {char_id} and profession = \'{profession}\' limit 1')
    xp_total = results[0]

    return xp_total


async def updateProfessionBoard(message, bot):
    last_profession_update = int(get_bot_config(f'last_profession_update'))
    profession_update_interval = int(get_bot_config(f'profession_update_interval'))
    next_update = last_profession_update + profession_update_interval

    current_time = int_epoch_time()

    if current_time < next_update:
        print(f'Skipping profession update, too soon')
        return False

    outputString = '__Current Profession Turn-In Items:__\n'

    profession_tier_list = db_query(False, f'select distinct profession, tier '
                                           f'from profession_item_list')
    for record in profession_tier_list:
        (profession, tier) = record

        itemList = db_query(False,
                            f'select item_id, item_name from profession_item_list '
                            f'where profession = \'{profession}\''
                            f'and tier = \'{tier}\' '
                            f'order by RANDOM() limit 1')
        for item in itemList:
            (item_id, item_name) = item

            db_query(True, f'insert or replace into profession_objectives '
                           f'(profession,tier,item_id,item_name) '
                           f'values (\'{profession}\', {tier}, {item_id}, \'{item_name}\')')
            outputString += f'{profession} Tier {tier}: `{item_name}`\n'
            print(f'Updated {profession} Tier {tier}: {item_name}')

    set_bot_config(f'last_profession_update', current_time)
    next_update = current_time + profession_update_interval
    outputString += f'Next update: <t:{next_update}:f> in your timezone'

    await message.edit(content=f'{outputString}')


class Professions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='profession_prep')
    @commands.is_owner()
    async def rp_prep(self, ctx: commands.Context):
        await ctx.send(f'Profession Info here!')
        return

    @commands.command(name='profession')
    @commands.has_any_role('Admin', 'Moderator')
    async def profession(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        profession_details = ProfessionTier()
        profession_list = ['Blacksmith', 'Armorer', 'Tamer', 'Archivist']
        outputString = ''

        character = is_registered(ctx.author.id)
        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        for profession in profession_list:
            profession_details = get_profession_tier(character.id, profession)
            outputString += (f'{profession_details.profession} - Tier {profession_details.tier}: '
                             f'Current XP: {profession_details.current_experience} / XXX \n')

        await ctx.reply(f'Profession Details for `{character.char_name}`:\n'
                        f'{outputString}')
@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Professions(bot))
