import sqlite3
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel, is_registered, has_feat

class FeatClaim(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='restorefeats',
                      aliases=['feats', 'restore', 'knowledge'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def restoreFeats(self, ctx, feat: int):
        """

        Parameters
        ----------
        ctx
        name
        feat

        Returns
        -------

        """
        charId = is_registered(ctx.message.author)

        if charId:
            if has_feat(charId, feat):
                await ctx.send(f'Character {charId} has feat {feat}')
            else:
                await ctx.send(f'Character {charId} is missing feat {feat}')
        else:
            await ctx.send(f'No character registered to {ctx.message.author}!')


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(FeatClaim(bot))