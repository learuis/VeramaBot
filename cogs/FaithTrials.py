import sqlite3
from datetime import date

import discord
import os

from discord.ext import commands
from functions.common import custom_cooldown, modChannel, is_registered
from dotenv import load_dotenv

load_dotenv('data/server.env')
ZATH_CHANNEL = int(os.getenv('ZATH_CHANNEL'))
ZATH_ROLE = int(os.getenv('ZATH_ROLE'))
SAG_CHANNEL = int(os.getenv('SAG_CHANNEL'))
SAG_ROLE = int(os.getenv('SAG_ROLE'))
YOG_CHANNEL = int(os.getenv('YOG_CHANNEL'))
YOG_ROLE = int(os.getenv('YOG_ROLE'))
DERKETO_CHANNEL = int(os.getenv('DERKETO_CHANNEL'))
DERKETO_ROLE = int(os.getenv('DERKETO_ROLE'))
MITRA_CHANNEL = int(os.getenv('MITRA_CHANNEL'))
MITRA_ROLE = int(os.getenv('MITRA_ROLE'))
SET_CHANNEL = int(os.getenv('SET_CHANNEL'))
SET_ROLE = int(os.getenv('SET_ROLE'))
YMIR_CHANNEL = int(os.getenv('YMIR_CHANNEL'))
YMIR_ROLE = int(os.getenv('YMIR_ROLE'))
CROM_CHANNEL = int(os.getenv('CROM_CHANNEL'))
CROM_ROLE = int(os.getenv('CROM_ROLE'))
FAITHLESS_ROLE = int(os.getenv('FAITHLESS_ROLE'))

class ChooseGod(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GodDropdown())


async def setGod(interaction: discord.Interaction, godChannel: int, godRole: int, godName: str):
    role_list = [ZATH_ROLE,
                 SAG_ROLE,
                 YOG_ROLE,
                 DERKETO_ROLE,
                 MITRA_ROLE,
                 SET_ROLE,
                 YMIR_ROLE,
                 CROM_ROLE,
                 FAITHLESS_ROLE
                 ]

    channel = interaction.guild.get_channel(godChannel)
    role_to_add = interaction.user.guild.get_role(godRole)

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'update registration set god = \'{godName}\' where discord_user = {interaction.user.id}')
    await channel.send(f'{interaction.user.mention} has declared their faith in {godName.capitalize()}')
    outputString = (f'You have declared your faith to {godName.capitalize()}! Join your fellow '
                    f'worshipers here: {channel.mention}')

    con.commit()
    con.close()

    # noinspection PyUnresolvedReferences
    await interaction.response.send_message(content=outputString, ephemeral=True)

    for role_to_remove in role_list:
        await interaction.user.remove_roles(interaction.user.guild.get_role(role_to_remove))

    if godRole:
        await interaction.user.add_roles(role_to_add)

    return


class GodDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Zath, The Spider-God of Yezud', emoji=f'\N{spider web}',
                                 description='Naught but holy venom can purify this world.'),
            discord.SelectOption(label='Jhebbal Sag, The Lord of Beasts', emoji=f'\N{wolf face}',
                                 description='We share the language of the beasts.'),
            discord.SelectOption(label='Yog, The Lord of Empty Abodes', emoji=f'\N{octopus}',
                                 description='Consume the flesh of our foes.'),
            discord.SelectOption(label='Derketo, The Two-Faced Goddess', emoji=f'\N{peach}',
                                 description='Walk the line between lust and death.'),
            discord.SelectOption(label='Mitra, The Phoenix', emoji=f'\N{bird}',
                                 description='We are called to live a life of virtue.'),
            discord.SelectOption(label='Set, The Old Serpent', emoji=f'\N{snake}',
                                 description='Our rule shall be restored.'),
            discord.SelectOption(label='Ymir, The Lord of War and Storms', emoji=f'\N{snowflake}',
                                 description='We go to the great feast.'),
            discord.SelectOption(label='Crom, The Grim Grey God', emoji=f'\N{drop of blood}',
                                 description='Courage, free will, and the strength to fight our enemies.'),
            discord.SelectOption(label='Faithless', emoji=f'\N{diamond shape with a dot inside}',
                                 description='I live, I burn with life, I love, I slay, and am content.')
            ]
        super().__init__(placeholder='Declare your faith to your God! (scroll for more)', max_values=1, min_values=1,
                         options=options, custom_id='choose_god')

    async def callback(self, interaction: discord.Interaction):

        if not is_registered(interaction.user.id):
            outputString = f'You must register a character before declaring your faith.'
            # noinspection PyUnresolvedReferences
            await interaction.response.send_message(content=outputString, ephemeral=True)
            return

        match self.values[0]:
            case 'Zath, The Spider-God of Yezud':
                await setGod(interaction, ZATH_CHANNEL, ZATH_ROLE, 'zath')
            case 'Jhebbal Sag, The Lord of Beasts':
                await setGod(interaction, SAG_CHANNEL, SAG_ROLE, 'jhebbal')
            case 'Yog, The Lord of Empty Abodes':
                await setGod(interaction, YOG_CHANNEL, YOG_ROLE, 'yog')
            case 'Derketo, The Two-Faced Goddess':
                await setGod(interaction, DERKETO_CHANNEL, DERKETO_ROLE, 'derketo')
            case 'Mitra, The Phoenix':
                await setGod(interaction, MITRA_CHANNEL, ZATH_ROLE, 'mitra')
            case 'Set, The Old Serpent':
                await setGod(interaction, SET_CHANNEL, SET_ROLE, 'set')
            case 'Ymir, The Lord of War and Storms':
                await setGod(interaction, YMIR_CHANNEL, YMIR_ROLE, 'ymir')
            case 'Crom, The Grim Grey God':
                await setGod(interaction, CROM_CHANNEL, CROM_ROLE, 'crom')
            case 'Faithless':
                await setGod(interaction, 0, FAITHLESS_ROLE, 'faithless')
            case _:
                print('this should never happen')

