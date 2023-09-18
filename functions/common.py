import discord
import re
import time
import requests
import os
from discord import ui
from discord.ext import commands
from functions.externalConnections import runRcon
import sqlite3
from datetime import date
from time import strftime, localtime

from dotenv import load_dotenv

load_dotenv('data/server.env')
QUERY_URL = os.getenv('QUERY_URL')

def custom_cooldown(ctx):
    whitelist = {'Admin', 'Moderator'}
    roles = {role.name for role in ctx.author.roles}
    if not whitelist.isdisjoint(roles):
        #if we're a special role, no cooldown assigned
        return None
    else:
        #everyone else
        return discord.app_commands.Cooldown(3, 60)

def checkChannel(ctx):
    execTime = time.strftime('%c')
    print(f'Command {ctx.command} executed by {ctx.author} on {execTime}')
    return ctx.channel.id == 1144882044552364093

def isInt(intToCheck):
    try:
        int(intToCheck)
    except ValueError:
        return False
    else:
        return True

def ununicode(string):
    output = re.sub(r'[^\x00-\x7F]', '?', string)
    output = output.replace('??', '?')
    return output

def percentage(int1, int2):
    ratio = (int1 / int2) * 100
    ratio = round(ratio)
    return ratio

def is_docker():
    path = '/proc/self/cgroup'
    return (
        os.path.exists('/.dockerenv') or
        os.path.isfile(path) and any('docker' in line for line in open(path))
    )

def popup_to_player(charName: str, message: str):
    rconId = get_rcon_id(charName)
    rconResponse = runRcon(f'con {rconId} PlayerMessage \"{charName}\" \"{message}\"')
    print(rconResponse.output)
    print(f'PlayerMessage \"{charName}\" \"{message}\"')

def get_rcon_id(name: str):
    connected_chars = []

    rconResponse = runRcon('listplayers')
    rconResponse.output.pop(0)

    for x in rconResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', x)
        connected_chars.append(match)
        print(connected_chars)

    if not connected_chars:
        return False

    for x in connected_chars:
        if name.casefold() in x[1].casefold():
            return x[0].strip()

def is_registered(discord_user):
    class Registration:
        def __init__(self):
            self.id = 0
            self.char_name = ''

    returnValue = Registration()
    name = str(discord_user).casefold()
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()

    cur.execute(f'select game_char_id, character_name from registration where discord_user = \'{name}\'')
    result = cur.fetchone()

    con.close()

    returnValue.id = result[0]
    returnValue.char_name = result[1]

    if result:
        return returnValue
    else:
        return False

async def editStatus(message, bot):
    currentTime = strftime('%A %m/%d/%y at %I:%M %p', time.localtime())

    response = requests.get(QUERY_URL).json()
    ipAddress = response.get('ipAddress')
    onlineStatus = response.get('online')
    currentPlayers = response.get('currentPlayers')
    maxPlayers = response.get('maxPlayers')

    if onlineStatus == 'False':
        statusSymbol = '<:redtick:1152409914430455839>'
        await bot.change_presence(activity=discord.Activity(name=f'-/{maxPlayers} OFFLINE', type=3))
    else:
        statusSymbol = '<:greentick:1152409721966432376>'
        await bot.change_presence(activity=discord.Activity(name=f'{currentPlayers}/{maxPlayers} ONLINE', type=3))

    onlineSymbol = ':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    if int(currentPlayers) == 30:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::orange_circle::orange_circle:'
    if int(currentPlayers) < 30:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::orange_circle::blue_circle:'
    if int(currentPlayers) < 24:
        onlineSymbol = f':orange_circle::orange_circle::orange_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 18:
        onlineSymbol = f':orange_circle::orange_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 12:
        onlineSymbol = f':orange_circle::blue_circle::blue_circle::blue_circle::blue_circle:'
    if int(currentPlayers) < 6:
        onlineSymbol = f':blue_circle::blue_circle::blue_circle::blue_circle::blue_circle:'

    await message.edit(content=f'**Band of Outcasts Server Status**\n'
                               f'__{currentTime}__\n'
                               f'- IP Address: {ipAddress}:32600\n'
                               f'- Server Online: {onlineStatus} {statusSymbol}\n'
                               f'- Players Connected: {currentPlayers} / {maxPlayers} {onlineSymbol}\n'
                               f'Server restarts are at 8:00am and 2:45pm Eastern')

class RegistrationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Register your Character", style=discord.ButtonStyle.green, custom_id="my_custom_button")
    async def register_character(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.send_modal(RegistrationForm())

class RegistrationForm(ui.Modal, title='Character Registration'):
    charName = ui.TextInput(label=f'Character Name', placeholder='Your discord nickname will be changed to this!')
    funcomId = ui.TextInput(label=f'Funcom ID', placeholder='Find this in game by pressing L')
    clanName = ui.TextInput(label=f'Clan Name', placeholder='Verama will make this a dropdown maybe?')

    async def on_submit(self, interaction: discord.Interaction):

        con_sub = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur_sub = con_sub.cursor()

        cur_sub.execute(f'select id from game_char_mapping where name like \'%{self.charName}%\'')
        res = cur_sub.fetchone()

        if res:
            charId = int(res[0])
        else:
            charId = 0

        cur_sub.execute(f'insert into registration '
                        f'(discord_user,character_name,funcom_id,registration_date,season,game_char_id) values '
                        f'(\'{interaction.user}\',\'{self.charName}\',\'{self.funcomId}\','
                        f'\'{date.today()}\',3,{charId})')
        con_sub.commit()
        con_sub.close()

        await interaction.response.send_message(f'Registered character: {self.charName} (id {charId}) '
                                                f'with Funcom ID: {self.funcomId} '
                                                f'to user {interaction.user.mention}', ephemeral=True)
                                                
        try:
            await interaction.user.edit(nick=str(self.charName))
        except discord.errors.Forbidden:
            print(f'Missing persmissions to change nickname on {interaction.user.name}')

        channel = interaction.client.get_channel(1150628473061253251)
        await channel.send(f'__Character Name:__ {self.charName}\n'
                           f'__Funcom ID:__ {self.funcomId}\n'
                           f'__Discord:__ {interaction.user.mention}')

    class GodSelection(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="Derketo", emoji="�", description="This is option 1!"),
                discord.SelectOption(label="Option 2", emoji="✨", description="This is option 2!"),
                discord.SelectOption(label="Option 3", emoji="🎭", description="This is option 3!")
            ]
            super().__init__(placeholder="Select an option", max_values=1, min_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            if self.values[0] == "Option 1":
                await interaction.response.edit_message(content="This is the first option from the entire list!")
            elif self.values[0] == "Option 2":
                await interaction.response.send_message("This is the second option from the list entire wooo!",
                                                        ephemeral=False)
            elif self.values[0] == "Option 3":
                await interaction.response.send_message("Third One!", ephemeral=True)

    class SelectView(discord.ui.View):
        def __init__(self, *, timeout=180):
            super().__init__(timeout=timeout)
            self.add_item(Select())
