import discord
from discord.ext import commands
from functions.common import (custom_cooldown, is_registered,
                              get_rcon_id, ununicode, update_registered_name)
from functions.externalConnections import runRcon

class NameChange(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='idlookup')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def idlookup(self, ctx, char_name: str):
        """ Returns matching IDs and Character Names based on the provided name

        Parameters
        ----------
        ctx
        char_name
            Full or partial character name, use quotes for names with spaces

        Returns
        -------

        """
        outputString = ''
        response = runRcon(f'sql select id, char_name from characters where char_name like \'%{char_name}%\'')

        if response.error == 1:
            outputString += f'\n\nRCON Error.'
            await ctx.reply(content=outputString)
            return
        else:
            outputString = f'Matching ID and characters:\n'
            message = await ctx.reply(content=outputString)
            for x in response.output:
                outputString += f'{x}\n'
                await message.edit(content=outputString)
            return

    @commands.command(name='rename')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def rename(self, ctx, char_id: int, new_name: str):
        """ Renames an unregistered character. Character must be offline to change name

        Parameters
        ----------
        ctx
        char_id
            ID of the character whose name to change
        new_name
            New name. No special characters, use equotes around names with spaces

        Returns
        -------

        """
        outputString = ''

        response = runRcon(f'sql update characters set char_name = \'{new_name}\' where id = {char_id}')

        if response.error == 1:
            outputString += f'\n\nRCON Error.'
            await ctx.reply(content=outputString)
            return
        else:
            for x in response.output:
                outputString += f'{x}\n'
            outputString += (f'Character ID `{char_id}` has been renamed to `{new_name}`. Probably.\n'
                             f'Remember that this does not change their player registration!')
            await ctx.reply(content=outputString)
            return

    @commands.command(name='namechange', aliases=['changename', 'setname'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def changeName(self, ctx, discord_user: discord.Member, new_name: str):
        """- Changes player name

        Usage: v/namechange @discorduser "New Name Here"

        Quotes are optional if the new name does not contain spaces. The new name cannot contain
        any special characters. Spaces and punctuation are OK.

        Parameters
        ----------
        ctx
        discord_user
            Mention the user whose character you want to rename.
        new_name
            Desired name of the character. If there are spaces, use double quotes

        Returns
        -------

        """
        outputString = f'Attempting to change the name of {discord_user.mention} to `{new_name}`...'

        message = await ctx.send(outputString)

        character = is_registered(discord_user.id)

        if character:
            outputString += (f'\n\nFound character `{character.char_name}` with '
                             f'id `{character.id}`.')
            await message.edit(content=outputString)

            character.char_name = ununicode(character.char_name)
            rconId = get_rcon_id(character.char_name)

            if rconId:
                outputString += (f'\n\nName change failed! Character `{character.char_name}` must be '
                                 f'offline to change name!')
                await message.edit(content=outputString)
                return
            else:
                outputString += (f'\nCharacter `{character.char_name}` is offline. Proceeding with name '
                                 f'change to `{new_name}`.')
                await message.edit(content=outputString)
                response = runRcon(f'sql update characters set char_name = \'{new_name}\' where id = {character.id}')

                if response.error == 1:
                    outputString += f'\n\nName change failed! RCON Error.'
                    await message.edit(content=outputString)
                    return
                else:
                    outputString += f'\n\nCharacter `{character.char_name}` has been renamed to `{new_name}`!'
                    await message.edit(content=outputString)
                    update_registered_name(discord_user, new_name)
                    outputString += f'\nUpdated registration table with name `{new_name}` for {discord_user.mention}'
                    return
        else:
            outputString += f'\n\nName change failed! Could not find a character registered to {discord_user.mention}!'
            await message.edit(content=outputString)
            return


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(NameChange(bot))
