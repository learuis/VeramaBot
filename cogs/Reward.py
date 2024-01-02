import os
import sqlite3
from datetime import date, timedelta

from discord.ext import commands
from functions.common import custom_cooldown, get_rcon_id, get_single_registration, is_registered
from functions.externalConnections import runRcon, db_query, db_delete_single_record

from dotenv import load_dotenv

load_dotenv('data/server.env')
VETERAN_ROLE = int(os.getenv('VETERAN_ROLE'))
ANNIVERSARY_ROLE = int(os.getenv('ANNIVERSARY_ROLE'))

def add_reward_record(char_id: int, itemId: int, quantity: int, reasonString: str):
    query = (f'insert into event_rewards (reward_date, character_id, reward_material, reward_quantity, '
             f'claim_flag, reward_name) values (\'{date.today()}\', {char_id}, \'{itemId}\', {quantity}, 0, '
             f'\'{reasonString}\')')

    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()
    cur.execute(query)
    con.commit()
    con.close()

class Rewards(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reward', aliases=['give', 'giveitem', 'prize', 'spawnitem'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def giveReward(self, ctx, itemId: int, quantity: int, name: str, *reason):
        """- Gives a reward to the tagged player

        Parameters
        ----------
        ctx
        itemId
            Item ID number to spawn
        quantity
            How many of the item to spawn
        name
            Character name. Must be registered and linked to char id.
        reason
            A message which will pop up for the character in game.

        Returns
        -------

        """
        itemName = ''
        reasonString = ''

        characters = get_single_registration(name)
        if not characters:
            await ctx.send(f'No character named `{name}` registered!')
            return
        else:
            (char_id, char_name, discord_id) = characters

        result = db_query(f'select name from cust_item_xref where template_id = {itemId} limit 1')

        for x in result:
            itemName = x[0]

        for word in reason:
            reasonString += f'{word} '

        add_reward_record(int(char_id), int(itemId), int(quantity), str(reasonString))

        await ctx.reply(f'Added record to the claim table for {name}: {quantity} x {itemName} ({itemId})')

    @commands.command(name='claim')
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def faith(self, ctx):
        """- Delivers item rewards to your character

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        insertResults = []

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character {character.char_name} must be online to claim rewards.')
            return

        results = db_query(f'select record_num, reward_material, reward_quantity, reward_name from event_rewards '
                           f'where character_id = {character.id} '
                           f'and reward_date >= \'{date.today() - timedelta(days = 14)}\' '
                           f'and claim_flag = 0')
        if results:
            outputString = f'You have rewards available to claim! Please wait...\n'
            message = await ctx.reply(f'{outputString}')

            for result in results:
                target = get_rcon_id(character.char_name)
                if not target:
                    await message.edit(f'Character {character.char_name} must be online to claim rewards.')
                    return

                rconCommand = f'con {target} spawnitem {result[1]} {result[2]}'
                rconResponse = runRcon(rconCommand)
                if rconResponse.error == 1:
                    await message.edit(f'Authentication error on {rconCommand}')
                    return

                reward_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
                reward_cur = reward_con.cursor()

                insertResults = reward_cur.execute(f'update event_rewards set claim_flag = 1 '
                                                   f'where record_num = {result[0]}')
                outputString += (f'Granted reward: {result[1]} x {result[2]} for: {result[3]} '
                                 f'to {character.char_name}\n')
                reward_con.commit()
                reward_con.close()

            if insertResults:
                await message.edit(content=f'{outputString}')
                return
            else:
                await message.edit(content=f'Error when granting rewards to {character.char_name}.')
                return
        else:
            await ctx.reply(f'You do not qualify for any rewards at this time.')

    @commands.command(name='claimlist')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def claimList(self, ctx):
        """- Lists all claim records

        Queries the VeramaBot database for all registered characters.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputString = f'reward_date | character_id | reward_material | reward_quantity | claim_flag | reward_name\n'

        res = db_query(f'select * from event_rewards')

        for x in res:
            outputString += f'{x}\n'
        await ctx.send(outputString)
        return

    @commands.command(name='claimdelete')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    async def claimDelete(self, ctx, recordToDelete: int = commands.parameter(default=0)):
        """- Delete a record from the claim database

        Deletes a selected record from the VeramaBot database table 'reward_claim'
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
            await ctx.send(f'Record to delete must be specified. Use `v/help claimdelete`')
        else:
            try:
                int(recordToDelete)
            except ValueError:
                await ctx.send(f'Invalid record number')
            else:
                res = db_delete_single_record('reward_claim', 'record_num', recordToDelete)

                await ctx.send(f'Deleted record:\n{res}')

    """
    @commands.command(name='claim')
    @commands.has_any_role('Outcasts')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(publicChannel)
    async def claim(self, ctx):
    """
    """- Delivers veteran or helper rewards to your character

    Parameters
    ----------
    ctx

    Returns
    -------

    """

    """
    character = is_registered(ctx.author.id)

    if not character:
        await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
        return

    rconCharId = get_rcon_id(character.char_name)
    if not rconCharId:
        await ctx.reply(f'Character {character.char_name} must be online to claim rewards.')
        return

    results = db_query(f'select discord_id from reward_claim '
                       f'where discord_id = {ctx.author.id} and claim_type = {ANNIVERSARY_ROLE}')

    if results:
        for result in results:
            if result[0] == ctx.author.id:
                await ctx.reply(f'No rewards are available for you to claim.')
                return
            else:
                pass
    else:
        role = ctx.author.get_role(ANNIVERSARY_ROLE)
        if role:
            message = await ctx.reply(f'You qualify for the Band of Outcasts 1st Anniversary Reward! '
                                      f'Please wait...')
            rconCommand = f'con {rconCharId} spawnitem 29034 1'
            if rconCommand:
                rconResponse = runRcon(rconCommand)
                if rconResponse.error == 1:
                    await ctx.send(f'Authentication error on {rconCommand}')
                    return

            reward_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
            reward_cur = reward_con.cursor()

            insertResults = reward_cur.execute(f'insert into reward_claim (discord_id,claim_type) '
                                               f'values ({ctx.author.id},{ANNIVERSARY_ROLE})')
            reward_con.commit()

            if insertResults:
                await message.edit(content=f'Granted {role.name} reward to {character.char_name}. '
                                           f'Check your inventory!')
                reward_con.close()
                return
            else:
                await message.edit(content=f'Error when granting {role.name} reward to {character.char_name}.')
                return

        #sql select all records from the faith claim table that match character id and are not older than 2 weeks
        #output those into a list
        #loop through list to grant each item.

        else:
            await ctx.reply(f'No rewards are available for you to claim.')
            return
    """

    """ Veteran reward
    role = ctx.author.get_role(VETERAN_ROLE)
    if role:
        message = await ctx.reply(f'You qualify for a veteran reward! Please wait...')
        rconCommand = f'con {rconCharId} spawnitem 10002 1'
        #rconCommand = f'con {rconCharId} say spawnitem 11108 777'
        if rconCommand:
            rconResponse = runRcon(rconCommand)
            if rconResponse.error == 1:
                await ctx.send(f'Authentication error on {rconCommand}')
                print(f'auth1')
                return

        rconCommand = f'con {rconCharId} spawnitem 10001 1'
        #rconCommand = f'con {rconCharId} say spawnitem 16002 900'
        if rconCommand:
            rconResponse = runRcon(rconCommand)
            if rconResponse.error == 1:
                await ctx.send(f'Authentication error on {rconCommand}')
                print(f'auth2')
                return

        reward_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
        reward_cur = reward_con.cursor()

        insertResults = reward_cur.execute(f'insert into reward_claim (discord_id,claim_type) '
                                           f'values ({ctx.author.id},{VETERAN_ROLE})')
        reward_con.commit()
        """


@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Rewards(bot))
