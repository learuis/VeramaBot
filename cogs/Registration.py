import re
import sqlite3
import discord
import os

from discord import ui
from discord.ext import commands
from functions.common import custom_cooldown, modChannel, get_character_id, is_registered, get_registration, \
    get_member_from_userid
from datetime import date
from dotenv import load_dotenv

from functions.externalConnections import db_delete_single_record, db_query

load_dotenv('data/server.env')
SUPPORT_CHANNEL = int(os.getenv('SUPPORT_CHANNEL'))
AUTOREG_CHANNEL = int(os.getenv('AUTOREG_CHANNEL'))
OUTCASTBOT_CHANNEL = int(os.getenv('OUTCASTBOT_CHANNEL'))
REG_ROLE = int(os.getenv('REG_ROLE'))


# noinspection PyUnresolvedReferences
class RegistrationButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Register your Character", style=discord.ButtonStyle.green, custom_id="my_custom_button")
    async def register_character(self, interaction: discord.Interaction, button: discord.ui.button):
        await interaction.response.send_modal(RegistrationForm())

# noinspection PyUnresolvedReferences
class RegistrationForm(ui.Modal, title='Character Registration'):
    charName = ui.TextInput(label=f'Character Name', placeholder='Type your full, exact in-game character name',
                            max_length=60)
    funcomId = ui.TextInput(label=f'Funcom ID', placeholder='Find this in game by pressing L',
                            max_length=60)

    async def on_submit(self, interaction: discord.Interaction):

        outputString = ''
        charId = get_character_id(f'{self.charName}')

        if not charId:
            channel = interaction.guild.get_channel(SUPPORT_CHANNEL)
            await interaction.response.send_message(f'Could not locate a character named `{self.charName}`. '
                                                    f'If you typed your name correctly, please post in '
                                                    f'{channel.mention}', ephemeral=True)
            return

        charId = charId.strip()

        if not re.search(r'^[^#]+#\d{5}', str(self.funcomId)):
            await interaction.response.send_message(f'Funcom ID `{self.funcomId}` was formatted incorrectly. Must be '
                                                    f'in the following format: `funcom name here#12345`. You can find '
                                                    f'this value by pressing L while in game.', ephemeral=True)
            return

        con_sub = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur_sub = con_sub.cursor()

        if is_registered(interaction.user.id):
            cur_sub.execute(f'update registration set character_name = \'{self.charName}\', '
                            f'funcom_id = \'{self.funcomId}\', game_char_id = {charId} '
                            f'where discord_user = \'{interaction.user.id}\'')
            outputString = (f'Your registration has been updated: {self.charName} (id {charId}) '
                            f'with Funcom ID: {self.funcomId} to user {interaction.user.mention}')
        else:
            cur_sub.execute(f'insert into registration '
                            f'(discord_user,character_name,funcom_id,registration_date,season,game_char_id) values '
                            f'(\'{interaction.user.id}\',\'{self.charName}\',\'{self.funcomId}\','
                            f'\'{date.today()}\',4,{charId})')
            outputString = (f'Registered character: {self.charName} (id {charId}) with Funcom ID: {self.funcomId} '
                            f' to user {interaction.user.mention}. You have been granted a feat as a reward! Go to the '
                            f'<#{OUTCASTBOT_CHANNEL}> channel and type `v/featrestore` to receive it!')

        cur_sub.execute(f'insert or ignore into featclaim (char_id,feat_id) values ({charId},50007)')

        con_sub.commit()
        con_sub.close()

        await interaction.response.send_message(f'{outputString}', ephemeral=True)

        try:
            await interaction.user.edit(nick=str(self.charName))
        except discord.errors.Forbidden:
            print(f'Missing persmissions to change nickname on {interaction.user.name}')

        channel = interaction.client.get_channel(AUTOREG_CHANNEL)
        await channel.send(f'__Character Name:__ {self.charName}\n'
                           f'__Funcom ID:__ {self.funcomId}\n'
                           f'__Discord:__ {interaction.user.mention}')

        await interaction.user.add_roles(interaction.user.guild.get_role(REG_ROLE))

