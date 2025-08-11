import discord
import sqlite3
import os
from urllib.parse import urlparse

from discord import ui
from discord.ext import commands
from dotenv import load_dotenv

from functions.common import is_message_deleted, is_registered, get_bot_config, check_channel
from functions.externalConnections import db_query

load_dotenv('data/server.env')
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))
CHARSHEETS_CHANNEL = int(os.getenv('CHARSHEETS_CHANNEL'))
CHARSHEET_HELPCHANNEL = int(os.getenv('CHARSHEET_HELPCHANNEL'))


# noinspection PyUnresolvedReferences
class RoleplayingButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create or Update Character Sheet", style=discord.ButtonStyle.green,
                       custom_id="my_custom_button1")
    async def roleplaying_sheet(self, interaction: discord.Interaction, button: discord.ui.button):
        discord_id = interaction.user.id
        await interaction.response.send_modal(RoleplayingProfile(discord_id))


# noinspection PyUnresolvedReferences
class RoleplayingProfile(ui.Modal, title='NO CHARACTER REGISTERED -> #REGISTER-HERE'):
    # charName = ui.TextInput(label=f'Character Name', placeholder='Type your full, exact in-game character name',
    #                         max_length=60)
    description = ui.TextInput(label=f'NO CHARACTER REGISTERED -> #REGISTER-HERE',
                               placeholder='NO CHARACTER REGISTERED -> #REGISTER-HERE',
                               max_length=600)
    attributes = ui.TextInput(label=f'NO CHARACTER REGISTERED -> #REGISTER-HERE',
                              placeholder='NO CHARACTER REGISTERED -> #REGISTER-HERE',
                              max_length=600)
    drives = ui.TextInput(label=f'NO CHARACTER REGISTERED -> #REGISTER-HERE',
                          placeholder='NO CHARACTER REGISTERED -> #REGISTER-HERE',
                          max_length=600)
    gear = ui.TextInput(label=f'NO CHARACTER REGISTERED -> #REGISTER-HERE',
                        placeholder='NO CHARACTER REGISTERED -> #REGISTER-HERE',
                        max_length=600)
    image = ui.TextInput(label=f'NO CHARACTER REGISTERED -> #REGISTER-HERE',
                         placeholder='NO CHARACTER REGISTERED -> #REGISTER-HERE',
                         max_length=600,
                         required=False)

    def __init__(self, discord_id):
        super().__init__()
        self.discord_id = discord_id
        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(
            f'select discord_id, message_id, character_name, description, attributes, drives, gear, image '
            f'from roleplaying_info where discord_id = \'{self.discord_id}\' and season = \'{CURRENT_SEASON}\'')
        result = cur.fetchone()
        con.close()

        if result:
            # self.charName.default = f'{result[2]}'
            self.description.default = f'{result[3]}'
            self.attributes.default = f'{result[4]}'
            self.drives.default = f'{result[5]}'
            self.gear.default = f'{result[6]}'
            self.image.default = f'{result[7]}'

        character = is_registered(self.discord_id)
        if character:
            self.title = f'{character.char_name}'
            self.description.label = f'Description of character'
            self.attributes.label = f'Attributes (Concept, Edges, Flaws)'
            self.drives.label = f'Drives / Goals'
            self.gear.label = f'Gear'
            self.image.label = f'Character Image:'
            self.description.placeholder = f'Type your background / notes here'
            self.attributes.placeholder = f'Type your attributes here'
            self.drives.placeholder = f'Type your drives here'
            self.gear.placeholder = f'Type your gear here'
            self.image.placeholder = f'Type a URL to use as your character image'

    async def on_submit(self, interaction: discord.Interaction):

        channel = interaction.client.get_channel(CHARSHEETS_CHANNEL)

        if not urlparse(str(self.image)):
            self.image = None

        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(f'select message_id from roleplaying_info '
                    f'where discord_id = \'{interaction.user.id}\' and season = \'{CURRENT_SEASON}\'')
        result = cur.fetchone()

        if result:
            message_id = result[0]
        else:
            message_id = 0

        # self.charName = str(self.charName).replace('\'', '')
        self.description = str(self.description).replace('\'', '')
        self.attributes = str(self.attributes).replace('\'', '')
        self.drives = str(self.drives).replace('\'', '')
        self.gear = str(self.gear).replace('\'', '')
        self.image = str(self.image).replace('\'', '')

        # self.charName = str(self.charName).replace('\"', '')
        self.description = str(self.description).replace('\"', '')
        self.attributes = str(self.attributes).replace('\"', '')
        self.drives = str(self.drives).replace('\"', '')
        self.gear = str(self.gear).replace('\"', '')
        self.image = str(self.image).replace('\"', '')

        embed = discord.Embed(title=f'{self.title}',
                              description=f'{self.description}',
                              colour=0x00b0f4)
        embed.add_field(name=f'Attributes',
                        value=f'{self.attributes}',
                        inline=False)
        embed.add_field(name=f'Drives',
                        value=f'{self.drives}',
                        inline=False)
        embed.add_field(name=f'Gear',
                        value=f'{self.gear}',
                        inline=False)
        embed.set_image(url=f'{self.image}')
        embed.add_field(name=f'Played By',
                        value=f'{interaction.user.mention}',
                        inline=False)

        character = is_registered(interaction.user.id)
        if character:
            print(f'registered')
            await interaction.response.send_message(
                content=f'Your character sheet has been saved. You can find it in the '
                        f'<#{CHARSHEETS_CHANNEL}> channel. If you want to display it '
                        f'on demand in any channel, you can use `v/charsheet`.',
                ephemeral=True)
        else:
            await interaction.response.send_message(content='You must register a character before you can create '
                                                            'a character sheet. Your character sheet has not been '
                                                            'saved.', ephemeral=True)
            print(f'no registation')
            return

        message_does_not_exist = await is_message_deleted(channel, message_id)
        if message_does_not_exist:
            message = await channel.send(embed=embed)
            message_id = message.id
        else:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=embed)
            message_id = message.id

        cur.execute(f'replace into roleplaying_info'
                    f'(discord_id, message_id, character_name, season, description, attributes, drives, gear, image) '
                    f'values (\'{interaction.user.id}\',\'{message_id}\',\'{character.char_name}\','
                    f'\'{CURRENT_SEASON}\',\'{self.description}\',\'{self.attributes}\',\'{self.drives}\','
                    f'\'{self.gear}\', \'{self.image}\')')

        con.commit()
        con.close()


