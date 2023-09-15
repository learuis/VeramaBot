import sqlite3
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel

class CharacterLink(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='linkcharacter',
                      aliases=['link', 'linkchar', 'characterlink', 'charlink'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def characterLink(self, ctx, name):
        """- Link your discord registration to a character on the server

        Parameters
        ----------
        ctx
        name
            Provide as v/linkchar "Exact Character Name"

        Returns
        -------

        """

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'select * from game_char_mapping where name like \'%{name}%\'')
        result = cur.fetchone()
        print(result)
        print(str(result[0]))

        if result:
            cur.execute(f'update registration set game_char_id = {int(result[0])} '
                        f'where discord_user like \'%{ctx.message.author}%\'')
            con.commit()
            con.close()

        await ctx.send(f'Results for character named {name}:\n{result}\n'
                       f'Mapping {name} (id {int(result[0])}) to {ctx.message.author}')

        await ctx.invoke(self.bot.get_command('registrationlist'))

        #require that player registration is already done
        #ask about linking characters in buttons automatically?
        #take an argument containing their character name
        #select records from the characters table that are like the character name
        #display a list of at most 5 choices to link your character. + "do this later"
        #send an emphemeral message to the user with a button for each option
        #take user button choice and assign the chosen character to that discord id in registration table

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(CharacterLink(bot))