class Registration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='prepare')
    @commands.is_owner()
    async def prepare(self, ctx: commands.Context):
        await ctx.send(f'Click the button below to register your character. Your character must already be '
                       f'created in game in order to register! \nMake sure to type your name exactly as it'
                       f' appears in game, including capitalization, spaces, punctuation and special characters. '
                       f'\n\n*Your discord nickname will be changed to match the character name you enter here!*',
                       view=RegistrationButton())

    @commands.command(name='registrationforce',
                      aliases=['forcereg', 'linkchar'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def registrationForce(self, ctx, discord_user: discord.Member, name: str, funcom_id: str, game_char_id: int):
        """- Manually create a character registration record

        Usage: v/forcereg @user "Character Name" funcom_id game_database_id

        Parameters
        ----------
        ctx
        discord_user
            @tag the user to be registered
        name
            Provide as "Exact Character Name" . QUotes are optional if name has no spaces.
        funcom_id
            The Funcom ID of the user to be registered
        game_char_id
            Can be retrieved with v/rcon sql select id from characters where char_name like '%name%'

        Returns
        -------

        """
        #fix me!
        season = 4

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'insert into registration '
                    f'(discord_user,character_name,funcom_id,registration_date,season,game_char_id) '
                    f'values (\'{discord_user.id}\', \'{name}\', \'{funcom_id}\', \'{date.today()}\', '
                    f'{season}, {game_char_id})')
        con.commit()
        con.close()

        await ctx.send(f'Registered character {name} (id {game_char_id} funcom {funcom_id}) '
                       f'to {discord_user.mention}.')

        await ctx.invoke(self.bot.get_command('registrationlist'))

        channel = ctx.author.guild.get_channel(AUTOREG_CHANNEL)
        await channel.send(f'__Character Name:__ {name}\n'
                           f'__Funcom ID:__ {funcom_id}\n'
                           f'__Discord:__ {discord_user.mention}')

        await ctx.author.add_roles(ctx.author.guild.get_role(REG_ROLE))

        return

    @commands.command(name='registrationlist', aliases=['reglist'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
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
        splitOutput = ''
        once = True

        res = db_query(f'select * from registration')

        for x in res:
            outputString += f'{x}\n'

        if outputString:
            if len(outputString) > 10000:
                await ctx.send(f'Too many results!')
                return
            if len(outputString) > 1800:
                workList = outputString.splitlines()
                for items in workList:
                    splitOutput += f'{str(items)}\n'
                    if len(str(splitOutput)) > 1800:
                        if once:
                            once = False
                            await ctx.send(content=str(splitOutput))
                            splitOutput = '(continued)\n'
                        else:
                            await ctx.send(str(splitOutput))
                            splitOutput = '(continued)\n'
                    else:
                        continue
                await ctx.send(str(splitOutput))
            else:
                await ctx.send(str(outputString))
        else:
            await ctx.send(content=f'No matching entries found.')

        return

    @commands.command(name='registrationdelete', aliases=['regdelete', 'regdel'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
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
                res = db_delete_single_record('registration', 'id', recordToDelete)

                await ctx.send(f'Deleted record:\n{res}')

    @commands.command(name='registrationlookup', aliases=['reglook', 'whois', 'who'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def registrationLookup(self, ctx, name: str):
        """- Look up registrations based on partial character name

        Parameters
        ----------
        ctx
        name
            Partial or full character name in quotes

        Returns
        -------

        """

        outputString = 'Matching Registered Characters:\n'
        memberList = get_registration(name)

        if memberList:
            for member in memberList:
                char_id = member[0]
                char_name = member[1]
                discord_id = member[2]
                discord_user = get_member_from_userid(ctx, int(discord_id))
                outputString += f'{char_id} - {char_name} - {discord_user.mention}\n'

            await ctx.send(f'{outputString}')
            return
        else:
            await ctx.send(f'No characters matching the string `{name}`')
            return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Registration(bot))
