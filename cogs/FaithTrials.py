import discord
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel
from functions.views import ChooseGod

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
