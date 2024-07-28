import os

from discord.ext import commands

from cogs.FeatClaim import grant_feat
from functions.common import int_epoch_time, get_bot_config, set_bot_config, is_registered, get_single_registration, \
    flatten_list
from functions.externalConnections import db_query
from dotenv import load_dotenv

load_dotenv('data/server.env')
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))

class ProfessionTier:
    def __init__(self):
        self.char_id = 0
        self.profession = ''
        self.tier = 0
        self.current_experience = 0
        self.turn_ins_this_cycle = 0


class ProfessionObjective:
    def __init__(self):
        self.profession = ''
        self.tier = 0
        self.item_id = 0
        self.item_name = ''


class Favor:
    def __init__(self):
        self.char_id = 0
        self.faction = ''
        self.current_favor = 0
        self.lifetime_favor = 0


def get_current_objective(profession, tier):
    objective = ProfessionObjective()

    if tier == 0:
        tier = 1

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
                     f'select char_id, profession, tier, current_experience, turn_ins_this_cycle '
                     f'from character_progression '
                     f'where char_id = {char_id} '
                     f'and profession = \'{profession}\' '
                     f'and season = {CURRENT_SEASON} '
                     f'limit 1')
    if not query:
        db_query(True,
                 f'insert into character_progression '
                 f'(char_id, season, profession, tier, current_experience, turn_ins_this_cycle) '
                 f'values ({char_id},{CURRENT_SEASON}, \'{profession}\', 0, 0, 0)')
        print(f'Created progression record for {char_id} / {profession}')
        player_profession_tier.char_id = char_id
        player_profession_tier.profession = profession
        player_profession_tier.tier = 0
        player_profession_tier.current_experience = 0
        player_profession_tier.turn_ins_this_cycle = 0
        return player_profession_tier

    for record in query:
        (player_profession_tier.char_id,
         player_profession_tier.profession,
         player_profession_tier.tier,
         player_profession_tier.current_experience,
         player_profession_tier.turn_ins_this_cycle) = record

    return player_profession_tier


def get_favor(char_id, faction):
    favor_values = Favor()

    query = db_query(False,
                     f'select char_id, faction, current_favor, lifetime_favor from factions '
                     f'where char_id = {char_id} '
                     f'and faction = \'{faction}\' '
                     f'and season = {CURRENT_SEASON} '
                     f'limit 1')

    if not query:
        db_query(True,
                 f'insert into factions '
                 f'(char_id, season, faction, current_favor, lifetime_favor) '
                 f'values ({char_id},{CURRENT_SEASON}, \'{faction}\', 0, 0)')
        print(f'Created faction record for {char_id} / {faction}')
        favor_values.char_id = char_id
        favor_values.faction = faction
        favor_values.current_favor = 0
        favor_values.lifetime_favor = 0

        return favor_values

    for record in query:
        (favor_values.char_id,
         favor_values.faction,
         favor_values.current_favor,
         favor_values.lifetime_favor) = record

    return favor_values


async def give_profession_xp(char_id, char_name, profession, tier, bot):

    db_query(True,
             f'update character_progression set current_experience = ( '
             f'select current_experience + 1 from character_progression '
             f'where char_id = {char_id} and profession = \'{profession}\'), '
             f'turn_ins_this_cycle = ('
             f'select turn_ins_this_cycle + 1 from character_progression '
             f'where char_id = {char_id} and profession = \'{profession}\') '
             f'where char_id = {char_id} and profession = \'{profession}\'')
    results = db_query(False,
                       f'select current_experience from character_progression '
                       f'where char_id = {char_id} and profession = \'{profession}\' limit 1')
    results = flatten_list(results)
    xp_total = results[0]
    print(f'{char_name} has {xp_total} xp in tier {tier} {profession}')

    await profession_tier_up(profession, tier, xp_total, char_id, char_name, bot)

    return

