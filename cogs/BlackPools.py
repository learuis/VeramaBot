import os
import random
import re

from discord.ext import commands

from cogs.QuestSystem import character_in_radius
from functions.common import custom_cooldown, is_registered, get_rcon_id, no_registered_char_reply, check_channel, \
    run_console_command_by_name, flatten_list, get_clan, modify_favor
from functions.externalConnections import runRcon, db_query

from dotenv import load_dotenv

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))

def circle_in_range(x, y, radius, owner_id):
    count = 0
    nwPoint = [x - radius, y - radius]
    sePoint = [x + radius, y + radius]

    rconResponse = runRcon(f'sql select count(*) from actor_position a left join buildings b on a.id = b.object_id '
                           f'where b.owner_id = {owner_id} '
                           f'and x > {nwPoint[0]} and y > {nwPoint[1]} '
                           f'and x < {sePoint[0]} and y < {sePoint[1]} '
                           f'and a.class like \'%ChalkCircle%\' limit 1;')

    for x in rconResponse.output:
        print(x)
        match = re.search(r'#\b\d\s+(\d+)', x)
        if match:
            match.group(1)
            count = int(match.group(1))

    return count

def figurine_in_range(x, y, radius, owner_id):
    object_id = False
    object_class = False
    nwPoint = [x - radius, y - radius]
    sePoint = [x + radius, y + radius]

    rconResponse = runRcon(f'sql select id, class from actor_position a left join buildings b on a.id = b.object_id '
                           f'where b.owner_id = {owner_id} '
                           f'and x > {nwPoint[0]} and y > {nwPoint[1]} '
                           f'and x < {sePoint[0]} and y < {sePoint[1]} '
                           f'and ( a.class like \'%Statue_BlackPool%\' or a.class like \'%VaultStatue%\' ) limit 1;')

    for x in rconResponse.output:
        print(x)
        # all_matches = re.findall(r'#\b\d\s+(\d+)\s+[|]\s+(.*)\s+[|]', x)
        # match_count = len(all_matches)
        match = re.search(r'#\b\d\s+(\d+)\s+[|]\s+(.*)\s+[|]', x)
        if match:
            object_id = int(match.group(1))
            object_class = match.group(2)
            print(f'{match.group(1)} {match.group(2)}')

    return object_id, object_class

