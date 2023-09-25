import os
import sqlite3

from discord.ext import commands
from functions.common import custom_cooldown, modChannel, get_rcon_id, popup_to_player, \
    get_single_registration, is_registered, publicChannel
from functions.externalConnections import runRcon, db_query, db_delete_single_record

from dotenv import load_dotenv

load_dotenv('data/server.env')
VETERAN_ROLE = int(os.getenv('VETERAN_ROLE'))

class Rewards(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reward', aliases=['give', 'giveitem', 'prize', 'spawnitem'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
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

        characters = get_single_registration(name)
        if not characters:
            await ctx.send(f'No character named `{name}` registered!')
            return
        else:
            name = characters[1]

        rconCharId = get_rcon_id(name)

        result = db_query(f'select name from cust_item_xref where template_id = {itemId} limit 1')

        for x in result:
            itemName = x[0]

        reasonString = f'You have been granted {quantity} {itemName} for: '
        for word in reason:
            reasonString += f'{word} '

        rconCommand = f'con {rconCharId} spawnitem {itemId} {quantity}'
        rconResponse = runRcon(rconCommand)

        if rconResponse.error == 1:
            await ctx.send(f'Authentication error on {rconCommand}')
        else:
            for x in rconResponse.output:
                await ctx.send(f'Gave `{quantity} {str(itemName)} (item id {itemId})` to `{name}`.'
                               f'\nRcon command output:{x}\nMessaged {name}: {reasonString}')
                popup_to_player(name, reasonString)

    @commands.command(name='claim')
    @commands.has_any_role('Admin', 'Moderator', 'bot_tester')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
    async def claim(self, ctx):
        """- Delivers veteran or helper rewards to your character

        Parameters
        ----------
        ctx

        Returns
        -------

        """

        async def is_online():
            rcon_id = get_rcon_id(character.char_name)
            if not id:
                await ctx.reply(f'Character {character.char_name} must be online to claim rewards.')
                print(f'offline')
                return
            else:
                return rcon_id

        print('got in code')
        character = is_registered(ctx.author.id)

        if not character:
            await ctx.reply(f'Could not find a character registered to {ctx.author.mention}.')
            print(f'missingreg')
            return

        rconCharId = get_rcon_id(character.char_name)
        if not rconCharId:
            await ctx.reply(f'Character {character.char_name} must be online to claim rewards.')
            print(f'offline')
            return

        results = db_query(f'select discord_id from reward_claim '
                           f'where discord_id = {ctx.author.id} and claim_type = {VETERAN_ROLE}')

        if results:
            for result in results:
                print(result)
                if result[0] == ctx.author.id:
                    await ctx.reply(f'No rewards are available for you to claim.')
                    print(f'no_rewards')
                    return
                else:
                    print('why are you here?')
                    pass
        else:
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

                if insertResults:
                    await message.edit(content=f'Granted {role.name} reward to {character.char_name} .TEST')
                    reward_con.close()
                    print(f'granted')
                    return
                else:
                    await message.edit(content=f'Error when granting {role.name} reward to {character.char_name}. TEST')
                    print(f'error')
                    return
            else:
                await ctx.reply(f'No rewards are available for you to claim.')
                return

    @commands.command(name='claimlist')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(publicChannel)
    async def claimList(self, ctx):
        """- Lists all claim records

        Queries the VeramaBot database for all registered characters.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        outputString = f'discord_id | claim_role_id\n'

        res = db_query(f'select * from reward_claim')

        for x in res:
            outputString += f'{x}\n'
        await ctx.send(outputString)
        return

    @commands.command(name='claimdelete')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(custom_cooldown, type=commands.BucketType.user)
    @commands.check(modChannel)
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

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Rewards(bot))
