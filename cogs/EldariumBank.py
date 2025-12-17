import math

from discord.ext import commands

from functions.common import *
from dotenv import load_dotenv

from functions.common import eld_transaction, get_balance, sufficient_funds
from functions.externalConnections import db_query

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))

class EldariumBank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='balance', aliases=['checkbalance', 'eld', 'bal'])
    @commands.check(check_channel)
    @commands.dynamic_cooldown(one_per_min, type=commands.BucketType.user)
    async def balance(self, ctx, discord_user: discord.Member = None):
        """
        Displays current eldarium balance

        Parameters
        ----------
        ctx
        discord_user

        Returns
        -------

        """
        if discord_user:
            character = is_registered(int(discord_user.id))
        else:
            character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        balance = int(get_balance(character))
        await ctx.reply(f'{character.char_name}\'s current eldarium balance: {balance}')

    @commands.command(name='transaction', aliases=['tx'])
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    @commands.dynamic_cooldown(one_per_min, type=commands.BucketType.user)
    async def transaction(self, ctx, discord_user: discord.Member, reason: str, amount: int = 0):
        """
        Eldarium bank transaction v/tx Name Reason Amount

        Parameters
        ----------
        ctx
        discord_user
            Mention the discord user
        reason
            Explanation for transaction
        amount
            Positive or negative integer

        Returns
        -------

        """
        balance = 0

        character = is_registered(int(discord_user.id))

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
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

    @commands.command(name='pay', aliases=['transfer', 'sendmoney'])
    @commands.check(check_channel)
    async def pay(self, ctx, payee: discord.Member, amount: str = 0, confirm: str = ''):
        """ - Transfers decaying eldarium to another registered player.

        v/pay @someone 200 bars

        Parameters
        ----------
        ctx
        payee
            Discord @ tag the user you want to transfer to
        amount
            Specify the amount to be transferred
        confirm
            Type confirm to execute the transfer

        Returns
        -------

        """
        eld_type = f'raw'

        payor = is_registered(ctx.author.id)
        if not payor:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        payee = is_registered(payee.id)
        if not payee:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {payee.mention}! Visit {reg_channel.mention}')
            return

        try:
            amount = int(amount)
            print(amount)
        except ValueError:
            await ctx.reply(f'Must transfer eldarium in whole number amounts > 0!')
            return

        if amount <= 0:
            await ctx.reply(f'Must transfer eldarium in whole number amounts > 0!')
            return

        amount_string = f'{amount} Decaying Eldarium'

        check_balance = sufficient_funds(payor, abs(amount), eld_type)
        if check_balance:
            if 'confirm' not in confirm:
                await ctx.reply(f'This command will transfer `{amount_string}` to `{payee.char_name}`. '
                                f'If this is correct, add `confirm` to the end of the command to execute the transfer.')
                return
            new_balance = eld_transaction(payor, f'Transfer to {payee.char_name}', -amount, eld_type)
            payee_balance = eld_transaction(payee, f'Transfer from {payor.char_name}', amount, eld_type)

            await ctx.reply(
                f'Transaction complete: Transferred {amount_string} to {payee.char_name}\'s account\n'
                f'`{payor.char_name}\'s` New Balance: {new_balance} Decaying Eldarium\n'
                f'`{payee.char_name}\'s` New Balance: {payee_balance} Decaying Eldarium\n')
            return
        else:
            balance = int(get_balance(payor))
            await ctx.reply(f'Insufficient funds! Available decaying eldarium: {balance}')
            return

    @commands.command(name='withdraw', aliases=['atm'])
    @commands.check(check_channel)
    @commands.dynamic_cooldown(one_per_min, type=commands.BucketType.user)
    async def withdraw(self, ctx, amount = '0', eld_type = 'raw'):
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

        if not amount or not eld_type:
            await ctx.reply(f'Command Format:`v/withdraw <amount> <eld_type> <confirm>`')
            return

        if 'raw' not in eld_type and 'bars' not in eld_type:
            await ctx.reply(f'Error. Must specify `raw` or `bars`.\nCommand Format:`v/withdraw <amount> <eld_type> <confirm>`')
            return

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        try:
            amount = int(amount)
        except ValueError:
            if amount == 'all':
                if eld_type == 'raw':
                    amount = get_balance(character)
                elif eld_type == 'bars':
                    amount = math.floor(get_balance(character) / 2)
                if amount == 0:
                    await ctx.reply(f'You do not have enough decaying eldarium in your account to withdraw that much!')
                    return
                if amount > 1000:
                    await ctx.reply(f'Withdrawals are limited to 1,000 units of currency. '
                                    f'Your withdrawal has been adjusted.')
                    amount = 1000

        if amount <= 0:
            await ctx.reply(f'Must withdraw eldarium in whole number amounts > 0!\nCommand Format:`v/withdraw <amount> <eld_type> <confirm>`')
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
    @commands.check(check_channel)
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
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def transactiondetail(self, ctx, discord_user: discord.Member, transaction_count: int):
        """ Shows the 10 most recent transactions for the named player

        Parameters
        ----------
        ctx
        discord_user
            Mention the discord user
        transaction_count

        Returns
        -------

        """
        message = ''
        character = is_registered(discord_user.id)

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        results = db_query(False, f'select * from bank_transactions where char_id = {character.id}'
                                  f' order by timestamp desc limit {transaction_count}')

        if results:
            for result in results:
                message += f'{result} | <t:{result[4]}>\n'
            await ctx.send(f'{message}')
            return
        else:
            await ctx.send(f'No results returned.')
            return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(EldariumBank(bot))
    