# VeramaBot.py
import discord
import time
import os
import traceback
from time import localtime, strftime
from discord.ext import commands
from discord.ext.commands import Bot
from discord.ext import tasks
from dotenv import load_dotenv

from cogs.Professions import updateProfessionBoard
from cogs.QuestSystem import oneStepQuestUpdate, pull_online_character_info, treasure_broadcast
from cogs.Roleplaying import RoleplayingButton
from cogs.Utilities import is_character_online
from functions.common import is_docker, editStatus, place_markers, fillThrallCages, update_boons, get_bot_config
from cogs.CharRegistration import RegistrationButton

load_dotenv('data/server.env')
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
BOT_CHANNEL = int(os.getenv('BOT_CHANNEL'))
STATUS_CHANNEL = int(os.getenv('STATUS_CHANNEL'))
STATUS_MESSAGE = int(os.getenv('STATUS_MESSAGE'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))
PROFESSION_CHANNEL = int(os.getenv('PROFESSION_CHANNEL'))
PROFESSION_MESSAGE = int(os.getenv('PROFESSION_MESSAGE'))
ADMIN_LOG_CHANNEL = int(os.getenv('ADMIN_LOG_CHANNEL'))
LOBBY_CHANNEL = int(os.getenv('LOBBY_CHANNEL'))

intents = discord.Intents.all()
intents.message_content = True

if is_docker():
    bot: Bot = commands.Bot(command_prefix=['v/', 'V/'], intents=intents)
else:
    bot: Bot = commands.Bot(command_prefix=['vt/', 'Vt/'], intents=intents)

bot.quest_running = False

# @bot.event
# async def on_ready():

@bot.event
async def on_ready():
    for f in os.listdir('./cogs'):
        if f.endswith('.py'):
            await bot.load_extension(f'cogs.{f[:-3]}')
    loadtime = strftime('%m/%d/%y at %H:%M:%S', localtime(time.time()))
    channel = bot.get_channel(BOT_CHANNEL)

    bot.add_view(RegistrationButton())
    bot.add_view(RoleplayingButton())

    if not liveStatus.is_running():
        liveStatus.start()

    if not onlineCharacterAlert.is_running():
        onlineCharacterAlert.start()

    if not professionBoard.is_running():
        professionBoard.start()

    if not onlineCharacterInfo.is_running():
        onlineCharacterInfo.start()

    if not oneStepQuestChecker.is_running():
        oneStepQuestChecker.start()

    if not placeMarkers.is_running():
        placeMarkers.start()

    if not boonChecker.is_running():
        boonChecker.start()

    if not fillCages.is_running():
        fillCages.start()

    # if not treasure_announcer.is_running():
    #     treasure_announcer.start()

    if is_docker():
        await channel.send(f'VeramaBot PROD (use /v) started on {loadtime}.')
    else:
        await channel.send(f'VeramaBot TEST (use /vt) started on {loadtime}.')

@tasks.loop(seconds=30)
async def onlineCharacterInfo():

    try:
        pull_online_character_info()
    except TimeoutError:
        print(f'onlineCharacterInfo took too long to complete.')
        return
    except Exception:
        print(f'onlineCharacterInfo ended with an exception')
        return


@tasks.loop(seconds=45)
async def oneStepQuestChecker():

    try:
        await oneStepQuestUpdate(bot)
    except TimeoutError:
        print(f'oneStepQuestUpdate took too long to complete.')
        return
    except Exception as e:
        print(f'oneStepQuestChecker ended with an exception {type(e)}')
        traceback.format_exc()
        return

@tasks.loop(minutes=8)
async def fillCages():

    try:
        fillThrallCages()
    except TimeoutError:
        print(f'fillThrallCages took too long to complete.')
        return
    except Exception as e:
        print(f'fillThrallCages ended with an exception: {type(e)}')
        return

@tasks.loop(minutes=5)
async def onlineCharacterAlert():
    channel = bot.get_channel(BOT_CHANNEL)

    try:
        await is_character_online(channel)
    except Exception as e:
        print(f'onlineCharacterAlert ended with an exception {type(e)}')
        return

@tasks.loop(minutes=1)
async def liveStatus():

    channel = bot.get_channel(STATUS_CHANNEL)
    message = await channel.fetch_message(STATUS_MESSAGE)

    try:
        await editStatus(message, bot)
    except discord.errors.DiscordServerError:
        print(f'Discord error prevented status updates.')
        return
    except Exception:
        print(f'liveStatus ended with an exception')
        return

@tasks.loop(minutes=1)
async def professionBoard():

    channel = bot.get_channel(PROFESSION_CHANNEL)
    message = await channel.fetch_message(PROFESSION_MESSAGE)

    try:
        await updateProfessionBoard(message)
    except discord.errors.DiscordServerError:
        print(f'Discord error prevented profession updates.')
        return
    except Exception as e:
        print(f'professionBoard ended with an exception {e}')
        return

@tasks.loop(hours=1)
async def placeMarkers():

    try:
        place_markers()
        #print(f'placing markers via loop')
    except TimeoutError:
        print(f'place_markers took too long to complete.')
        return
    except Exception:
        print(f'place_markers ended with an exception')
        return

@tasks.loop(hours=1)
async def boonChecker():

    try:
        update_boons()
    except TimeoutError:
        print(f'boonChecker took too long to complete.')
        return
    except Exception:
        print(f'boonChecker ended with an exception')
        return

@tasks.loop(minutes=30)
async def treasure_announcer():

    try:
        treasure_broadcast()
    except TimeoutError:
        print(f'treasure_broadcast took too long to complete.')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(ADMIN_LOG_CHANNEL)
    guild = member.guild
    if channel is not None:
        await channel.send(f"{member.name} - {member.mention} has joined the server!")
    channel2 = bot.get_channel(LOBBY_CHANNEL)
    if channel2 is not None:
        await channel2.send(f"Hello {member.name} - {member.mention}! Welcome to **Band of Outcasts**! "
                            f"Please follow the server onboarding process and accept the rules here <id:customize>")

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(ADMIN_LOG_CHANNEL)
    guild = member.guild
    if channel is not None:
        await channel.send(f"{member.name} - {member.mention} has left the server! Join date: {member.joined_at}")

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