class BlackPools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='conjure')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def conjure(self, ctx):
        """- Consumes a placed Figurine or Devolved Statue to summon a powerful enemy at your Circle of Power.
        Place Siptah Figurines or Devolved Statues inside the Circle of Power to control which enemy is conjured.
        Execute the discord command while standing in the circle, then quickly return to the game and point your cursor at the desired spawn location.
        Only use this in a secluded location. Do not use this to grief other players or their bases!

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        monster = ''

        figurine_mapping = {'/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Shaggai.BP_PL_Statue_BlackPool_Shaggai_C': 'BlackPool_Boss_Shaggai_Horror',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_BloodlessHusk.BP_PL_Statue_BlackPool_BloodlessHusk_C': 'BlackPool_Boss_Bloodless_Husk',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Ghoul.BP_PL_Statue_BlackPool_Ghoul_C': 'BlackPool_Boss_Ghoul',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Tchotcho.BP_PL_Statue_BlackPool_Tchotcho_C': 'BlackPool_Boss_TchoTcho_Lama',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Thunnha.BP_PL_Statue_BlackPool_Thunnha_C': 'BlackPool_Boss_Thunnha',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Lloigor.BP_PL_Statue_BlackPool_Lloigor_C':
                                ['BlackPool_Boss_Lloigor_Blue','BlackPool_Boss_Lloigor_Red'],
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_FirstMen.BP_PL_Statue_BlackPool_FirstMen_C':
                                ['BlackPool_Boss_First_Men_Chieftain_1','BlackPool_Boss_First_Men_Chieftain_2','BlackPool_Boss_First_Men_Chieftain_3'],
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Yakith.BP_PL_Statue_BlackPool_Yakith_C': 'BlackPool_Boss_Yakith',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Bokrug.BP_PL_Statue_BlackPool_Bokrug_C': 'BlackPool_Boss_Avatar_of_Bokrug',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_BloodDefiler.BP_PL_Statue_BlackPool_BloodDefiler_C': 'BlackPool_Boss_Blood-Defiler',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_BloodMoonBeast.BP_PL_Statue_BlackPool_BloodMoonBeast_C': 'BlackPool_Boss_Blood-moon_Beast',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_GiantKing.BP_PL_Statue_BlackPool_GiantKing_C': 'BlackPool_Boss_Giant_King',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_Krllyandian.BP_PL_Statue_BlackPool_Krllyandian_C': 'BlackPool_Boss_Krllyandian',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_MiGo.BP_PL_Statue_BlackPool_MiGo_C': 'BlackPool_Boss_MiGo',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_ShaggaiHuntress.BP_PL_Statue_BlackPool_ShaggaiHuntress_C': 'BlackPool_Boss_Shaggai_Huntress',
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_SilentLegion.BP_PL_Statue_BlackPool_SilentLegion_C':
                                ['BlackPool_Boss_Silent_Legion_Warrior_Solo','BlackPool_Boss_Silent_Legion_Warrior_1',
                                 'BlackPool_Boss_Silent_Legion_Warrior_2','BlackPool_Boss_Silent_Legion_Warrior_3'],
                            '/Game/Systems/Building/Placeables/BP_PL_Statue_BlackPool_SpiderOfLeng.BP_PL_Statue_BlackPool_SpiderOfLeng_C': 'BlackPool_Boss_SpiderOfLeng',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue1.BP_VaultStatue1_C': 'Wildlife_Siptah_DevolvedBatBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue2.BP_VaultStatue2_C': 'Wildlife_Siptah_DevolvedBirdBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue3.BP_VaultStatue3_C': 'Wildlife_Siptah_DevolvedDrownedBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue4.BP_VaultStatue4_C': 'Wildlife_Siptah_DevolvedFiend_Boss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue5.BP_VaultStatue5_C': 'Wildlife_Siptah_DevolvedGoblinBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue6.BP_VaultStatue6_C': 'Wildlife_Siptah_DevolvedHarpyBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue7.BP_VaultStatue7_C': 'Wildlife_Siptah_DevolvedHarpyBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue8.BP_VaultStatue8_C': 'Wildlife_Siptah_DevolvedSerpentBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue9.BP_VaultStatue9_C': 'Wildlife_Siptah_DevolvedDemonSpiderBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultStatue10.BP_VaultStatue10_C': 'Wildlife_Siptah_DevolvedWerewolfBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy1.BP_VaultTrophy1_C': 'Wildlife_Siptah_DevolvedBatBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy2.BP_VaultTrophy2_C': 'Wildlife_Siptah_DevolvedBirdBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy3.BP_VaultTrophy3_C': 'Wildlife_Siptah_DevolvedDrownedBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy4.BP_VaultTrophy4_C': 'Wildlife_Siptah_DevolvedFiend_Boss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy5.BP_VaultTrophy5_C': 'Wildlife_Siptah_DevolvedGoblinBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy6.BP_VaultTrophy6_C': 'Wildlife_Siptah_DevolvedHarpyBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy7.BP_VaultTrophy7_C': 'Wildlife_Siptah_DevolvedSerpentBoss',
                            '/Game/DLC/DLC_Siptah/Systems/Placeables/BP_VaultTrophy8.BP_VaultTrophy8_C': 'Wildlife_Siptah_DevolvedDemonSpiderBoss'}

        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        if not get_rcon_id(character.char_name):
            await ctx.reply(f'Character {character.char_name} must be online to conjure monsters.')
            return

        location = db_query(False, f'select x, y, z '
                                   f'from online_character_info as online '
                                   f'where char_id = {character.id}')
        (x, y, z) = flatten_list(location)

        clan_id, clan_name = get_clan(character)
        print(f'{clan_id} {clan_name}')
        if not clan_id:
            clan_id = character.id

        if int(circle_in_range(x, y, 500, clan_id)) == 0:
            await ctx.reply(f'`{character.char_name}` is not close enough to a Circle of Power that they own.\n'
                            f'Please wait 90 seconds and try again.')
            return
        else:
            object_id, object_class = figurine_in_range(x, y, 500, clan_id)
            print(f'out of loop {object_id} {object_class}')
            if object_id and object_class:
                print(figurine_mapping[object_class])
                if type(figurine_mapping[object_class]) is list:
                    monster = random.choice(figurine_mapping[object_class])
                else:
                    monster = figurine_mapping[object_class]
                run_console_command_by_name(character.char_name, f'destroyactorbyuniqueid {object_id}')
                run_console_command_by_name(character.char_name, f'dc spawn exact {monster} r180')
                modify_favor(character.id, 'conjurer', 1)
                await ctx.send(f'`{character.char_name}` conjured a `{monster}`!')
                return
            else:
                await ctx.send(f'Could not find an appropriate Conjuration Focus inside the Circle of Power!')
                return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog((BlackPools(bot)))
