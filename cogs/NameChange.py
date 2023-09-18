import discord
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel

class NameChange(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='namechange', aliases=['changename', 'setname'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def changeName(self, ctx, discord_user: discord.Member):
        """

        Parameters
        ----------
        ctx
        discord_user

        Returns
        -------

        """

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(NameChange(bot))
