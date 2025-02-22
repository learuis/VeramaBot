import os

from discord.ext import commands

from cogs.FeatClaim import grant_feat
from functions.common import int_epoch_time, get_bot_config, set_bot_config, is_registered, get_single_registration, \
    flatten_list, get_registration, get_rcon_id
from functions.externalConnections import db_query, runRcon
from dotenv import load_dotenv

load_dotenv('data/server.env')
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))
PROFESSION_CHANNEL = int(os.getenv('PROFESSION_CHANNEL'))
PROFESSION_MESSAGE = int(os.getenv('PROFESSION_MESSAGE'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))


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
    selection_tier = 0

    if tier == 0:
        selection_tier = 1
    elif tier == 5:
        selection_tier = 4
    else:
        selection_tier = tier

    # print(f'Getting objective for {profession} / tier {tier}')
    current_objective = db_query(False,
                                 f'select item_id, item_name from profession_objectives '
                                 f'where profession like \'%{profession}%\' and tier = {selection_tier} limit 1')
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
                     f'and profession like \'%{profession}%\' '
                     f'and season = {CURRENT_SEASON} '
                     f'limit 1')
    if not query:
        db_query(True,
                 f'insert into character_progression '
                 f'(char_id, season, profession, tier, current_experience, turn_ins_this_cycle) '
                 f'values ({char_id},{CURRENT_SEASON}, \'{profession}\', 0, 0, 0)')
        # print(f'Created progression record for {char_id} / {profession}')
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
        # print(f'Created faction record for {char_id} / {faction}')
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
    profession_xp_mult = int(get_bot_config(f'{profession.casefold()}_xp_multiplier'))

    if not tier:
        earned_xp = profession_xp_mult
    else:
        earned_xp = tier * profession_xp_mult

    db_query(True,
             f'update character_progression set current_experience = ( '
             f'select current_experience + {earned_xp} from character_progression '
             f'where char_id = {char_id} and profession like \'%{profession}%\' and season = {CURRENT_SEASON}), '
             f'turn_ins_this_cycle = ('
             f'select turn_ins_this_cycle + 1 from character_progression '
             f'where char_id = {char_id} and profession like \'%{profession}%\'),'
             f'season = {CURRENT_SEASON} '
             f'where char_id = {char_id} and profession like \'%{profession}%\' and season = {CURRENT_SEASON}')
    results = db_query(False,
                       f'select current_experience from character_progression '
                       f'where char_id = {char_id} and profession like \'%{profession}%\' '
                       f'and season = {CURRENT_SEASON} limit 1')
    results = flatten_list(results)
    xp_total = results[0]
    # print(f'{char_name} has {xp_total} xp in tier {tier} {profession}')

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

    if 0 <= turn_in_amount < tier_2_xp:
        new_tier = 1
    elif tier_2_xp <= turn_in_amount < tier_3_xp:
        new_tier = 2
    elif tier_3_xp <= turn_in_amount < tier_4_xp:
        new_tier = 3
    elif tier_4_xp <= turn_in_amount < tier_5_xp:
        new_tier = 4
    elif tier_5_xp <= turn_in_amount:
        new_tier = 5
    else:
        # print(f'Error in calculating next tier for {char_id} - tier {tier} xp {turn_in_amount}')
        return

    if tier == new_tier:
        # print(f'No tier increase is due to {char_id} - tier {tier} xp {turn_in_amount}')
        return

    db_query(True,
             f'update character_progression set tier = {new_tier}, turn_ins_this_cycle = 0 '
             f'where char_id = {char_id} and season = {CURRENT_SEASON} and profession like \'%{profession}%\'')
    registration = get_single_registration(char_name)

    outputString += f'<@{registration[2]}>:\n`{char_name}` - `{profession}` tier has increased to `T{new_tier}`!\n'
    outputString += f'Your remaining deliveries for this cycle have been reset to `{cycle_limit}`.\n'
    outputString += f'You have unlocked the following {profession} recipes (claim with with `v/featrestore`)\n'

    feats_to_grant = db_query(False, f'select feat_id, feat_name from profession_rewards '
                                     f'where turn_in_amount <= {turn_in_amount} and profession like \'%{profession}%\' '
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
        # print(f'Created faction record for {char_id} / {faction}')

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


async def updateProfessionBoard(message, displayOnly: bool = False):

    if int(get_bot_config(f'disable_professions')) == 1:
        # print(f'Skipping profession loop, server in maintenance mode')
        return False

    last_profession_update = int(get_bot_config(f'last_profession_update'))
    profession_update_interval = int(get_bot_config(f'profession_update_interval'))
    profession_community_goal = int(get_bot_config(f'profession_community_goal'))
    profession_community_goal_desc = str(get_bot_config(f'profession_community_goal_desc'))
    next_update = last_profession_update + profession_update_interval
    profession_list = ['Blacksmith', 'Armorer', 'Tamer', 'Archivist']
    count = 0

    current_time = int_epoch_time()

    if current_time < next_update:
        displayOnly = True

    outputString = '__Requested Items (No uniques/gold borders)__\n'

    profession_tier_list = db_query(False, f'select distinct profession, tier '
                                           f'from profession_item_list')
    for record in profession_tier_list:
        (profession, tier) = record

        if (int(count) % 4) + 1 == 1:
            outputString += f'**{profession}**\n'

        if not displayOnly:
            itemList = db_query(False,
                                f'select item_id, item_name from profession_item_list '
                                f'where profession like \'%{profession}%\''
                                f'and tier = \'{tier}\' and item_id not in ( select item_id from profession_objectives )'
                                f'order by RANDOM() limit 1')
        else:
            itemList = db_query(False,
                                f'select item_id, item_name from profession_objectives '
                                f'where tier = \'{tier}\' and profession like \'%{profession}%\' limit 1')
        for item in itemList:
            (item_id, item_name) = item

            if not displayOnly:
                db_query(True, f'insert or replace into profession_objectives '
                               f'(profession,tier,item_id,item_name) '
                               f'values (\'{profession}\', {tier}, {item_id}, \'{item_name}\')')
                db_query(True, f'update character_progression set turn_ins_this_cycle = 0')

            outputString += f'T{tier}: `{item_name}`\n'

            # print(f'{count}')
            count += 1
            if int(count) % 4 == 0:
                outputString += f'\n'

            # print(f'Updated {profession} Tier {tier}: {item_name}')

    if not displayOnly:
        set_bot_config(f'last_profession_update', current_time)
        next_update = current_time + profession_update_interval

    all_total = db_query(False, f'select sum(current_experience) from character_progression '
                                f'where season = {CURRENT_SEASON}')
    all_total = flatten_list(all_total)

    totals = db_query(False, f'select profession, sum(current_experience) '
                             f'from character_progression where season = {CURRENT_SEASON} '
                             f'group by profession order by sum(current_experience) desc')
    outputString += f'__Serverwide:__\n'
    for record in totals:
        outputString += f'`{record[0]}` - `{record[1]}`\n'
    outputString += f'`Total` - `{all_total[0]}`\n\n'

    outputString += (f'__Goal:__\n`{all_total[0]}` / `{profession_community_goal}` - '
                     f'{profession_community_goal_desc}\n')

    # print(f'make leaderboard')

    for item in profession_list:

        query = f'select char_id, current_experience from character_progression '\
                f'where season = {CURRENT_SEASON} and profession like \'%{item}%\' '\
                f'order by current_experience desc limit 3'
        # print(f'{query}')
        profession_leaders = db_query(False, f'{query}')
        # print(f'{profession_leaders}')
        if not profession_leaders:
            continue
        else:
            outputString += f'\n__{item} Leaderboard:__\n| '

            for character in profession_leaders:
                char_details = get_registration('', int(character[0]))
                char_details = flatten_list(char_details)
                # print(f'{char_details}')
                char_name = char_details[1]

                outputString += f'`{char_name}` - `{character[1]}` | '
                # print(f'outputstring is {outputString}')

    # print(f'timestamps')
    if not displayOnly:
        outputString += (f'\n\nUpdated hourly.\n'
                         f'Updated at: <t:{current_time}> in your timezone'
                         f'\nNext: <t:{next_update}:f> in your timezone\n')
    else:
        outputString += (f'\n\nUpdated hourly.\n'
                         f'Updated at: <t:{last_profession_update}> in your timezone'
                         f'\nNext: <t:{next_update}:f> in your timezone\n')

    # print(f'outputstring is {len(outputString)} characters')

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
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
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
        target_list = []

        character = is_registered(ctx.author.id)
        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        for profession in profession_list:
            profession_details = get_profession_tier(character.id, profession)
            if profession_details.tier == 0:
                config_value = f'profession_t2_xp'
                xp_target = int(get_bot_config(f'{config_value}'))
            elif profession_details.tier == 5:
                xp_target = f'--'
            else:
                config_value = f'profession_t{profession_details.tier + 1}_xp'
                xp_target = int(get_bot_config(f'{config_value}'))

            outputString += (f'`{profession_details.profession}` - `T{profession_details.tier}` '
                             f'XP: `{profession_details.current_experience}` / `{xp_target}` '
                             f'- Deliveries Remaining: '
                             f'`{cycle_limit - profession_details.turn_ins_this_cycle}`\n')

            target_item = get_current_objective(profession_details.profession, profession_details.tier)

            outputString += f'Target Item: `{target_item.item_name}`\n'

            ranking = db_query(False, f'select char_id from character_progression '
                                      f'where profession like \'%{profession_details.profession}%\' '
                                      f'and season = {CURRENT_SEASON} order by current_experience desc')
            ranking = flatten_list(ranking)
            # print(f'{ranking}')
            for index, rank in enumerate(ranking):
                # print(f'{index + 1} {rank}')
                if int(rank) == character.id:
                    outputString += f'Server-wide Ranking: `{index + 1}`\n\n'

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

        results = db_query(True,
                           f'update character_progression '
                           f'set tier = {tier}, current_experience = {xp}, turn_ins_this_cycle = {turn_ins} '
                           f'where char_id = {char_id} and season = {CURRENT_SEASON} '
                           f'and profession = \'{profession.capitalize()}\'')

        if results:
            await ctx.send(f'Updated Profession details for '
                           f'`{char_name}`: {profession.capitalize()} Tier {tier} XP {xp} Deliveries {turn_ins}')
        else:
            await ctx.send(f'Error updating Profession details for {char_name}')
        return

    @commands.command(name='carryoverprofessions')
    @commands.has_any_role('Admin', 'Moderator', 'Outcasts')
    async def carryoverprofessions(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)

        results = db_query(True,
                           f'insert into character_progression '
                           f'select char_id, {CURRENT_SEASON}, profession, tier, current_experience, '
                           f'turn_ins_this_cycle from character_progression '
                           f'where char_id = {character.id} and season = {PREVIOUS_SEASON}')

        if results:
            await ctx.send(f'Transferred Profession experience from Season {PREVIOUS_SEASON} '
                           f'to Season {CURRENT_SEASON} for `{character.char_name}`')
        else:
            await ctx.send(f'Error updating Profession details for {character.char_name}')
        return

    @commands.command(name='refreshprofessions')
    @commands.has_any_role('Admin', 'Moderator')
    async def refreshprofessions(self, ctx, update: bool = False):
        """

        Parameters
        ----------
        ctx
        update
            Specify True if the board should be refreshed

        Returns
        -------

        """
        if update:
            set_bot_config(f'last_profession_update', f'0')
            await ctx.reply(f'Profession Update clock reset. Objectives will be refreshed within 1 minute.')
        else:
            channel = ctx.author.guild.get_channel(PROFESSION_CHANNEL)
            message = await channel.fetch_message(PROFESSION_MESSAGE)
            await updateProfessionBoard(message, True)
            await ctx.reply(f'Profession display has been updated without making changes.')

    @commands.command(name='professionitem')
    @commands.has_any_role('Admin', 'Moderator')
    async def professionitem(self, ctx, input_name: str, profession: str = 'all', quantity: int = 1):
        """ Give player the current profession items for their tier for testing/replacement

        Parameters
        ----------
        ctx
        input_name
        profession
        quantity

        Returns
        -------

        """
        registration = get_single_registration(f'{input_name}')

        if not registration:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return
        else:
            (char_id, char_name, discord_id) = registration
            profession = profession.capitalize()
            profession_list = ['Blacksmith', 'Armorer', 'Tamer', 'Archivist']

            if 'all' in profession:
                for profession in profession_list:
                    prof_data = get_profession_tier(char_id, profession)
                    objective = get_current_objective(prof_data.profession, prof_data.tier)

                    rcon_id = get_rcon_id(char_name)
                    if rcon_id:
                        runRcon(f'con {rcon_id} spawnitem {objective.item_id} {quantity}')
                        await ctx.send(f'Gave `{char_name}` `{quantity}` `{objective.item_name}` '
                                       f'for `{objective.profession}` Tier `{objective.tier}`')
            elif profession in profession_list:
                prof_data = get_profession_tier(char_id, profession)
                objective = get_current_objective(prof_data.profession, prof_data.tier)

                rcon_id = get_rcon_id(char_name)
                if rcon_id:
                    runRcon(f'con {rcon_id} spawnitem {objective.item_id} {quantity}')
                    await ctx.send(f'Gave `{char_name}` `{quantity}` `{objective.item_name}` '
                                   f'for `{objective.profession}` Tier `{objective.tier}`')
            else:
                await ctx.send(f'Invalid profession specified. Must use Blacksmith, Armorer, Tamer, Archivist')

    @commands.command(name='professiondetails')
    @commands.has_any_role('Admin', 'Moderator')
    async def professiondetails(self, ctx):
        """ Displays the current profession details

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        channel = ctx.author.guild.get_channel(PROFESSION_CHANNEL)
        message = await channel.fetch_message(PROFESSION_MESSAGE)

        await ctx.send(content=message.content)


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Professions(bot))
