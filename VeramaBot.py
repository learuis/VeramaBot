# VeramaBot.py
import discord
import time
import os
from time import localtime, strftime
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext import tasks
from dotenv import load_dotenv

from functions.common import is_docker, checkChannel, editStatus
from cogs.Registration import RegistrationButton
from cogs.FaithTrials import ChooseGod

load_dotenv('data/server.env')
TOKEN = os.getenv('DISCORD_TOKEN')
print(f'you did it! great job')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.all()
intents.message_content = True


if is_docker():
    bot: Bot = commands.Bot(command_prefix=['v/', 'V/'], intents=intents)
else:
    bot: Bot = commands.Bot(command_prefix=['vt/', 'Vt/'], intents=intents)

@bot.event
async def on_ready():
    for f in os.listdir('./cogs'):
        if f.endswith('.py'):
            await bot.load_extension(f'cogs.{f[:-3]}')
    loadtime = strftime('%m/%d/%y at %H:%M:%S', localtime(time.time()))
    channel = bot.get_channel(1144882044552364093)

    if is_docker():
        await channel.send(f'VeramaBot PROD (use /v) started on {loadtime}.')
    else:
        await channel.send(f'VeramaBot TEST (use /vt) started on {loadtime}.')

    bot.add_view(RegistrationButton())
    bot.add_view(ChooseGod())

    if not liveStatus.is_running():
        liveStatus.start()

@tasks.loop(minutes=1)
async def liveStatus():

    channel = bot.get_channel(1027396030469255178)
    message = await channel.fetch_message(1151908253752635412)

    await editStatus(message, bot)

@bot.command(name='break', aliases=['breaking', 'broke', 'why'])
@commands.has_any_role('Admin', 'Moderator')
@commands.check(checkChannel)
async def breaking(ctx):
    """- Breaks the bot. Do not use!

    You broke it.

    Parameters
    ----------
    ctx

    Returns
    -------

    """

    await ctx.send(f'Nooooooooooooo I am broken')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Missing parameter! See v/help for details.')
        return
    if isinstance(error, commands.errors.CheckFailure):
        print(f'Command from {ctx.message.author} failed checks. '
              f'{ctx.message.channel.id} / {ctx.message.channel.name}.')
        await ctx.send(error)
        return
    if isinstance(error, commands.errors.CommandOnCooldown):
        await ctx.send(error)
        return
    if isinstance(error, commands.errors.BadArgument):
        await ctx.send(error)
        return
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f'Invalid command `{ctx.message.content}`! Use `v/help`')
        return
    else:
        await ctx.send(error)
        raise error


bot.run(TOKEN)

"""
@bot.command(name='size', brief='Change a player\'s size (test only)', help='Changes the size of a player by copying \
            from a reference thrall (test only)')
@commands.has_role('Admin')
@commands.check(checkChannel)
async def size(ctx, charName):
    #nothing
    print(0)
    #take in player name, sex, chosen size
    #kick them from the server
    #listplayers to make sure they're offline
    #get their char id from the database
    #get the char id of the source entity
    #run sql to copy their current layout to placeholder
    #run sql to copy the source layout to current layout
"""
