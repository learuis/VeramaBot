import hashlib
import io
import random
import os

import discord
from discord.ext import commands
from functions.common import custom_cooldown, is_registered, get_rcon_id, set_bot_config, get_bot_config, \
    no_registered_char_reply, check_channel, flatten_list, eld_transaction, get_balance
from functions.externalConnections import runRcon, notify_all, db_query

from dotenv import load_dotenv

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='boss')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def boss(self, ctx):
        """- Spawns a random Siptah boss at cursor position.

        Uses RCON to spawn a random Siptah boss at the location your target is currently pointing at

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        monsterlist = []

        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        file = io.open('data/boss_py.dat', mode='r')

        for line in file:
            monsterlist.append(line)

        file.close()

        monster = random.choice(monsterlist)
        monster = f'dc spawn exact {monster}'

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character {character.char_name} must be online to spawn bosses')
            return
        else:
            runRcon(f'con {rconCharId} {monster}')

            await ctx.send(f'Spawned `{monster}` at `{character.char_name}\'s` position')
            return

    @commands.command(name='startevent', aliases=['endevent'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def startevent(self, ctx, location: str = commands.parameter(default='0')):
        """
        Sets event location. Use quotes around coordinates like \"x y z\". Use v/endevent to disable.
        Parameters
        ----------
        ctx
        location
            as: x y z

        Returns
        -------

        """
        if location == '0':
            set_bot_config('event_location', str(location))
            await ctx.send(f'Event Teleport Flag has been disabled!')
        else:
            currentSetting = set_bot_config('event_location', str(location))
            await ctx.send(f'Event Teleport Flag has been enabled, destination: {currentSetting}!')

    @commands.command(name='checkdragon')
    @commands.has_any_role('Moderator')
    @commands.check(check_channel)
    async def checkdragon(self, ctx, discord_user: discord.Member = None, set_claim: str = f''):
        """

        Parameters
        ----------
        ctx
        discord_user
        set_claim

        Returns
        -------

        """
        if not discord_user:
            output = db_query(False, f'select dragons.*, registration.character_name from dragons left join registration on dragons.discord_id = registration.discord_user where claimed is null and paid is not null')
            if output:
                await ctx.reply(output)
                return
            else:
                await ctx.reply(f'All dragons that have been paid for have been claimed!')
                return

        dragon_record = db_query(False, f'select discord_id, dragon_type, paid, claimed from dragons where discord_id = {discord_user.id} limit 1')
        if dragon_record:
            dragon_list = flatten_list(dragon_record)
            print(dragon_list)
            discord_id, dragon_type, paid, claimed = dragon_list
            if claimed:
                await ctx.reply(f'{discord_user.mention} has already `CLAIMED` their dragon!')
                return
            else:
                if 'claim' in set_claim:
                    if paid:
                        db_query(True, f'update dragons set claimed = 1 where discord_id = {discord_user.id}')
                        await ctx.reply(f'{discord_user.mention} - `{dragon_type} Dragon Hatchling` has been marked as `CLAIMED`!')
                        return
                    else:
                        await ctx.reply(f'{discord_user.mention} has `NOT PAID` for their `{dragon_type} Dragon Hatchling` yet. It must be purchased before marking it as claimed.')
                        return
                if paid:
                    await ctx.reply(f'{discord_user.mention} has `PAID` for a `{dragon_type} Dragon Hatchling` but `DID NOT` receive it yet.')
                    return
                else:
                    await ctx.reply(f'{discord_user.mention} is entitled to a `{dragon_type} Dragon Hatchling`, but has `NOT PAID` yet.')
                    return
        else:
            await ctx.reply(f'{discord_user.mention} has not started the dragon purchase process yet. Direct them to use `v/dragon`')
            return



    @commands.command(name='dragon')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def dragon(self, ctx, confirm: str = ''):
        """

        Parameters
        ----------
        ctx
        confirm

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        output_string = ''

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            return

        # code = hashlib.md5(str(ctx.author.id).encode('utf-8')).hexdigest()
        # hex_value = code.encode('utf-8').hex()

        dragon_cost = int(get_bot_config(f'dragon_cost'))
        dragon_record = db_query(False, f'select discord_id, dragon_type, paid, claimed from dragons where discord_id = {ctx.author.id} limit 1')
        if dragon_record:
            dragon_list = flatten_list(dragon_record)
            print(dragon_list)
            discord_id, dragon_type, paid, claimed = dragon_list
            if claimed:
                await ctx.reply(f'You have already claimed your dragon!')
                return
            else:
                if 'White' in dragon_type:
                    output_string = f'You are entitled to purchase a `White Dragon Hatchling` due to 3 Year Band of Outcasts celebration.\n\n'
                    message = await ctx.reply(f'{output_string}')
                else:
                    output_string = f'You are entitled to purchase a `Green Dragon Hatchling`.\n\n'
                    message = await ctx.reply(f'{output_string}')
                if paid:
                    output_string += f'Your dragon has been paid for but not yet claimed. It can be claimed by tagging @Moderator.'
                    await message.edit(content=f'{output_string}')
                    return
                else:
                    if 'confirm' in confirm:
                        balance = get_balance(character)
                        if balance >= dragon_cost:
                            eld_transaction(character, f'Dragon Purchase', -dragon_cost, f'raw')
                            db_query(True, f'update dragons set paid = 1 where discord_id = {ctx.author.id} limit 1')
                            output_string = f'Dragon Purchase has been completed. Tag @Moderator to claim it (pending mod availability)!'
                            await message.edit(content=f'{output_string}')
                            return
                        else:
                            output_string += f'Insufficient decaying eldarium balance! Current Balance: `{balance}` | Needed: `{dragon_cost}`'
                            await message.edit(content=f'{output_string}')
                            return
                    else:
                        output_string += f'Purchasing a dragon costs `{dragon_cost}` Decaying Eldarium. If you are sure you want to purchase one, use `v/dragon confirm`'
                        await message.edit(content=f'{output_string}')
                        return
        else:
            # they arent in the table yet:
            db_query(True, f'insert or replace into dragons(discord_id, dragon_type, paid, claimed) values ({character.discord_id}, \'Green\', NULL, NULL)')
            output_string = (f'You are entitled to purchase a `Green Dragon Hatchling`.\n\n'
                             f'Purchasing a dragon costs `{dragon_cost}` Decaying Eldarium. If you are sure you want to purchase one, use `v/dragon confirm`')
            await ctx.reply(f'{output_string}')
            return

            # claimed = flatten_list(claimed)
            # print(claimed)
            # print(claimed[1])
            # if claimed[1] and claimed[2]:
            #     await ctx.reply(f'Dragon is already claimed.')
            #     return
            # elif claimed[1] and not claimed[2]:
            #     named_properly = runRcon(f'sql select object_id from properties where name like \'%PetName%\' and hex(value) like \'%{claimed[3]}%\'')
            #     named_properly.output.pop(0)
            #     if named_properly.output:
            #         outputString = f'Found a pet with the correct name and it is ready to be converted.'
            #     else:
            #         outputString = (f'Could not find a pet with the correct name. '
            #                         f'Name a level 0 pet with this code (must be exact, case sensitive!) to convert '
            #                         f'it to a dragon hatchling. ')
            #     await ctx.author.send(f'Dragon code has been generated but not yet claimed.'
            #                           f'\n\n```{claimed[1]}```\n\n{outputString}\n\n'
            #                           f'Conversion happens at server restarts and is done manually by '
            #                           f'Verama, so please be patient! :)')
            #     await ctx.reply(f'Dragon code has been generated but not yet claimed. '
            #                     f'Check your DMs!\n\n{outputString}')
            #     return


        # db_query(True, f'insert or ignore into dragon_claim (discord_id, code, claimed, hex_value) '
        #                f'values ({ctx.author.id}, \'{code}\', 0, \'{hex_value}\')')
        # await ctx.author.send(f'Dragon Code generated!\n```{code}```\n\nName a level 0 pet with this code '
        #                 f'(must be exact, case sensitive!) to convert it to a dragon hatchling. '
        #                       f'Conversion happens at server restarts and is done manually by Verama, so please be patient! :)')
        # await ctx.reply(f'Dragon code has been generated. Check your DMs!')

        return
    @commands.command(name='event', aliases=['market'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def event(self, ctx):
        """- Teleports you to an active event location.

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        location = get_bot_config('event_location')
        if location == '0':
            await ctx.reply(f'This command can only be used during an event!')
            return

        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to player {ctx.author.mention}! '
            #                 f'Please register here: {channel.mention} ')
            return
        else:
            name = character.char_name

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character `{name}` must be online to teleport to an event!')
            return
        else:
            # print(f'{name} - slot {rconCharId} event TP')
            runRcon(f'con {rconCharId} TeleportPlayer {location}')
            await ctx.reply(f'Teleported `{name}` to the event location.')
            return

    @commands.command(name='alert')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def Alert(self, ctx, style: int = commands.parameter(default=5),
                    text1: str = commands.parameter(default=f'-Event-'),
                    text2: str = commands.parameter(default=f'Siptah beasts roam the Exiled Lands')):
        """
        - Sends an alert to all online players

        Parameters
        ----------
        ctx
        style
        text1
        text2

        Returns
        -------

        """

        notify_all(style, f'{text1}', f'{text2}')
        await ctx.send(f'Sent alert style {style} with message: {text1} {text2}')

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Events(bot))
