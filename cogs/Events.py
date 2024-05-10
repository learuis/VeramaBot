import io
import random

from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id, set_bot_config, get_bot_config
from functions.externalConnections import runRcon, notify_all


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='boss')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def boss(self, ctx):
        """- Spawns a random Siptah boss at cursor position.

        Uses RCON to spawn a random Siptah boss at the location your target is currently pointing at

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        monsterlist = []

        character = is_registered(ctx.author.id)

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        file = io.open('data/boss_py.dat', mode='r')

        for line in file:
            monsterlist.append(line)

        file.close()

        monster = random.choice(monsterlist)
        monster = f'dc spawn exact {monster}'

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character {character.char_name} must be online to spawn bosses')
            return
        else:
            runRcon(f'con {rconCharId} {monster}')

            await ctx.send(f'Spawned `{monster}` at `{character.char_name}\'s` position')
            return

    @commands.command(name='startevent')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def startevent(self, ctx, location: str):
        """

        Parameters
        ----------
        ctx
        location
            as: x y z

        Returns
        -------

        """
        if location == '0':
            set_bot_config('event_location', str(location))
            await ctx.send(f'Event Teleport Flag has been disabled!')
        else:
            currentSetting = set_bot_config('event_location', str(location))
            await ctx.send(f'Event Teleport Flag has been enabled, destination: {currentSetting}!')

    @commands.command(name='event', aliases=['market'])
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def event(self, ctx):
        """- Teleports you to an active event location.

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        location = get_bot_config('event_location')
        if location == '0':
            await ctx.reply(f'This command can only be used during an event!')
            return

        character = is_registered(ctx.author.id)

        if not character:
            await ctx.reply(f'No character registered to player {ctx.author.mention}!')
            return
        else:
            name = character.char_name

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{name}` must be online to teleport to an event!')
            return
        else:
            runRcon(f'con {rconCharId} TeleportPlayer {location}')
            await ctx.reply(f'Teleported `{name}` to the event location.')
            return

    @commands.command(name='alert')
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def Alert(self, ctx, style: int = commands.parameter(default=5),
                    text1: str = commands.parameter(default=f'-Event-'),
                    text2: str = commands.parameter(default=f'Siptah beasts roam the Exiled Lands')):
        """
        - Sends an alert to all online players

        Parameters
        ----------
        ctx
        style
        text1
        text2

        Returns
        -------

        """

        notify_all(style, f'{text1}', f'{text2}')
        await ctx.send(f'Sent alert style {style} with message: {text1} {text2}')

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Events(bot))
