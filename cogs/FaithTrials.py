import discord
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel

class ChooseGod(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GodDropdown())

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
                                 description='Consume the flesh of our foes.'),
            discord.SelectOption(label='Faithless', emoji=f'\N{diamond shape with a dot inside}',
                                 description='I live, I burn with life, I love, I slay, and am content.')
            ]
        super().__init__(placeholder='Declare your faith to your God! (scroll for more)', max_values=1, min_values=1,
                         options=options, custom_id='choose_god')

    async def callback(self, interaction: discord.Interaction):
        role_list = [1153364149707997264,
                     1153364278326333491,
                     1153364443875516466,
                     1153364580647579845,
                     1153364669877190797,
                     1153364727825694842,
                     1153364788680872047,
                     1153364847262707752,
                     1153369055512776754]
        role_to_add = discord.Role
        outputString = 'This should never be written!'

        storeUser = interaction.user

        match self.values[0]:
            case 'Zath, The Spider-God of Yezud':
                channel = interaction.guild.get_channel(1153363765539123270)
                role_to_add = storeUser.guild.get_role(1153364847262707752)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Jhebbal Sag, The Lord of Beasts':
                channel = interaction.guild.get_channel(1153363889602437211)
                role_to_add = storeUser.guild.get_role(1153364580647579845)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Yog, The Lord of Empty Abodes':
                channel = interaction.guild.get_channel(1153363990349631550)
                role_to_add = storeUser.guild.get_role(1153364788680872047)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Derketo, The Two-Faced Goddess':
                channel = interaction.guild.get_channel(1153363802918756362)
                role_to_add = storeUser.guild.get_role(1153364278326333491)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Mitra, The Phoenix':
                channel = interaction.guild.get_channel(1153363926449406022)
                role_to_add = storeUser.guild.get_role(1153364443875516466)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Set, The Old Serpent':
                channel = interaction.guild.get_channel(1153363948737941504)
                role_to_add = storeUser.guild.get_role(1153364669877190797)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Ymir, The Lord of War and Storms':
                channel = interaction.guild.get_channel(1153374995930689547)
                role_to_add = storeUser.guild.get_role(1153364727825694842)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Crom, The Grim Grey God':
                channel = interaction.guild.get_channel(1153363838343856128)
                role_to_add = storeUser.guild.get_role(1153364149707997264)
                outputString = (f'You have declared your faith to {self.values[0]}! Join your fellow '
                                f'worshipers here: {channel.mention}')
            case 'Faithless':
                role_to_add = storeUser.guild.get_role(1153369055512776754)
                outputString = f'You have declared yourself to be {self.values[0]}!'
            case _:
                print('this should never happen')

        storeUser = interaction.user

        await interaction.response.send_message(content=outputString, ephemeral=True)

        for role_to_remove in role_list:
            await storeUser.remove_roles(storeUser.guild.get_role(role_to_remove))

        await storeUser.add_roles(role_to_add)

class FaithTrials(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='faithlist', aliases=['listfaith', 'listgods'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def faithList(self, ctx):
        """- Placeholder

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        print('return list of people in roles')

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
