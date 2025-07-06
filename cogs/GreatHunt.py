import os

from discord.ext import commands

from cogs.QuestSystem import character_in_radius
from functions.common import custom_cooldown, is_registered, get_rcon_id, no_registered_char_reply
from functions.externalConnections import runRcon

from dotenv import load_dotenv

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))

class GreatHunt(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='hunt')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def hunt(self, ctx):
        """- Spawns the Sacred Hunt vendor at your location.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        monster = 'Event_Gods_JS_Vendor'

        # match target.casefold():
        #     case 'mammoth':
        #         monster = 'Event_Gods_JS_Mammoth'
        #         await ctx.reply(f'Invalid target selection. Must be mammoth, rhino, panther, or merchant')
        #         return
        #     case 'rhino':
        #         monster = 'Event_Gods_JS_Rhino'
        #         await ctx.reply(f'Invalid target selection. Must be mammoth, rhino, panther, or merchant')
        #         return
        #     case 'panther':
        #         monster = 'Event_Gods_JS_Panther'
        #         await ctx.reply(f'Invalid target selection. Must be mammoth, rhino, panther, or merchant')
        #         return
        #     case 'merchant':
        #         monster = 'Event_Gods_JS_Vendor'
        #         await ctx.reply(f'Invalid target selection. Must be mammoth, rhino, panther, or merchant')
        #         return
        #     case _:
        #         await ctx.reply(f'Invalid target selection. Must be mammoth, rhino, panther, or merchant')
        #         return

        # 351692.40625 - 38293.332031 - 19874.220703
        # merhcant

        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        # char_id, char_name = character_in_radius(354927.28125, -34319.316406, -19872.861328, 200)
        # if char_id:
        #     rconCharId = get_rcon_id(char_name)
        #     if not rconCharId:
        #         await ctx.reply(f'Character {char_name} must be online to spawn Great Hunt bosses')
        #         return
        #     else:
        #         runRcon(f'con {rconCharId} dc spawn exact {monster}')
        #
        #         await ctx.send(f'Spawned `{monster}` at `{char_name}\'s` position')
        #         return
        # else:
        #     if 'Event_Gods_JS_Vendor' not in monster:
        #         await ctx.reply(f'Character {char_name} is not in the correct location!')
        #         return

        char_id, char_name = character_in_radius(-164557.375, 6978.441895, -462.746765, 200)
        if char_id:
            rconCharId = get_rcon_id(char_name)
            if not rconCharId:
                await ctx.reply(f'Character {char_name} must be online to spawn the Sacred Hunt Vendor')
                return
            else:
                runRcon(f'con {rconCharId} dc spawn exact {monster} r180')

                await ctx.send(f'Spawned `{monster}` at `{char_name}\'s` position')
                return
        else:
            await ctx.reply(f'Character may not be in the correct position. '
                            f'Please wait 90 seconds and try again.')
            return
@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog((GreatHunt(bot)))
