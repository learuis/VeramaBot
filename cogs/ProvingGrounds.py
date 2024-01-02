import math
import re

from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id
from functions.externalConnections import runRcon


class ProvingGrounds(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='provinggrounds', aliases=['pg'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def provingGrounds(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        characterPosition = []
        character = is_registered(ctx.author.id)

        if not character:
            await ctx.reply(f'**Proving Grounds Testing**\n'
                            f'Could not find a character registered to {ctx.author.mention}.')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'**Proving Grounds Testing**\n'
                            f'Character {character.char_name} must be online to begin the Proving Grounds.')
            return

        rconResponse = runRcon(f'sql select x, y from actor_position where id = {character.id}')
        if rconResponse.output:
            print(rconResponse.output)
            rconResponse.output.pop(0)
            for record in rconResponse.output:
                match = re.findall(r'\s+\d+ | [^|]*', record)
                characterPosition = [float(line.strip()) for line in match]
            print(characterPosition)

        if rconResponse.output:
            centerPosition = [-161388.328125, 4962.57959]
            distance = math.dist(characterPosition, centerPosition)
            if distance > 500:
                await ctx.send(f'**Proving Grounds Testing**\n'
                               f'Character {character.char_name} is not within the specified location.')
            else:
                rconCharId = get_rcon_id(character.char_name)
                runRcon(f'con {rconCharId} dc spawn Sorcery_DemonSummonPerk_Elite')
                await ctx.send(f'**Proving Grounds Testing**\n'
                               f'Location confirmed! Spawned `Sorcery_DemonSummonPerk_Elite` at `{character.char_name}'
                               f'\'s` position')
        else:
            await ctx.send(f'**Proving Grounds Testing**\n'
                           f'problem!')
            return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(ProvingGrounds(bot))
