from discord.ext import commands

from cogs.Reward import add_reward_record
from functions.common import *
from dotenv import load_dotenv

from functions.externalConnections import db_query

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))

def get_balance(character):
    balance = 0

    results = db_query(False,
                       f'SELECT balance from bank where char_id = {character.id} and season = {CURRENT_SEASON} limit 1')
    if results:
        balance = int(flatten_list(results)[0])
    return balance

def sufficient_funds(character, debit_amount: int = 0, eld_type: str = 'raw'):

    balance = int(get_balance(character))

    if eld_type == 'bars':
        debit_amount = debit_amount * 2

    if balance >= debit_amount:
        return True
    else:
        return False

def eld_transaction(character, reason: str, amount: int = 0, eld_type: str = 'raw'):

    if eld_type == 'bars':
        amount = amount * 2
        reason += f' (Bars)'
    else:
        reason += f' (DE)'

    db_query(True, f'insert into bank_transactions (season, char_id, amount, reason, timestamp) '
                   f'values ({CURRENT_SEASON}, {character.id}, {amount}, \'{reason}\', \'{int_epoch_time()}\')')
    db_query(True, f'insert or replace into bank (season, char_id, balance) '
                   f'values ({CURRENT_SEASON}, {character.id}, '
                   f'( select sum(amount) from bank_transactions '
                   f'where season = {CURRENT_SEASON} and char_id = {character.id}) )')
    new_balance = get_balance(character)
    return new_balance

class EldariumBank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='balance', aliases=['checkbalance', 'eld', 'bal'])
    @commands.dynamic_cooldown(one_per_min, type=commands.BucketType.user)
    async def balance(self, ctx, name: str = ''):
        """
        Displays current eldarium balance

        Parameters
        ----------
        ctx
        name

        Returns
        -------

        """
        if name:
            registration_record = get_single_registration(name)
            (char_id, char_name, discord_id) = registration_record

            character = is_registered(int(discord_id))
        else:
            character = is_registered(ctx.author.id)

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        balance = int(get_balance(character))
        await ctx.reply(f'{character.char_name}\'s current eldarium balance: {balance}')

    @commands.command(name='transaction', aliases=['tx'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(one_per_min, type=commands.BucketType.user)
    async def transaction(self, ctx, name: str, reason: str, amount: int = 0):
        """
        Eldarium bank transaction v/tx Name Reason Amount

        Parameters
        ----------
        ctx
        name
            Character name
        reason
            Explanation for transaction
        amount
            Positive or negative integer

        Returns
        -------

        """
        balance = 0

        registration_record = get_single_registration(name)
        (char_id, char_name, discord_id) = registration_record

        character = is_registered(int(discord_id))

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        if amount < 0:
            check_balance = sufficient_funds(character, abs(amount))
            if check_balance:
                new_balance = eld_transaction(character, reason, amount)
                await ctx.reply(f'Transaction complete: {amount} decaying eldarium to {character.char_name}\'s account\n'
                                f'New Balance: {new_balance}')
                return
            else:
                balance = int(get_balance(character))
                await ctx.reply(f'Insufficient funds! Available decaying eldarium: {balance}')
                return
        else:
            new_balance = eld_transaction(character, reason, amount)
            await ctx.reply(f'Transaction complete: {amount} decaying eldarium to {character.char_name}\'s account\n'
                            f'New Balance: {new_balance}')
            return

    @commands.command(name='withdraw', aliases=['atm'])
    @commands.dynamic_cooldown(one_per_min, type=commands.BucketType.user)
    async def withdraw(self, ctx, amount: int = 0, eld_type: str = 'raw'):
        """
        Eldarium bank transaction

        Parameters
        ----------
        ctx
        amount
        eld_type
            raw or bars

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        balance = 0
        amount_string = ''

        if 'raw' not in eld_type and 'bars' not in eld_type:
            await ctx.reply(f'Error. Must specify `raw` or `bars`.')
            return

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        if amount <= 0:
            await ctx.reply(f'Must withdraw eldarium in whole number amounts > 0!')
            return
        else:
            check_balance = sufficient_funds(character, abs(amount), eld_type)
            if check_balance:
                new_balance = eld_transaction(character, f'Withdrawal', -amount, eld_type)
                if 'bars' in eld_type:
                    add_reward_record(character.id, 11498, amount, f'Bank Withdrawal: Bars')
                    amount_string = f'{amount} Eldarium Bars'
                else:
                    add_reward_record(character.id, 11499, amount, f'Bank Withdrawal: Raw')
                    amount_string = f'{amount} Decaying Eldarium'

                await ctx.reply(
                    f'Transaction complete: Withdrew {amount_string} from {character.char_name}\'s account\n'
                    f'New Balance: {new_balance} Decaying Eldarium\n'
                    f'Use `v/claim` to collect your {amount} currency.')
                return
            else:
                balance = int(get_balance(character))
                await ctx.reply(f'Insufficient funds! Available decaying eldarium: {balance}')
                return

    @commands.command(name='deposit', aliases=['bank'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.dynamic_cooldown(one_per_min, type=commands.BucketType.user)
    async def deposit(self, ctx):
        """
        Deposits up to 100 decaying eldarium from your inventory to the bank

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        balance = 0
        new_balance = 0
        amount_deposited = 0

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        inventory_count = count_inventory_qty(character.id, 0, 11499)
        if inventory_count == 2:
            await ctx.reply(f'You cannot deposit decaying eldarium in quantities of 1 or 2. Blame Funcom.')
            return
        if not inventory_count:
            await ctx.reply(f'You do not have any decaying eldarium in your main inventory to deposit')
            return
        else:
            message = await ctx.reply(f'Depositing {inventory_count} decaying eldarium from main inventory, '
                                      f'please wait...')
            consume_from_inventory(character.id, character.char_name, 11499)
            eld_transaction(character, f'Deposit', inventory_count)

        # print(f'Initial loop: {inventory_count}')
        # while inventory_count:
        #     eld_transaction(character, f'Deposit', inventory_count)
        #     amount_deposited += inventory_count
        #     consume_from_inventory(character.id, character.char_name, 11499)
        #     inventory_count = count_inventory_qty(character.id, 0, 11499)
        #     print(f'Continuing loop: {inventory_count}')
        # print(f'Loop ended')

        await message.edit(content=f'Transaction complete: Desposited {inventory_count} decaying eldarium '
                           f'to {character.char_name}\'s account\n'
                           f'New Balance: {int(get_balance(character))}\n')

        return

    @commands.command(name='transactiondetail', aliases=['txd'])
    async def transactiondetail(self, ctx, name: str):
        """ Shows the 10 most recent transactions for the named player

        Parameters
        ----------
        ctx
        name
            Character name

        Returns
        -------

        """
        message = ''
        registration_record = get_single_registration(name)
        (char_id, char_name, discord_id) = registration_record

        character = is_registered(int(discord_id))

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        results = db_query(False, f'select * from bank_transactions where char_id = {character.id} '
                                  'order by timestamp desc limit 10')

        if results:
            for result in results:
                message += f'{result}\n'
            await ctx.send(f'{message}')
            return
        else:
            await ctx.send(f'No results returned.')
            return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(EldariumBank(bot))
    