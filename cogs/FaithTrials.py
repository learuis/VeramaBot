import sqlite3

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
    await channel.send(f'{interaction.user.mention} has declared their faith in {godName}')
    outputString = (f'You have declared your faith to {godName}! Join your fellow '
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
                await setGod(interaction, ZATH_CHANNEL, ZATH_ROLE, self.values[0])
            case 'Jhebbal Sag, The Lord of Beasts':
                await setGod(interaction, SAG_CHANNEL, SAG_ROLE, self.values[0])
            case 'Yog, The Lord of Empty Abodes':
                await setGod(interaction, YOG_CHANNEL, YOG_ROLE, self.values[0])
            case 'Derketo, The Two-Faced Goddess':
                await setGod(interaction, DERKETO_CHANNEL, DERKETO_ROLE, self.values[0])
            case 'Mitra, The Phoenix':
                await setGod(interaction, MITRA_CHANNEL, ZATH_ROLE, self.values[0])
            case 'Set, The Old Serpent':
                await setGod(interaction, SET_CHANNEL, SET_ROLE, self.values[0])
            case 'Ymir, The Lord of War and Storms':
                await setGod(interaction, YMIR_CHANNEL, YMIR_ROLE, self.values[0])
            case 'Crom, The Grim Grey God':
                await setGod(interaction, CROM_CHANNEL, CROM_ROLE, self.values[0])
            case 'Faithless':
                await setGod(interaction, 0, FAITHLESS_ROLE, self.values[0])
            case _:
                print('this should never happen')

class FaithTrials(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='faithlist', aliases=['listfaith', 'listgods'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def faithList(self, ctx):
        """- Placeholder

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        print(f'{ctx} return list of people in roles')

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

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(FaithTrials(bot))
