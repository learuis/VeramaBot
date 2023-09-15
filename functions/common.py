import discord
import re
import time
import requests
import os
from discord import ui
from discord.ext import commands
import sqlite3
from datetime import date
from time import strftime, localtime

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

async def editStatus(message):
    currentTime = strftime('%A %m/%d/%y at %I:%M %p', time.localtime())

    response = requests.get("https://api.g-portal.us/gameserver/query/846857").json()
    ipAddress = response.get('ipAddress')
    onlineStatus = response.get('online')
    currentPlayers = response.get('currentPlayers')
    maxPlayers = response.get('maxPlayers')

    await message.edit(content=f'**Band of Outcasts Server Status**\n'
                               f'__{currentTime}__\n'
                               f'- IP Address: {ipAddress}:32600\n'
                               f'- Server Online: {onlineStatus}\n'
                               f'- Players Connected: {currentPlayers} / {maxPlayers}\n'
                               f'Server restarts are at 8:00am and 2:45pm Eastern')

class RegistrationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Register your Character", style=discord.ButtonStyle.green, custom_id="my_custom_button")
    async def register_character(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.send_modal(RegistrationForm())

class TestRegistrationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Register your Character (TEST)", style=discord.ButtonStyle.green,
                       custom_id="test_registration")
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