async def profession_tier_up(profession, tier, turn_in_amount, char_id, char_name, bot):
    channel = bot.get_channel(OUTCASTBOT_CHANNEL)
    outputString = ''

    cycle_limit = int(get_bot_config(f'profession_cycle_limit'))
    tier_2_xp = int(get_bot_config(f'profession_t2_xp'))
    tier_3_xp = int(get_bot_config(f'profession_t3_xp'))
    tier_4_xp = int(get_bot_config(f'profession_t4_xp'))
    tier_5_xp = int(get_bot_config(f'profession_t5_xp'))
    tier_threshholds = [1, tier_2_xp, tier_3_xp, tier_4_xp, tier_5_xp]

    print(f'Checking if {turn_in_amount} is in {tier_threshholds}')
    if turn_in_amount in tier_threshholds:
        print(f'it is!')
        db_query(True,
                 f'update character_progression set tier = {tier + 1}, turn_ins_this_cycle = 0 '
                 f'where char_id = {char_id} and season = {CURRENT_SEASON} and profession = \'{profession}\'')
        registration = get_single_registration(char_name)

        outputString += f'<@{registration[2]}>:\n`{char_name}` - `{profession}` tier has increased to `T{tier+1}`!\n'
        outputString += f'Your remaining deliveries for this cycle have been reset to `{cycle_limit}`.\n'
        outputString += f'You have unlocked the following {profession} recipes (claim with with `v/featrestore`)\n'

        feats_to_grant = db_query(False, f'select feat_id, feat_name from profession_rewards '
                                         f'where turn_in_amount <= {turn_in_amount} and profession = \'{profession}\' '
                                         f'order by turn_in_amount desc')
        for feat in feats_to_grant:
            grant_feat(char_id, char_name, feat[0])
            outputString += f'{feat[1]}\n'

        await channel.send(f'{outputString}')

    return

def give_favor(char_id, faction, tier):
    query = db_query(False,
                     f'select char_id, faction, current_favor, lifetime_favor from factions '
                     f'where char_id = {char_id} '
                     f'and faction = \'{faction}\' '
                     f'and season = {CURRENT_SEASON} '
                     f'limit 1')
    if not query:
        db_query(True,
                 f'insert into factions '
                 f'(char_id, season, faction, current_favor, lifetime_favor) '
                 f'values ({char_id},{CURRENT_SEASON}, \'{faction}\', {tier}, {tier})')
        print(f'Created faction record for {char_id} / {faction}')

    db_query(True,
             f'update factions set current_favor = ( '
             f'select current_favor + {tier} from factions '
             f'where char_id = {char_id} and faction = \'{faction}\') '
             f'where char_id = {char_id} and faction = \'{faction}\'')
    db_query(True,
             f'update factions set lifetime_favor = ( '
             f'select lifetime_favor + {tier} from factions '
             f'where char_id = {char_id} and faction = \'{faction}\') '
             f'where char_id = {char_id} and faction = \'{faction}\'')
    results = db_query(False,
                       f'select current_favor from factions '
                       f'where char_id = {char_id} and faction = \'{faction}\' limit 1')
    favor_total = results[0]

    return favor_total


async def updateProfessionBoard(message):
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
            db_query(True, f'update character_progression set turn_ins_this_cycle = 0')
            outputString += f'{profession} Tier {tier}: `{item_name}`\n'
            print(f'Updated {profession} Tier {tier}: {item_name}')

    set_bot_config(f'last_profession_update', current_time)
    next_update = current_time + profession_update_interval
    outputString += (f'\nLast update: <t:{current_time}> in your timezone'
                     f'\nNext update: <t:{next_update}:f> in your timezone')

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
        profession_list = ['Blacksmith', 'Armorer', 'Tamer', 'Archivist']
        cycle_limit = int(get_bot_config(f'profession_cycle_limit'))
        outputString = ''

        character = is_registered(ctx.author.id)
        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        for profession in profession_list:
            profession_details = get_profession_tier(character.id, profession)
            if profession_details.tier == 0:
                config_value = f'profession_t2_xp'
            elif profession_details.tier == 5:
                config_value = f'--'
            else:
                config_value = f'profession_t{profession_details.tier+1}_xp'
            print(f'getting config for {config_value}')
            xp_target = int(get_bot_config(config_value))

            outputString += (f'`{profession_details.profession}` - `T{profession_details.tier}` '
                             f'XP: `{profession_details.current_experience}` / `{xp_target}` '
                             f'- Deliveries Remaining: '
                             f'`{cycle_limit - profession_details.turn_ins_this_cycle}`\n')

        await ctx.reply(f'Profession Details for `{character.char_name}`:\n'
                        f'{outputString}')

    @commands.command(name='modifyprofession')
    @commands.has_any_role('Admin', 'Moderator')
    async def modifyprofession(self, ctx, char_name: str, profession: str, tier: int, xp: int, turn_ins: int):
        """

        Parameters
        ----------
        ctx
        char_name
        profession
        tier
        xp
        turn_ins

        Returns
        -------

        """
        registration_result = get_single_registration(char_name)
        (char_id, char_name, discord_id) = registration_result

        db_query(True,
                 f'update character_progression '
                 f'set tier = {tier}, current_experience = {xp}, turn_ins_this_cycle = {turn_ins} '
                 f'where char_id = {char_id} and season = {CURRENT_SEASON} and profession = \'{profession}\'')

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Professions(bot))
