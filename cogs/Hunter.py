import os

import discord
from discord.ext import commands

from functions.common import is_registered, get_bot_config, no_registered_char_reply, \
    check_channel, modify_favor, display_quest_text, grant_reward, eld_transaction, get_balance, \
    sufficient_funds, killed_target, set_slayer_target, clear_slayer_target, get_slayer_target, get_notoriety, \
    increase_notoriety, increment_killed_total, grant_slayer_rewards, toggle_arachnophobia, set_slayer_reroll_exclusion, \
    clear_slayer_reroll
from dotenv import load_dotenv

from functions.externalConnections import db_query

load_dotenv('data/server.env')
REGHERE_CHANNEL = int(os.getenv('REGHERE_CHANNEL'))
CURRENT_SEASON = int(os.getenv('CURRENT_SEASON'))
PREVIOUS_SEASON = int(os.getenv('PREVIOUS_SEASON'))


class Hunter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='quarry', aliases=['rq'])
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def quarry(self, ctx, confirm: str = ''):
        """ - Be assigned a different Beast Slayer quarry, costs 50 DE

        Parameters
        ----------
        ctx
        confirm
            Add confirm to execute the command

        Returns
        -------

        """
        character = is_registered(ctx.author.id)

        if not character:
            await no_registered_char_reply(self.bot, ctx)
            # reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            # await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        exclude_target = get_slayer_target(character)
        if not exclude_target:
            await ctx.reply(f'`{character.char_name}` does not currently have a Beast Slayer Quarry! '
                            f'Visit the Profession Hub to be assigned one.')
            return

        if 'confirm' in confirm:
            reason = (f'Quarry Reroll')
            reroll_cost = int(get_bot_config(f'beast_slayer_reroll_cost'))
            amount = -reroll_cost
            reward_quantity = int(get_bot_config(f'beast_slayer_reward'))
            check_balance = sufficient_funds(character, abs(amount))

            if check_balance:
                new_balance = eld_transaction(character, reason, amount)
                set_slayer_reroll_exclusion(character, exclude_target)
                current_target = set_slayer_target(character) #, exclude_target)

                (notorious_target, notorious_multiplier) = increase_notoriety(exclude_target)
                total_bounty = reward_quantity + (reroll_cost * notorious_multiplier)

                await ctx.reply(
                    f'Consumed {abs(amount)} decaying eldarium from {character.char_name}\'s account\n'
                    f'New Balance: {new_balance}\n\n'
                    f'You will not be assigned to slay `{exclude_target.display_name}` again until '
                    f'it has been slain by someone else.\n\n'
                    f'`{character.char_name}` was assigned a new Beast Slayer quarry: `{current_target.display_name}`'
                    f' on <t:{current_target.start_time}:f>.'
                    f'\n\nThe bounty on `{exclude_target.display_name}` has increased to `{total_bounty}` '
                    f'decaying eldarium!')
                return
            else:
                balance = int(get_balance(character))
                await ctx.reply(f'Insufficient funds! Available decaying eldarium: {balance}')
                return

        else:
            await ctx.reply(f'`{character.char_name}`\'s current quarry: `{exclude_target.display_name}`.\n\n'
                            f'This command will clear your quarry and assign you a new one for 50 decaying eldarium. '
                            f'You will not be able to claim any reward for the current quarry, even if you already '
                            f'killed it.\n\nIf you are sure want to be assigned a new quarry, '
                            f'use `v/quarry confirm`.')
            return

    @commands.command(name='notorious')
    @commands.has_any_role('Outcasts')
    @commands.check(check_channel)
    async def notorious(self, ctx):
        """ - Lists the top 10 notorious quarries

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        outputString = '__Notorious Quarries__\n'

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        query = (f'select target_display_name, notoriety from beast_slayer_target_list '
                 f'where notoriety > 0 order by notoriety desc, target_display_name')
        results = db_query(False, f'{query}')
        if not results:
            await ctx.reply(f'There are currently no notorious quarries. '
                            f'When a quarry is re-rolled, notoriety of that quarry is increased.')
            return
        else:
            reroll_cost = int(get_bot_config(f'beast_slayer_reroll_cost'))
            reward_quantity = int(get_bot_config(f'beast_slayer_reward'))
            for result in results:
                display_name, notoriety = result
                total_reward = reward_quantity + (reroll_cost * notoriety)
                outputString += f'`{display_name}` - `{total_reward}` DE\n'

        await ctx.reply(outputString)
        return

    @commands.command(name='adminquarry')
    @commands.has_any_role('Admin', 'Moderator')
    @commands.check(check_channel)
    async def adminquarry(self, ctx, user: discord.Member, option: str = ''):
        """ - Assigns a Beast Slayer task
        
        Parameters
        ----------
        ctx
        user
        option
    
        Returns
        -------
    
        """
        character = is_registered(user.id)

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        if 'new' in option:
            current_target = set_slayer_target(character)
        else:
            current_target = get_slayer_target(character)

        await ctx.reply(f'`{character.char_name}` was assigned a task to slay `{current_target.display_name}`'
                        f' on <t:{current_target.start_time}:f>')

    # @commands.command(name='logkill')
    # @commands.has_any_role('Admin', 'Moderator')
    # @commands.check(check_channel)
    # async def logkill(self, ctx):
    #     """ - Completes a Beast Slayer task
    #
    #     Parameters
    #     ----------
    #     ctx
    #
    #     Returns
    #     -------
    #
    #     """
    #     character = is_registered(ctx.author.id)
    #     outputString = ''
    #
    #     if not character:
    #         reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
    #         await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
    #         return
    #
    #     current_target = get_slayer_target(character)
    #     if killed_target(current_target):
    #         outputString += f'`{character.char_name}` slew `{current_target.target_name}`. Assigning new target!'
    #         new_target = set_slayer_target(character)
    #         outputString += (f'\n\n`{character.char_name}` was assigned a task to slay `{current_target.display_name}`'
    #                          f' on <t:{current_target.start_time}:f>.')
    #         await ctx.reply(outputString)
    #         return
    #     else:
    #         await ctx.reply(f'You have not yet slain `{current_target.target_name}` since it was '
    #                         f'assigned on <t:{current_target.start_time}:f>.')
    #         return

    @commands.command(name='arachnophobia', aliases=['nospiders'])
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def arachnophobia(self, ctx):
        """ - Toggles arachnophobia mode.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        output_string = 'This message should not be displayed!'

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        arachnophobia_flag = toggle_arachnophobia(character)
        if arachnophobia_flag:
            output_string = (f'Arachnophobia mode `enabled` for `{character.id}`! '
                             f'You will not be assigned to kill spiders in the Beast Slayer profession.')
        else:
            output_string = (f'Arachnophobia mode `disabled` for `{character.id}`! '
                             f'You may be assigned to kill spiders in the Beast Slayer profession.')

        await ctx.reply(output_string)
        return


    @commands.command(name='verifyslaying', aliases=['verifyquarry', 'vquarry', 'slay', 'vslay'])
    @commands.check(check_channel)
    @commands.has_any_role('Outcasts')
    async def verifyslaying(self, ctx):
        """ - Verifies that you killed your quarry after it was assigned.

        Parameters
        ----------
        ctx

        Returns
        -------

        """
        character = is_registered(ctx.author.id)
        output_string = 'This message should not be displayed!'
        notorious_multiplier = 0

        if not character:
            reg_channel = self.bot.get_channel(REGHERE_CHANNEL)
            await ctx.reply(f'No character registered to {ctx.message.author.mention}! Visit {reg_channel.mention}')
            return

        current_target = get_slayer_target(character)

        if current_target:
            if killed_target(current_target, character):
                favor_to_give = int(get_bot_config(f'slayer_favor_per_kill'))
                modify_favor(character.id, 'slayer', favor_to_give)

                notorious_target, notorious_multiplier = get_notoriety(current_target)
                if notorious_multiplier > 0:
                    display_quest_text(0, 0, False, character.char_name, 7,
                                       f'Notorious Beast Slain!', f'{current_target.display_name}')
                else:
                    display_quest_text(0, 0, False, character.char_name, 7,
                                       f'Slain', f'{current_target.display_name}')
                output_string = grant_slayer_rewards(character, current_target)
                clear_slayer_reroll(current_target)
                clear_slayer_target(character)
                await ctx.reply(output_string)
                return
            else:
                # print(f'displaying existing quarry')
                display_quest_text(0, 0, False, character.char_name, 6,
                                   f'Quarry:', f'{current_target.display_name}')
                await ctx.reply(f'You have not yet slain `{current_target.display_name}` since it was '
                                f'assigned on <t:{current_target.start_time}:f>.')
                return

        #
        # if current_target:
        #     if killed_target(current_target, character):
        #         reward = int(get_bot_config(f'beast_slayer_reward'))
        #         reroll_cost = int(get_bot_config('beast_slayer_reroll_cost'))
        #         outputString += (f'Your quarry, `{current_target.display_name}`, has been slain! '
        #                          f'You have earned '
        #                          f'`{reward+(reroll_cost*notorious_multiplier)}` decaying eldarium!\n'
        #                          f'Return to the Beast Slayer at the Profession Hub to be assigned a new Quarry.')
        #         await ctx.reply(outputString)
        #         return
        #     else:
        #         await ctx.reply(f'You have not yet slain `{current_target.display_name}` since it was '
        #                         f'assigned on <t:{current_target.start_time}:f>.')
        #         return
        # else:
        #     await ctx.reply(f'`{character.char_name}` does not currently have a Beast Slayer Quarry! '
        #                     f'Visit the Profession Hub to be assigned one.')
        #     return

@commands.Cog.listener()
async def setup(bot):
    await bot.add_cog(Hunter(bot))
