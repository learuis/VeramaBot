import sqlite3
import re
import discord

from discord import ui
from discord.ext import commands
from functions.common import custom_cooldown, checkChannel
from functions.externalConnections import runRcon
from datetime import date

class RegistrationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Register your Character", style=discord.ButtonStyle.green, custom_id="my_custom_button")
    async def register_character(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.send_modal(RegistrationForm())

class RegistrationForm(ui.Modal, title='Character Registration'):
    charName = ui.TextInput(label=f'Character Name', placeholder='Type your full in-game character name')
    funcomId = ui.TextInput(label=f'Funcom ID', placeholder='Find this in game by pressing L')

    async def on_submit(self, interaction: discord.Interaction):

        response = runRcon(f'sql select id, char_name from characters where char_name = \'{self.charName}\'')
        response.output.pop(0)
        print(response.output)

        if response.output:
            for x in response.output:
                print(x)
                match = re.findall(r'\s+\d+ | [^|]*', x)
                print(f'{match[0]} matched to {match[1]}')
                charId = match[0]
        else:
            channel = interaction.guild.get_channel(1025790340499767296)
            await interaction.response.send_message(f'Could not locate a character named `{self.charName}`. '
                                                    f'If you typed your name correctly, please post in '
                                                    f'{channel.mention}', ephemeral=True)
            return
        con_sub = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur_sub = con_sub.cursor()

        cur_sub.execute(f'insert into registration '
                        f'(discord_user,character_name,funcom_id,registration_date,season,game_char_id) values '
                        f'(\'{interaction.user}\',\'{self.charName}\',\'{self.funcomId}\','
                        f'\'{date.today()}\',4,{charId})')
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

class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='prepare')
    @commands.is_owner()
    async def prepare(self, ctx: commands.Context):
        await ctx.send('Click the button below to register your character. You must type your name exactly as it'
                       ' appears in game, including spaces, punctuation, and special characters. \n\n*Your discord '
                       'nickname will be changed to match the character name you enter here!*',
                       view=RegistrationButton())

    @commands.command(name='registrationlist', aliases=['reglist'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def register(self, ctx):
        """- Lists all registered characters

        Queries the VeramaBot database for all registered characters.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputString = f'id,discord_user,character_name,funcom_id,registration_date,season,game_char_id\n'

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()
        cur.execute(f'select * from registration')
        res = cur.fetchall()

        for x in res:
            outputString += f'{x}\n'
        await ctx.send(outputString)
        return

    @commands.command(name='registrationdelete', aliases=['regdelete', 'regdel'])
    @commands.has_any_role('Admin')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
    async def registrationdelete(self, ctx,
                                 recordToDelete: int = commands.parameter(default=0)):
        """- Delete a record from the registration database

        Deletes a selected record from the VeramaBot database table 'registration'.

        Does not delete the entry in the registration channel.

        Parameters
        ----------
        ctx
        recordToDelete
            Specify which record number should be deleted.
        Returns
        -------

        """
        if recordToDelete == 0:
            await ctx.send(f'Record to delete must be specified. Use `v/help registrationdelete`')
        else:
            try:
                int(recordToDelete)
            except ValueError:
                await ctx.send(f'Invalid record number')
            else:
                con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                cur = con.cursor()

                cur.execute(f'select * from registration where id = {recordToDelete}')
                res = cur.fetchone()

                cur.execute(f'delete from registration where id = {recordToDelete}')
                con.commit()

                await ctx.send(f'Deleted record:\n{res}')

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Registration(bot))
