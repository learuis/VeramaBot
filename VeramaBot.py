# VeramaBot.py
import discord
import time
import os
from time import localtime, strftime
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext import tasks
from dotenv import load_dotenv

from cogs.CommunityBoons import update_boons
from cogs.QuestSystem import oneStepQuestUpdate
from functions.common import is_docker, editStatus, place_markers
from cogs.Registration import RegistrationButton
from cogs.FaithTrials import ChooseGod

load_dotenv('data/server.env')
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
BOT_CHANNEL = int(os.getenv('BOT_CHANNEL'))
STATUS_CHANNEL = int(os.getenv('STATUS_CHANNEL'))
STATUS_MESSAGE = int(os.getenv('STATUS_MESSAGE'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))

intents = discord.Intents.all()
intents.message_content = True

if is_docker():
    bot: Bot = commands.Bot(command_prefix=['v/', 'V/'], intents=intents)
else:
    bot: Bot = commands.Bot(command_prefix=['vt/', 'Vt/'], intents=intents)

bot.maintenance_flag = False
bot.market_night = False

# @bot.event
# async def on_ready():

@bot.event
async def on_ready():
    for f in os.listdir('./cogs'):
        if f.endswith('.py'):
            await bot.load_extension(f'cogs.{f[:-3]}')
    loadtime = strftime('%m/%d/%y at %H:%M:%S', localtime(time.time()))
    channel = bot.get_channel(BOT_CHANNEL)

    if is_docker():
        await channel.send(f'VeramaBot PROD (use /v) started on {loadtime}.')
    else:
        await channel.send(f'VeramaBot TEST (use /vt) started on {loadtime}.')

    bot.add_view(RegistrationButton())
    bot.add_view(ChooseGod())

    if not liveStatus.is_running():
        liveStatus.start()

    # if not onlineCharacterInfo.is_running():
    #     onlineCharacterInfo.start()

    # if not questChecker.is_running():
    #     questChecker.start()

    if not oneStepQuestChecker.is_running():
        oneStepQuestChecker.start()

    if not placeMarkers.is_running():
        placeMarkers.start()

    if not boonChecker.is_running():
        boonChecker.start()

# @tasks.loop(seconds=30)
# async def onlineCharacterInfo():
#
#     try:
#         pull_online_character_info()
#     except TimeoutError:
#         print(f'onlineCharacterInfo took too long to complete.')

# @tasks.loop(seconds=30)
# async def questChecker():
#
#     try:
#         await questUpdate()
#     except TimeoutError:
#         print(f'questUpdate took too long to complete.')

@tasks.loop(seconds=30)
async def oneStepQuestChecker():
    try:
        await oneStepQuestUpdate()
    except TimeoutError:
        print(f'oneStepQuestUpdate took too long to complete.')

@tasks.loop(minutes=1)
async def liveStatus():

    channel = bot.get_channel(STATUS_CHANNEL)
    message = await channel.fetch_message(STATUS_MESSAGE)

    try:
        await editStatus(message, bot)
    except discord.errors.DiscordServerError:
        print(f'Discord error prevented status updates.')

@tasks.loop(hours=1)
async def placeMarkers():

    try:
        place_markers()
    except TimeoutError:
        print(f'placeMarkers took too long to complete.')

@tasks.loop(hours=1)
async def boonChecker():

    try:
        update_boons()
    except TimeoutError:
        print(f'boonChecker took too long to complete.')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Missing parameter! See v/help for details.')
        return
    if isinstance(error, commands.errors.CheckFailure):
        print(f'Command from {ctx.message.author} failed checks. '
              f'{ctx.message.channel.id}.')
        channel = bot.get_channel(OUTCASTBOT_CHANNEL)
        await ctx.send(f'You do not have permission to use this command, or you cannot use that command in this '
                       f'channel. Try {channel.mention}!')
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
    if isinstance(error, discord.errors.DiscordServerError):
        channel = bot.get_channel(BOT_CHANNEL)
        await channel.send(f'A discord server error has occurred. VeramaBot may need to be restarted to recover.')
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
