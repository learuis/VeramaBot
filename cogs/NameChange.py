from discord.ext import commands

class NameChange(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(NameChange(bot))