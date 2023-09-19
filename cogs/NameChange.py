import discord
from discord.ext import commands
from functions.common import (custom_cooldown, checkChannel, is_registered,
                              get_rcon_id, ununicode, update_registered_name)
from functions.externalConnections import runRcon

class NameChange(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='namechange', aliases=['changename', 'setname', 'rename'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(checkChannel)
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

        character = is_registered(discord_user)

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
