# VeramaBot.py
#import io
#import random
#import time
import sys

from time import strftime, localtime
from discord.ext.commands import Bot
#from dotenv import load_dotenv
from discord.ext import commands

from functions.common import *
from functions.externalConnections import *

load_dotenv('bandofoutcasts_env.txt')
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')

intents = discord.Intents.all()
intents.message_content = True

#modified again
#test comment for working copy
#bot: Bot = commands.Bot(command_prefix=['v/', 'V/'], intents=intents)
bot: Bot = commands.Bot(command_prefix=['vt/', 'Vt/'], intents=intents)

@bot.event
async def on_ready():
    for f in os.listdir('./cogs'):
        if f.endswith('.py'):
            await bot.load_extension(f'cogs.{f[:-3]}')
    loadtime = strftime('%m/%d/%y at %H:%M:%S', localtime(time.time()))
    channel = bot.get_channel(1144882044552364093)

    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):
        await channel.send(f'VeramaBot PROD (use /v) started on {loadtime}.')
    elif __file__:
        await channel.send(f'VeramaBot TEST (use /vt) started on {loadtime}.')

    bot.add_view(RegistrationButton())

@bot.command(name='prepare')
@commands.is_owner()
async def prepare(ctx: commands.Context):
    await ctx.send("Click this button to register your character.", view=RegistrationButton())

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
    if isinstance(error, commands.errors.CheckFailure):
        print(f'Command from {ctx.message.author} failed checks. '
              f'{ctx.message.channel.id} / {ctx.message.channel.name}.')
        await ctx.send(error)
    if isinstance(error, commands.errors.CommandOnCooldown):
        await ctx.send(error)
    if isinstance(error, commands.errors.BadArgument):
        await ctx.send(error)
    if isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f'Invalid command `{ctx.message.content}`! Use `v/help`')
    else:
        await ctx.send(error)
        raise error


bot.run(TOKEN)

"""

class Buttons(discord.ui.View):
    def __init__(self, *, timeout=180):
        super().__init__(timeout=timeout)
    @discord.ui.button(label="Button",style=discord.ButtonStyle.gray)
    #async def gray_button(self,button:discord.ui.Button,interaction:discord.Interaction):
    async def send_message(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.edit_message(content=f"This is an edited button response!")

@bot.command(name='button', brief='A button', help='This makes a button.')
@commands.has_any_role('Admin','Moderator')
@commands.check(checkChannel)
async def button(ctx):
    await ctx.send("This message has buttons!",view=Buttons())
"""

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