class FaithTrials(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='faithlist', aliases=['listfaith', 'listgods'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def faithList(self, ctx, faith: str):
        """- List players who are members of a faith

        Parameters
        ----------
        ctx
        faith
            Which god to select

        Returns
        -------

        """
        godList = ['crom', 'derketo', 'yog', 'ymir', 'set', 'zath', 'jhebbal', 'mitra', 'all']
        outputString = ''

        if faith.casefold() not in godList:
            await ctx.send(f'Invalid god `{faith}` provided.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        if faith == 'all':
            cur.execute(f'select character_name, god from registration where god is not null order by god ASC')
            results = cur.fetchall()
            if results:
                outputString = f'All Faithful:\n'
                for result in results:
                    outputString += f'{result}\n'
            await ctx.send(f'{outputString}')
            con.close()
            return

        # get all players with the selected faith in a list
        cur.execute(f'select character_name, god from registration where god like \'%{faith}%\'')
        results = cur.fetchall()

        if results:
            outputString = f'Followers of {faith.capitalize()}:\n'
            for result in results:
                outputString += f'{result[0]}\n'
            await ctx.send(f'{outputString}')
        else:
            await ctx.send(f'There are currently no followers of {faith.capitalize()}.')

    @commands.command(name='god_prepare')
    @commands.is_owner()
    async def god_prepare(self, ctx: commands.Context):
        """- Sends a message with the God selection dialog

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        file = discord.File('data/images/gods.png', filename='gods.png')
        embed = discord.Embed(title='Declaration of Faith',
                              description='Declare your faith here, mortal. \nThe gods shall determine your worthiness '
                                          'to serve them. \n\n__This cannot be changed once selected!__\n\nIf you '
                                          'declare yourself to be Faithless, you will not have access to any of '
                                          'the Trials of the Faithful channels. You can join one of the faiths '
                                          'later through roleplaying.',
                              color=discord.Color.blue())
        embed.set_image(url='attachment://gods.png')
        await ctx.send(file=file, embed=embed, view=ChooseGod())

    @commands.command(name='quest', aliases=['completequest', 'faithquest'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def quest(self, ctx, faith: str, blessing: str, playerCount: int):
        """
        Usage:
        v/quest [faith] [blessing] [playerCount]

        Faiths: crom | derketo | yog | ymir | set | zath | jhebbal | mitra

        Blessings: dregs | midnightgrove | witchqueen | passage | scorpionden

                   barrowking | blackkeep | arena | wellofskelos | frosttemple

                   sunkencity | warmakers | wincellar | purge
        Parameters
        ----------
        ctx
        faith
            Which religion completed the quest
        blessing
            Which dungeon/blessing was completed
        playerCount
            Number of players who completed it


        Returns
        -------

        """

        godList = ['crom', 'derketo', 'yog', 'ymir', 'set', 'zath', 'jhebbal', 'mitra']
        blessingList = ['dregs', 'midnightgrove', 'witchqueen', 'passage', 'scorpionden', 'barrowking', 'blackkeep',
                        'arena', 'wellofskelos', 'frosttemple', 'sunkencity', 'warmakers', 'winecellar', 'purge']
        blessingNames = {
            'dregs': 'the abyss',
            'midnightgrove': 'the grove',
            'witchqueen': 'the witch',
            'passage': 'the spawn',
            'scorpionden': 'the venom',
            'barrowking': 'the giant',
            'blackkeep': 'the kin',
            'arena': 'the dragon',
            'wellofskelos': 'the degenerate',
            'frosttemple': 'the forge',
            'sunkencity': 'the deep',
            'warmakers': 'the sanctuary',
            'winecellar': 'wine',
            'purge': 'war'
        }

        if faith.casefold() not in godList:
            await ctx.send(f'Invalid god `{faith}` provided.')
            return
        if blessing.casefold() not in blessingList:
            await ctx.send(f'Invalid blessing `{blessing}` provided.')
            return

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        #get all players with the selected faith in a list
        cur.execute(f'select game_char_id, character_name from registration where god like \'%{faith}%\'')
        faithMembers = cur.fetchall()

        rewards = []
        match blessing:
            case 'dregs':
                amount = 50 * playerCount
                rewards.append([11501, amount])
                rewards.append([14195, amount])

        for member in faithMembers:
            print(date.today())
            amount = 1 * playerCount
            for reward in rewards:
                cur.execute(f'insert into faith_rewards '
                            f'(reward_date, character_id, reward_material, reward_quantity, claim_flag) '
                            f'values '
                            f'(\'{date.today()}\',{member[0]}, {reward[0]}, {reward[1]}, 0)')

            await ctx.send(f'`{member[1]}` has been granted **{faith.capitalize()}\'s Blessing of '
                           f'{blessingNames.get(blessing).title()}**. Type `v/claim` to receive your reward.')
        con.commit()
        con.close()

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(FaithTrials(bot))
