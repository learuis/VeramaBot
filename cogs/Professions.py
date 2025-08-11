import os
import math
import random

from discord.ext import commands

from cogs.FeatClaim import grant_feat
from functions.common import int_epoch_time, get_bot_config, set_bot_config, is_registered, get_single_registration, \
    flatten_list, get_rcon_id, run_console_command_by_name, get_single_registration_new, \
    no_registered_char_reply, check_channel, eld_transaction, get_balance, get_slayer_target, get_notoriety, get_favor, \
    add_reward_record, get_treasure_target
from functions.externalConnections import db_query, runRcon
from dotenv import load_dotenv

load_dotenv('data/server.env')
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))
PROFESSION_CHANNEL = int(os.getenv('PROFESSION_CHANNEL'))
PROFESSION_MESSAGE = int(os.getenv('PROFESSION_MESSAGE'))


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

    # grant feats on every XP increase
    feats_to_grant = db_query(False, f'select feat_id, feat_name from profession_rewards '
                                     f'where turn_in_amount <= {xp_total} and profession like \'%{profession}%\' '
                                     f'order by turn_in_amount desc')
    for feat in feats_to_grant:
        grant_feat(char_id, char_name, feat[0])

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
    match profession.casefold():
        case 'blacksmith':
            if new_tier == 4:
                outputString += (f'**You have gained the ability to reforge weapons to scale with different attributes '
                                 f'with `v/reforge`. Use `v/help reforge` for an explanation.**\n')
            if new_tier == 5:
                outputString += (f'**You have gained the ability to repair all items with `v/repair`. '
                                 f'Use `v/help repair` for an explanation.**\n')
        case 'armorer':
            if new_tier == 4:
                outputString += (f'**You have gained the ability to trim armor weight to 0 with `v/trim`. '
                                 f'Use `v/help trim` for an explanation.**\n')
            if new_tier == 5:
                outputString += (f'**You have gained the ability to repair equipped armor with `v/repair`. '
                                 f'Use `v/help repair` for an explanation.**\n')
        case 'archivist':
            if new_tier == 4:
                outputString += (f'**You have gained the ability to enchant weapons with long-lasting effects '
                                 f'with `v/enchant`.  Use `v/help enchant` for an explanation.**\n')
            if new_tier == 5:
                outputString += (f'**You have gained the ability to research sigils with `v/research`. '
                                 f'Use `v/help research` for an explanation.**\n')
        case 'tamer':
            if new_tier == 3:
                outputString += (f'**You have gained the ability to breed rare offspring from animals '
                                 f'with `v/offspring`. Use `v/help offspring` for an explanation.**\n')
            if new_tier == 4:
                outputString += (f'**You have gained the ability to bond with an animal companion, increasing its damage significantly '
                                 f'with `v/animalbond`. Use `v/help animalbond` for an explanation.**\n')
            if new_tier == 5:
                outputString += (f'**You have gained the ability to train followers, granting them experience '
                                 f'with `v/train`. Use `v/help train` for an explanation.**\n')

    outputString += f'You have unlocked the following {profession} recipes (claim with with `v/featrestore`)\n'

    feats_to_grant = db_query(False, f'select feat_id, feat_name from profession_rewards '
                                     f'where turn_in_amount <= {turn_in_amount} and profession like \'%{profession}%\' '
                                     f'order by turn_in_amount desc')
    for feat in feats_to_grant:
        grant_feat(char_id, char_name, feat[0])
        outputString += f'{feat[1]}\n'

    await channel.send(f'{outputString}')

    return

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
    faction_list = ['Provisioner', 'Slayer']
    count = 0
    item_id_string = ''
    item_name_string = ''

    current_time = int_epoch_time()

    if current_time < next_update:
        displayOnly = True

    outputString = '__Requested Items (No uniques/gold borders)__\n'

    profession_tier_list = db_query(False, f'select distinct profession, tier '
                                           f'from profession_item_list order by profession, tier asc')
    for record in profession_tier_list:
        (profession, tier) = record

        if (int(count) % 4) + 1 == 1:
            outputString += f'**{profession}**\n'

        if not displayOnly:
            itemList = db_query(False,
                                f'select item_id, item_name from profession_item_list '
                                f'where profession like \'%{profession}%\''
                                f'and tier = \'{tier}\' and item_id not in ( select item_id from profession_objectives )'
                                f'order by RANDOM() limit 3')
        else:
            itemList = db_query(False,
                                f'select item_id, item_name from profession_objectives '
                                f'where tier = \'{tier}\' and profession like \'%{profession}%\' limit 1')
        for index, item in enumerate(itemList):
            # (item_id, item_name) = item
            if len(itemList) == 1:
                item_id_string += f'{item[0]}'
                item_name_string += f'`{item[1]}`'
                break
            elif index == len(itemList) - 1:
                item_id_string += f'{item[0]}'
                item_name_string += f'`{item[1]}`'
            else:
                item_id_string += f'{item[0]}, '
                item_name_string += f'`{item[1]}`, '

        outputString += f'T{tier}: {item_name_string}\n'

        item_name_string = item_name_string.replace('`', '')

        # print(f'{count}')
        count += 1
        if int(count) % 4 == 0:
            outputString += f'\n'

        if not displayOnly:
            db_query(True, f'insert or replace into profession_objectives '
                           f'(profession,tier,item_id,item_name) '
                           f'values (\'{profession}\', {tier}, \'{item_id_string}\', \'{item_name_string}\')')
            db_query(True, f'update character_progression set turn_ins_this_cycle = 0')

        item_id_string = ''
        item_name_string = ''

            # print(f'Updated {profession} Tier {tier}: {item_name}')

    # all_total = db_query(False, f'select sum(current_experience) from character_progression '
    #                             f'where season = {CURRENT_SEASON}')
    # all_total = flatten_list(all_total)
    #
    # totals = db_query(False, f'select profession, sum(current_experience) '
    #                          f'from character_progression where season = {CURRENT_SEASON} '
    #                          f'group by profession order by sum(current_experience) desc')
    # outputString += f'__Serverwide:__\n'
    # for record in totals:
    #     outputString += f'`{record[0]}` - `{record[1]}`\n'
    # outputString += f'`Total` - `{all_total[0]}`\n'

    # outputString += (f'__Goal:__\n`{all_total[0]}` / `{profession_community_goal}` - '
    #                  f'{profession_community_goal_desc}\n')

    # print(f'make leaderboard')
    #LEADERBOARD COMMENT 7/11/25
    # for item in profession_list:
    #
    #     query = f'select char_id, current_experience from character_progression ' \
    #             f'where season = {CURRENT_SEASON} and profession like \'%{item}%\' ' \
    #             f'order by current_experience desc, char_id limit 3'
    #     # print(f'{query}')
    #     profession_leaders = db_query(False, f'{query}')
    #     # print(f'{profession_leaders}')
    #     if not profession_leaders:
    #         continue
    #     else:
    #         outputString += f'\n__{item} Leaderboard:__\n| '
    #
    #         for character in profession_leaders:
    #             char_details = get_registration('', int(character[0]))
    #             char_details = flatten_list(char_details)
    #             # print(f'{char_details}')
    #             char_name = char_details[1]
    #
    #             outputString += f'`{char_name}` - `{character[1]}` | '
    #             # print(f'outputstring is {outputString}')
    #
    # # print(f'{faction_list}')
    # for faction in faction_list:
    #     # print(f'{faction}')
    #
    #     query = (f'select char_id, lifetime_favor from factions where season = {CURRENT_SEASON} '
    #              f'and faction like \'%{faction.lower()}%\' group by char_id order by lifetime_favor desc, char_id '
    #              f'limit 3')
    #     faction_leaders = db_query(False, f'{query}')
    #     # print(f'{faction_leaders}')
    #
    #     if not faction_leaders:
    #         continue
    #     else:
    #         outputString += f'\n__{faction} Leaderboard:__\n| '
    #
    #         for character in faction_leaders:
    #             char_details = get_registration('', int(character[0]))
    #             # print(char_details)
    #             char_details = flatten_list(char_details)
    #             # print(f'{char_details[1]}')
    #             char_name = char_details[1]
    #             # print(f'{char_name}')
    #
    #             outputString += f'`{char_name}` - `{character[1]}` | '
    #             # print(f'outputstring is {len(outputString)} characters')
    #
    #         # print(f'end of loop')
        # LEADERBOARD COMMENT 7/11/25

    # print(f'timestamps')
    if not displayOnly:
        set_bot_config(f'last_profession_update', current_time)
        next_update = current_time + profession_update_interval
        outputString = (f'\n\nUpdated hourly.\n'
                         f'Updated at: <t:{current_time}> in your timezone'
                         f'\nNext: <t:{next_update}:f> in your timezone\n\n') + outputString
        # outputString += (f'\n\nUpdated hourly.\n'
        #                  f'Updated at: <t:{current_time}> in your timezone'
        #                  f'\nNext: <t:{next_update}:f> in your timezone\n')
    else:
        outputString = (f'\n\nUpdated hourly.\n'
                        f'Updated at: <t:{last_profession_update}> in your timezone'
                        f'\nNext: <t:{next_update}:f> in your timezone\n\n') + outputString
        # outputString += (f'\n\nUpdated hourly.\n'
        #                  f'Updated at: <t:{last_profession_update}> in your timezone'
        #                  f'\nNext: <t:{next_update}:f> in your timezone\n')

    # print(f'outputstring is {len(outputString)} characters')
    # print(f'{outputString}')

    await message.edit(content=f'{outputString}')
    return True


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
    @commands.check(check_channel)
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
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
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


        current_target = get_slayer_target(character)
        slayer_favor = get_favor(character.id, f'slayer')

        outputString += f'`Beast Slayer` - Renown: `{slayer_favor.lifetime_favor}`\n'

        if not current_target:
            outputString += f'`Beast Slayer` - Current Quarry: `None`'
        else:
            if current_target.char_id:
                outputString += f'Current Quarry: `{current_target.display_name}`'
                notorious_target, notorious_multiplier = get_notoriety(current_target)
                if notorious_multiplier > 0:
                    outputString += f' **Notorious +{notorious_multiplier}!**'
            else:
                outputString += f'`Beast Slayer` - Current Quarry: `None`'


        slayer_ranking = db_query(False, f'select char_id from factions '
                                  f'where faction like \'%slayer%\' '
                                  f'and season = {CURRENT_SEASON} order by lifetime_favor desc')
        slayer_ranking = flatten_list(slayer_ranking)
        for index, rank in enumerate(slayer_ranking):
            # print(f'{index + 1} {rank}')
            if int(rank) == character.id:
                outputString += f'\nServer-wide Ranking: `{index + 1}`\n\n'

        favor = get_favor(character.id, f'provisioner')
        outputString += (f'`Provisioner` - Current Favor: `{favor.current_favor} / 50` | '
                         f'Lifetime Favor: `{favor.lifetime_favor}`\n')

        provisioner_ranking = db_query(False, f'select char_id from factions '
                                  f'where faction like \'%provisioner%\' '
                                  f'and season = {CURRENT_SEASON} order by lifetime_favor desc')
        provisioner_ranking = flatten_list(provisioner_ranking)
        for index, rank in enumerate(provisioner_ranking):
            if int(rank) == character.id:
                outputString += f'Server-wide Ranking: `{index + 1}`\n\n'

        treasure_target = get_treasure_target(character)

        if not treasure_target:
            outputString += f'`Treasure Hunter`\nCurrent Location: `None`'
        else:
            if treasure_target.char_id:
                outputString += f'`Treasure Hunter`\nCurrent Location: `{treasure_target.location_name}`'
            else:
                outputString += f'`Treasure Hunter`\nCurrent Location: `None`'

        last_profession_update = int(get_bot_config(f'last_profession_update'))
        profession_update_interval = int(get_bot_config(f'profession_update_interval'))
        next_update = last_profession_update + profession_update_interval
        outputString += (f'\n\nProfession Targets Updated at: <t:{last_profession_update}> in your timezone'
                         f'\nNext: <t:{next_update}:f> in your timezone\n')

        await ctx.reply(f'Profession Details for `{character.char_name}`:\n'
                        f'{outputString}')

    @commands.command(name='modifyprofession')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
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

    @commands.command(name='refreshprofessions')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
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
    @commands.check(check_channel)
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
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
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

    @commands.command(name='renameitem')
    @commands.has_any_role('Admin')
    @commands.check(check_channel)
    async def renameitem(self, ctx, item_id: int, item_name: str):
        """

        Parameters
        ----------
        ctx
        item_id
        item_name

        Returns
        -------

        """
        db_query(True, f'update profession_item_list '
                       f'set item_name = \'{item_name}\' where item_id = {item_id}')
        response = db_query(False, f'select * from profession_item_list where item_id = \'{item_id}\'')
        print(response)

        await ctx.reply(response)

    @commands.command(name='professiondetails')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
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

    @commands.command(name='repair', aliases=['fix'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def repair(self, ctx, slot: str = 'hotbar', repair_amount: int = 0, confirm: str = ''):
        """ Modifies current and max durability for eldarium

        Parameters
        ----------
        ctx
        slot
            Which slot contains the item you want to repair
        repair_amount
            How much durability to restore
        confirm
            Type confirm to perform the repair

        Returns
        -------

        """
        eldarium_per_durability = float(get_bot_config(f'eldarium_per_durability'))
        valid_slots = ['hotbar', 'head', 'chest', 'hands', 'legs', 'feet']
        slot_mapping = {'hotbar': 0, 'head': 3, 'chest': 4, 'hands': 5, 'legs': 6, 'feet': 7}
        slot_text = ''

        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        if slot.lower() not in valid_slots:
            await ctx.reply(f'You must specify a valid equipment slot to repair! Use `hotbar`, `head`, `chest`, '
                            f'`hands`, `legs`, `feet`')
            return

        try:
            repair_amount = int(repair_amount)
        except ValueError:
            await ctx.reply(f'You can only repair in whole number amounts greater than 1.')
            return

        repair_cost = math.floor(int(repair_amount) * eldarium_per_durability)
        repair_amount = math.floor(int(repair_amount))

        if slot == 'hotbar':
            slot_text = ' `1`'
            inv_type = 2
            blacksmith = get_profession_tier(character.id, f'Blacksmith')
            if not (blacksmith.tier == 5):
                await ctx.reply(f'Only Blacksmiths who have achieved Tier 5 can repair items on the hotbar. \n'
                                f'Current Blacksmith Tier: `T{blacksmith.tier}`')
                return
        else:
            inv_type = 1
            armorer = get_profession_tier(character.id, f'Armorer')
            if not (armorer.tier == 5):
                await ctx.reply(f'Only Armorers who have achieved Tier 5 can repair equipped armor. \n'
                                f'Current Armorer Tier: `T{armorer.tier}`')
                return

        if repair_cost < 1:
            await ctx.reply(f'You can only repair in whole number amounts greater than 1.')
            return

        slot_value = slot_mapping[slot]

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will repair the item in your `{slot}` slot{slot_text} to exactly `{repair_amount}/{repair_amount}`'
                f' durability. '
                f'\nThe item will be considered fully repaired for the purposes of applying kits.'
                f'\n`{int(repair_cost)} Decaying Eldarium` will be consumed. \nDo not move items in your '
                f'inventory while this command is processing, or it may fail. \nNo refunds will be '
                f'given for user error! \n\nIf you are sure you want to proceed, '
                f'use `v/repair {slot} {repair_amount} confirm`')
            return

        balance = get_balance(character)
        if balance >= repair_cost:
            message = await ctx.reply(f'Repairing item in `{slot}` slot{slot_text}, please wait... '
                                      f'Do not move the item until the process is complete!')
            eld_transaction(character, f'Item Repair Cost', -repair_cost)
            run_console_command_by_name(character.char_name, f'setinventoryitemfloatstat {slot_value} 7 {repair_amount} {inv_type}')
            run_console_command_by_name(character.char_name, f'setinventoryitemfloatstat {slot_value} 8 {repair_amount} {inv_type}')
            await message.edit(content=f'`{character.char_name}` repaired the item in `{slot}` slot{slot_text} to '
                                       f'`{repair_amount}/{repair_amount}` durability.'
                                       f'\nConsumed `{repair_cost}` Decaying Eldarium')
            return
        else:
            await ctx.reply(f'Not enough materials to repair! Available decaying eldarium: `{balance}`, '
                            f'Needed: `{repair_cost}`')
            return

    @commands.command(name='reforge')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def reforge(self, ctx, attribute: str = '', confirm: str = ''):
        """ - Changes the attribute that scales weapon damage for hotbar slot 1

        Parameters
        ----------
        ctx
        attribute
            strength | agility | vitality | grit | authority | expertise
        confirm
            Type confirm to perform the reforging

        Returns
        -------

        """
        valid_attributes = ['strength', 'agility', 'vitality', 'grit', 'authority', 'expertise',
                            'str', 'agi', 'vit', 'auth', 'exp']
        attribute_mapping = {'strength': 17, 'str': 17,
                             'agility': 19, 'agi': 19,
                             'vitality': 14, 'vit': 14,
                             'grit': 15,
                             'authority': 27, 'auth': 27,
                             'expertise': 16, 'exp': 16}

        character = is_registered(ctx.author.id)
        reforge_cost = int(get_bot_config('reforge_cost'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        blacksmith = get_profession_tier(character.id, f'Blacksmith')
        if not (blacksmith.tier >= 4):
            await ctx.reply(f'Only Blacksmiths who have achieved Tier 4 can reforge weapons. \n'
                            f'Current Blacksmith Tier: `T{blacksmith.tier}`')
            return

        if attribute not in valid_attributes:
            await ctx.reply(f'You must specify a valid attribute to reforge a weapon! Use `strength`, `agility`, '
                            f'`vitality`, `grit`, `authority`, `expertise`')
            return

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will change the attribute scaling of the item in hotbar slot 1 to `{attribute}`'
                f'\nIf you choose anything other than Strength or Agility, "Balanced Weapon" '
                f'will be shown on the modified item.'
                f'\n`{reforge_cost} Decaying Eldarium` will be consumed. \nDo not move items in your '
                f'inventory while this command is processing, or it may fail. \nNo refunds will be '
                f'given for user error! \n\nIf you are sure you want to proceed, '
                f'use `v/reforge {attribute} confirm`')
            return

        balance = get_balance(character)
        if balance >= reforge_cost:
            message = await ctx.reply(f'Reforging item in hotbar slot 1, please wait... '
                                      f'Do not move the item until the process is complete!')
            eld_transaction(character, f'Weapon Reforge Cost', -reforge_cost)
            attribute_value = attribute_mapping[attribute]
            run_console_command_by_name(character.char_name, f'setinventoryitemintstat 0 71 {attribute_value} 2')
            run_console_command_by_name(character.char_name, f'setinventoryitemintstat 0 72 {attribute_value} 2')

            await message.edit(content=f'`{character.char_name}` refogred the weapon in hotbar slot 1 to '
                                       f'scale using `{attribute}`.\n'
                                       f'\nConsumed `{reforge_cost}` Decaying Eldarium')
            return
        else:
            await ctx.reply(f'Not enough materials to reforge! Available decaying eldarium: `{balance}`, '
                            f'Needed: `{reforge_cost}`')
            return

    @commands.command(name='fortify')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def fortify(self, ctx, slot: str = '', amount: int = 0, confirm: str = ''):
        """ - Increases the armor value of equipped armor to a fixed amount
        
        Parameters
        ----------
        ctx
        slot
            head | chest | hands | legs | feet
        amount
            How much armor to grant to the item
        confirm
            Type confirm to fortify an armor piece
    
        Returns
        -------
    
        """
        valid_slots = ['head', 'chest', 'hands', 'legs', 'feet']
        slot_mapping = {"head": 3, 'chest': 4, 'hands': 5, 'legs': 6, 'feet': 7}
        # armor_mapping = {"head": 360, 'chest': 630, 'hands': 180, 'legs': 450, 'feet': 180}

        character = is_registered(ctx.author.id)
        eldarium_per_armor = int(get_bot_config('eldarium_per_armor'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        armorer = get_profession_tier(character.id, f'Armorer')
        if not (armorer.tier == 5):
            await ctx.reply(f'Only Armorers who have achieved Tier 5 can fortify armor. \n'
                            f'Current Armorer Tier: `T{armorer.tier}`')
            return

        if slot not in valid_slots:
            await ctx.reply(f'You must specify a valid equipment slot to fortify armor! Use `head`, `chest`, '
                            f'`hands`, `legs`, `feet`')
            return

        slot_value = slot_mapping[slot]
        # armor_value = armor_mapping[slot]

        final_cost = amount * eldarium_per_armor

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will set the armor value of the armor equipped in your `{slot}` '
                f'slot to `{amount}` Armor'
                f'\n`{final_cost} Decaying Eldarium` will be consumed. \nDo not move items in your '
                f'inventory while this command is processing, or it may fail. \nNo refunds will be '
                f'given for user error! \n\nIf you are sure you want to proceed, '
                f'use `v/fortify {slot} confirm`')
            return

        balance = get_balance(character)
        if balance >= final_cost:
            message = await ctx.reply(f'Fortifying armor in equipment slot `{slot}`, please wait... '
                                      f'Do not move the item until the process is complete!')
            eld_transaction(character, f'Armor Fortification Cost', -final_cost)
            run_console_command_by_name(character.char_name,
                                        f'setinventoryitemfloatstat {slot_value} 4 {amount} 1')

            await message.edit(content=f'`{character.char_name}` fortified the armor in '
                                       f'equipment slot `{slot}` to `{amount}` Armor!\n'
                                       f'You must re-equip the armor for it to take effect.\n'
                                       f'\nConsumed `{final_cost}` Decaying Eldarium')
            return
        else:
            await ctx.reply(f'Not enough materials to fortify! Available decaying eldarium: `{balance}`, '
                            f'Needed: `{final_cost}`')
            return

    @commands.command(name='trim')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def trim(self, ctx, slot: str = '', confirm: str = ''):
        """ - Reduces the weight of equipped armor to 0

        Parameters
        ----------
        ctx
        slot
            head | chest | hands | legs | feet
        confirm
            Type confirm to trim an armor piece

        Returns
        -------

        """
        valid_slots = ['head', 'chest', 'hands', 'legs', 'feet']
        slot_mapping = {"head": 3, 'chest': 4, 'hands': 5, 'legs': 6, 'feet': 7}

        character = is_registered(ctx.author.id)
        trim_cost = int(get_bot_config('trim_cost'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        armorer = get_profession_tier(character.id, f'Armorer')
        if not (armorer.tier >= 4):
            await ctx.reply(f'Only Armorers who have achieved Tier 4 can trim armor. \n'
                            f'Current Armorer Tier: `T{armorer.tier}`')
            return

        if slot not in valid_slots:
            await ctx.reply(f'You must specify a valid equipment slot to trim armor! Use `head`, `chest`, '
                            f'`hands`, `legs`, `feet`')
            return

        slot_value = slot_mapping[slot]

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will reduce the weight value of the armor equipped in your `{slot}` '
                f'slot to `0` weight.'
                f'\n`{trim_cost} Decaying Eldarium` will be consumed. \nDo not move items in your '
                f'inventory while this command is processing, or it may fail. \nNo refunds will be '
                f'given for user error! \n\nIf you are sure you want to proceed, '
                f'use `v/trim {slot} confirm`')
            return

        balance = get_balance(character)
        if balance >= trim_cost:
            message = await ctx.reply(f'Trimming weight from armor in equipment slot {slot}, please wait... '
                                      f'Do not move the item until the process is complete!')
            eld_transaction(character, f'Armor Trimming Cost', -trim_cost)
            run_console_command_by_name(character.char_name,
                                        f'setinventoryitemfloatstat {slot_value} 5 0 1')

            await message.edit(content=f'`{character.char_name}` trimmed weight from the armor in '
                                       f'equipment slot `{slot}` to `0`!\n'
                                       f'You must re-equip the armor for it to take effect.\n'
                                       f'\nConsumed `{trim_cost}` Decaying Eldarium')
        else:
            await ctx.reply(f'Not enough materials to trim armor! Available decaying eldarium: `{balance}`, '
                            f'Needed: `{trim_cost}`')
            return

    @commands.command(name='enchant')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def enchant(self, ctx, enchant: str = '', confirm: str = ''):
        """ - Enchants a weapon with a long-lasting effect (1000 charges)

        Parameters
        ----------
        ctx
        enchant
            scorpion | queen | specter
        confirm
            Type confirm to enchant a weapon

        Returns
        -------

        """
        enchant = enchant.lower()
        valid_enchants = ['reaper', 'queen', 'specter']
        enchant_names = {'reaper': 'Reaper Poison', 'queen': 'Scorpion Queen Poison', 'specter': 'Specter Coating'}
        id_mapping = {'reaper': 53201, 'queen': 53203, 'specter': 92127}

        character = is_registered(ctx.author.id)
        enchant_cost = int(get_bot_config('enchant_cost'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        archivist = get_profession_tier(character.id, f'Archivist')
        if not (archivist.tier >= 4):
            await ctx.reply(f'Only Archivists who have achieved Tier 4 can enchant weapons. \n'
                            f'Current Archivist Tier: `T{archivist.tier}`')
            return

        if enchant not in valid_enchants:
            await ctx.reply(f'You must specify a valid enchant to apply! Use `reaper`, `queen`, `specter`')
            return

        id_value = id_mapping[enchant]
        enchant_value = enchant_names[enchant]

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will apply `1000 charges of {enchant_value}` to the weapon in hotbar slot 1.'
                f'\n`{enchant_cost} Decaying Eldarium` will be consumed. \nDo not move items in your '
                f'inventory while this command is processing, or it may fail. \nNo refunds will be '
                f'given for user error! \n\nIf you are sure you want to proceed, '
                f'use `v/enchant {enchant} confirm`')
            return

        balance = get_balance(character)
        if balance >= enchant_cost:
            message = await ctx.reply(f'Enchanting weapon in hotbar slot 1, please wait... '
                                      f'Do not move the item until the process is complete!')
            eld_transaction(character, f'Weapon Enchant Cost', -enchant_cost)
            run_console_command_by_name(character.char_name, f'setinventoryitemintstat 0 51 1000 2')
            run_console_command_by_name(character.char_name, f'setinventoryitemintstat 0 52 1000 2')
            run_console_command_by_name(character.char_name, f'setinventoryitemintstat 0 50 {id_value} 2')

            await message.edit(content=f'`{character.char_name}` enchanted the weapon in hotbar slot 1 '
                                       f'with `1000 charges of {enchant_value}`!\n'
                                       f'\nConsumed `{enchant_cost}` Decaying Eldarium')
        else:
            await ctx.reply(f'Not enough materials to enchant a weapon! Available decaying eldarium: `{balance}`, '
                            f'Needed: `{enchant_cost}`')
            return

    @commands.command(name='research')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def research(self, ctx, sigil: str = '', amount: int = 0, confirm: str = ''):
        """ - Researches a specified sigil for 100 Decaying Eldarium

        Parameters
        ----------
        ctx
        sigil
            bat | demon | outsider | jhil | fiend | drowned | twice-drowned | goblin |
            gremlin | harpy | serpent | snakemen | wolf-brother | wolfmen
        amount
            How many sigils to produce
        confirm
            Type confirm to enchant a weapon

        Returns
        -------

        """
        sigil = sigil.lower()
        valid_sigils = ['bat', 'demon', 'outsider', 'jhil', 'fiend', 'drowned', 'twice-drowned', 'goblin',
                        'gremlin', 'harpy', 'serpent', 'snakemen', 'wolf-brother', 'wolfmen']
        sigil_names = {'bat': 'Sigil of the Bat',
                       'demon': 'Sigil of the Demon',
                       'outsider': 'Sigil of the Outsider',
                       'jhil': 'Sigil of Jhils Brood',
                       'fiend': 'Sigil of the Fiend',
                       'drowned': 'Sigil of the Drowned',
                       'twice-drowned': 'Sigil of the Twice-Drowned',
                       'goblin': 'Sigil of the Goblin',
                       'gremlin': 'Sigil of the Gremlin',
                       'harpy': 'Sigil of the Harpy',
                       'serpent': 'Sigil of the Serpent',
                       'snakemen': 'Sigil of the Snakemen',
                       'wolf-brother': 'Sigil of the Wolf-Brothers',
                       'wolfmen': 'Sigil of the Wolfmen'}
        id_mapping = {'bat': 100006,
                      'demon': 100007,
                      'outsider': 100014,
                      'jhil': 100003,
                      'fiend': 100008,
                      'drowned': 100005,
                      'twice-drowned': 100011,
                      'goblin': 100001,
                      'gremlin': 100010,
                      'harpy': 100009,
                      'serpent': 100013,
                      'snakemen': 100002,
                      'wolf-brother': 100004,
                      'wolfmen': 100012}

        character = is_registered(ctx.author.id)
        research_cost = int(get_bot_config('research_cost'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        archivist = get_profession_tier(character.id, f'Archivist')
        if not (archivist.tier == 5):
            await ctx.reply(f'Only Archivists who have achieved Tier 5 can research sigils. \n'
                            f'Current Archivist Tier: `T{archivist.tier}`')
            return

        if sigil not in valid_sigils:
            await ctx.reply(f'You must specify a valid sigil to research! Use `bat`, `demon`, `outsider`, `jhil`, '
                            f'`fiend`, `drowned`, `twice-drowned`, `goblin`, `gremlin`, `harpy`, `serpent`, '
                            f'`snakemen`, `wolf-brother`, `wolfmen`')
            return

        if amount == 0:
            await ctx.reply(f'You must research at least one sigil at a time! Use `v/research {sigil} amount`')
            return

        try:
            int(amount)
        except ValueError:
            await ctx.reply(f'You can only research sigils in whole numbers greater than zero!')
            return

        id_value = id_mapping[sigil]
        sigil_value = sigil_names[sigil]

        final_cost = amount * research_cost

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will generate `{amount}x {sigil_value}` and place them in your claim list.'
                f'\n`{final_cost} Decaying Eldarium` will be consumed.\nIf you are sure you want to proceed, '
                f'use `v/research {sigil} {amount} confirm`')
            return

        balance = get_balance(character)
        if balance >= final_cost:
            message = await ctx.reply(f'Researching sigils... please wait!')
            eld_transaction(character, f'Sigil Research Cost: {sigil_value}', -final_cost)
            add_reward_record(character.id, id_value, amount, f'Archivist - Research {sigil_value}')

            await message.edit(content=f'`{character.char_name}` has researched `{amount}x {sigil_value}`! '
                                       f'Use `v/claim` to receive them.'
                                       f'\nConsumed `{final_cost}` Decaying Eldarium')
        else:
            await ctx.reply(f'Not enough materials to research that many sigils! '
                            f'Available decaying eldarium: `{balance}`, '
                            f'Needed: `{final_cost}`')
            return

    @commands.command(name='offspring')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def offspring(self, ctx, pet: str = '', amount: int = 0, confirm: str = ''):
        """ - Directs your animals to produce offspring, resulting in rare siptah baby animals using decaying eldarium

        Parameters
        ----------
        ctx
        pet
            feraldog | lynx | lacerta | aardwolf | jungleclaw | siptah pelican |
            mountain lion | turtle | tuskbeast | elephant | pup | yakith
        amount
            How many baby animals to produce
        confirm
            Type confirm to direct animals to produce offspring

        Returns
        -------

        """
        pet = pet.lower()
        valid_pets = ['feraldog', 'lynx', 'lacerta', 'aardwolf', 'jungleclaw', 'pelican',
                      'mountainlion', 'turtle', 'tuskbeast', 'elephant', 'pup', 'yakith']
        pet_names = {'feraldog': 'Feral Dog Pup',
                     'lynx': 'Island Lynx Cub',
                     'lacerta': 'Crested Lacerta Hatchling',
                     'aardwolf': 'Aardwolf Cub',
                     'jungleclaw': 'Jungleclaw Cub',
                     'pelican': 'Siptah Pelican Chick',
                     'mountainlion': 'Mountain Lion Cub',
                     'turtle': 'Turtle Hatchling',
                     'tuskbeast': 'Siptah Rhinoceros Calf',
                     'elephant': 'Antediluvian Elephant Calf',
                     'pup': 'Playful Pup',
                     'yakith': 'Yakith'}

        pup_randomizer = random.randint(19223, 19229)
        tuskbeast_randomizer = random.randint(19046, 19047)
        yakith_randomizer = random.randint(19623, 19624)

        id_mapping = {'feraldog': 19038,
                      'lynx': 19039,
                      'lacerta': 19040,
                      'aardwolf': 19042,
                      'jungleclaw': 19041,
                      'pelican': 19043,
                      'mountainlion': 19044,
                      'turtle': 18262,
                      'tuskbeast': int(tuskbeast_randomizer),
                      'elephant': 19045,
                      'pup': int(pup_randomizer),
                      'yakith': int(yakith_randomizer)}

        character = is_registered(ctx.author.id)
        offspring_cost = int(get_bot_config('offspring_cost'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        tamer = get_profession_tier(character.id, f'Tamer')
        if not (tamer.tier >= 3):
            await ctx.reply(f'Only Tamers who have achieved Tier 3 can direct their animals to produce offspring. \n'
                            f'Current Tamer Tier: `T{tamer.tier}`')
            return

        if pet not in valid_pets:
            await ctx.reply(f'You must specify a valid pet to breed! Use `feraldog`, `lynx`, `lacerta`, `aardwolf`, '
                            f'`jungleclaw`, `pelican`, `mountainlion`, `turtle`, `tuskbeast`, `elephant`, `pup`, `yakith`')
            return

        if amount == 0:
            await ctx.reply(f'Your animals must produce at least one offspring at a time! '
                            f'Use `v/offspring {pet} amount`')
            return

        try:
            int(amount)
        except ValueError:
            await ctx.reply(f'Your animals can only produce offspring in whole numbers greater than zero!')
            return

        id_value = id_mapping[pet]
        pet_value = pet_names[pet]

        final_cost = amount * offspring_cost

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will generate `{amount}x {pet_value}` and place them in your claim list.'
                f'\n`{final_cost} Decaying Eldarium` will be consumed.\nIf you are sure you want to proceed, '
                f'use `v/offspring {pet} {amount} confirm`')
            return

        balance = get_balance(character)
        if balance >= final_cost:
            message = await ctx.reply(f'Breeding animals... please wait!')
            eld_transaction(character, f'Produce Offpsring Cost: {pet_value}', -final_cost)
            add_reward_record(character.id, id_value, amount, f'Tamer - Produce {pet_value}')

            await message.edit(content=f'`{character.char_name}`- `{amount}x{pet_value}` was born! '
                                       f'Use `v/claim` to receive them.'
                                       f'\nConsumed `{final_cost}` Decaying Eldarium')
        else:
            await ctx.reply(f'Not enough materials to produce that many offspring! '
                            f'Available decaying eldarium: `{balance}`, '
                            f'Needed: `{final_cost}`')
            return

    @commands.command(name=f'train')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def train(self, ctx, amount: int, confirm: str = ''):
        """ - Grants your follower XP

        Parameters
        ----------
        ctx
        amount
        confirm

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        xp_per_eldarium = int(get_bot_config('xp_per_eldarium'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        try:
            int(amount)
        except ValueError:
            await ctx.reply(f'Amount must be an integer!.')
            return

        if amount <= 0 or amount < xp_per_eldarium:
            await ctx.reply(f'Amount must be positive and >= {xp_per_eldarium}!.')
            return

        tamer = get_profession_tier(character.id, f'Tamer')
        if not (tamer.tier == 5):
            await ctx.reply(f'Only Tamers who have achieved Tier 5 can train followers. \n'
                            f'Current Tamer Tier: `T{tamer.tier}`')
            return

        final_cost = math.ceil(amount / xp_per_eldarium)

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command grant your follower `{amount}` experience. If you have '
                f'War Party, you can train both followers at once.\n'
                f'\n`{final_cost} Decaying Eldarium` will be consumed. \n\n'
                f'If you are sure you want to proceed, use `v/train {amount} confirm`')
            return

        balance = get_balance(character)

        if balance >= final_cost:
            message = await ctx.reply(f'Training followers... please wait!')
            eld_transaction(character, f'Training Cost: {amount}', -final_cost)
            run_console_command_by_name(character.char_name,f'givefollowerxp {amount}')

            await message.edit(content=f'`{character.char_name}`trained their followers, granting `{amount}` experience. '
                                       f'\nConsumed `{final_cost}` Decaying Eldarium')
        else:
            await ctx.reply(f'Not enough materials to train that much experience! '
                            f'Available decaying eldarium: `{balance}`, '
                            f'Needed: `{final_cost}`')
            return

    @commands.command(name='animalbond')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def animalbond(self, ctx, confirm: str = ''):
        """ - Increases pet stats significantly

        Parameters
        ----------
        ctx
        confirm
            Type confirm to perform the ritual of bonding

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        bond_cost = int(get_bot_config('bond_cost'))
        damage_bonus = int(get_bot_config('animal_bond_damage_bonus'))

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        tamer = get_profession_tier(character.id, f'Tamer')
        if not (tamer.tier >= 4):
            await ctx.reply(f'Only Tamers who have achieved Tier 4 perform an animal bonding ritual. \n'
                            f'Current Tamer Tier: `T{tamer.tier}`')
            return

        if 'confirm' not in confirm.lower():
            await ctx.reply(
                f'This command will set the Damage Modifier of your current pet on follow mode to `{damage_bonus}.0`. '
                f'Mounts will be upgraded to `10,000` Endurance.'
                f'Do not use this command with human followers, or you will be thrown into the volcano.\nIf you have '
                f'War Party, you can bond with both following pets at once.\n'
                f'\n`{bond_cost} Decaying Eldarium` will be consumed. \n\n'
                f'If you are sure you want to proceed, '
                f'use `v/animalbond confirm`')
            return

        balance = get_balance(character)
        if balance >= bond_cost:
            damage_bonus = int(get_bot_config('animal_bond_damage_bonus'))
            message = await ctx.reply(f'Performing ritual of bonding with your pet, please wait... ')
            eld_transaction(character, f'Animal Bond Cost', -bond_cost)
            run_console_command_by_name(character.char_name,
                                        f'setfollowerstat damagemodifiermelee {damage_bonus}')
            run_console_command_by_name(character.char_name,
                                        f'setfollowerstat damagemodifierranged {damage_bonus}')
            run_console_command_by_name(character.char_name,
                                        f'setfollowerstat endurancemax 10000')

            await message.edit(content=f'`{character.char_name}` has performed a ritual of bonding with their pet, '
                                       f'increasing their damage modifiers to `5.0` and endurance to `10,000`!'
                                       f'\nConsumed `{bond_cost}` Decaying Eldarium')
        else:
            await ctx.reply(f'Not enough materials to perform a ritual of bonding! '
                            f'Available decaying eldarium: `{balance}`, Needed: `{bond_cost}`')
            return

    @commands.command(name='crafterlist', aliases=['professionlist', 'whocrafter'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def crafterlist(self, ctx):
        """ - Lists profession crafters of T4 or higher

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        professioner = ProfessionTier()
        character = is_registered(ctx.author.id)
        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        outputString = '__List of T4+ Profession Crafters__\n'
        message = await ctx.reply(f'{outputString}')
        results = db_query(False, f'select char_id, profession, tier from character_progression where '
                                  f'season = {CURRENT_SEASON} and tier >= 4 order by profession asc, tier asc')

        for result in results:
            (professioner.char_id, professioner.profession, professioner.tier) = result
            character = get_single_registration_new(char_id=professioner.char_id)
            outputString += f'<@{character.discord_id}> - {professioner.profession} T{professioner.tier}\n'

        await message.edit(content=f'{outputString}')

        return


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Professions(bot))