class Roleplaying(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='rp_prep')
    @commands.is_owner()
    @commands.check(check_channel)
    async def rp_prep(self, ctx: commands.Context):
        await ctx.send(f'OPTIONAL - Click the button below to create your RP character sheet. '
                       f'It\'s very brief and simple! Please note - you must '
                       f'register your character first!\n\nDetailed information is available here: '
                       f'<#{CHARSHEET_HELPCHANNEL}>',
                       view=RoleplayingButton())

    @commands.command(name='charsheet', aliases=['charactersheet', 'rpcard'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def rpcard(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        cur = con.cursor()

        cur.execute(
            f'select character_name, description, attributes, drives, gear, image '
            f'from roleplaying_info where discord_id = \'{ctx.author.id}\' and season = \'{CURRENT_SEASON}\'')
        result = cur.fetchone()
        con.close()

        if result:
            embed = discord.Embed(title=f'{result[0]}',
                                  description=f'{result[1]}',
                                  colour=0x00b0f4)
            embed.add_field(name=f'Attributes',
                            value=f'{result[2]}',
                            inline=False)
            embed.add_field(name=f'Drives',
                            value=f'{result[3]}',
                            inline=False)
            embed.add_field(name=f'Gear',
                            value=f'{result[4]}',
                            inline=False)
            embed.set_image(url=f'{result[5]}')
            embed.add_field(name=f'Played By',
                            value=f'{ctx.author.mention}',
                            inline=False)

            await ctx.send(embed=embed)
        else:
            await ctx.send(f'You have not yet created a character sheet. Go to <#{CHARSHEETS_CHANNEL}>.')

    @commands.command(name='roleplay', aliases=['rp'])
    @commands.has_any_role('Admin', 'Moderator', 'Roleplay')
    @commands.check(check_channel)
    async def Roleplay(self, ctx):
        """

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputMessage = f'__Online Roleplayers:__\n'

        results = db_query(False, f'select online.char_id, online.char_name, reg.discord_user '
                                  f'from online_character_info as online '
                                  f'left join registration as reg on online.char_id = reg.game_char_id '
                                  f'where reg.season = {CURRENT_SEASON}')

        if not results:
            outputMessage += f'None'
            return

        message = await ctx.reply(f'{outputMessage}')

        for result in results:
            outputMessage += f'\n{result[1]} | <@{result[2]}>'

        await message.edit(content=outputMessage)
        return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Roleplaying(bot))
