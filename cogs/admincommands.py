from discord.ext import commands
import helpers.database
import helpers.pagination
import helpers.checks
import os
import sys


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="clear_tables",
        description="Clears all data from message_log and patch tables",
    )
    async def clear_all_tables(self, ctx):
        if not await helpers.checks.same_server_as_requester(ctx):
            return

        if not await helpers.checks.requester_is_owner(ctx):
            await ctx.send("You are not the owner of this bot.", ephemeral=True)
            return

        result = await helpers.database.clear_tables()
        await ctx.send(result, ephemeral=True)

    @commands.hybrid_command(name="restart", help="Restart the bot")
    async def restart(self, ctx):
        if not await helpers.checks.same_server_as_requester(ctx):
            return

        if not await helpers.checks.requester_is_owner(ctx):
            await ctx.send("You are not the owner of this bot.", ephemeral=True)
            return

        await ctx.send("Restarting the bot...", ephemeral=True)
        await self.bot.close()
        os.execv(sys.executable, ["python"] + sys.argv)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
