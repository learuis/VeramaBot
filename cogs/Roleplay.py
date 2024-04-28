from discord.ext import commands
from functions.common import custom_cooldown, flatten_list
from functions.externalConnections import db_query


class Roleplay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='roleplay', aliases=['rp'])
    @commands.has_any_role('Admin', 'Moderator', 'Roleplay')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def Roleplay(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputMessage = f'__Online Roleplayers:__\n'

        results = db_query(f'select online.char_id, online.char_name, reg.discord_user '
                           f'from online_character_info as online '
                           f'left join registration as reg on online.char_id = reg.game_char_id '
                           f'where reg.season = 6')

        if results:
            print(f'{results}')
        else:
            outputMessage += f'None'
            return

        message = await ctx.reply(f'{outputMessage}')

        for result in results:
            outputMessage += f'\n{result[1]} | <@{result[2]}>'

        await message.edit(content=outputMessage)
        return


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Roleplay(bot))
