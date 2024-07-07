from discord.ext import commands
import discord
import helpers.database
import helpers.pagination
import helpers.checks
import helpers.utils
import settings


class MemberCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="stored_pathofexile_versions", help="List all stored versions"
    )
    @commands.cooldown(
        1, 60, commands.BucketType.guild
    )  # Change cooldown to guild-based
    async def list_versions(self, ctx):
        if not await helpers.checks.same_server_as_requester(ctx):
            return

        if not await helpers.checks.requester_has_role(
            ctx, settings.All_COMMANDS_REQUIRED_ROLE_ID
        ):
            role_name = await helpers.utils.get_role_name(
                ctx.guild, settings.All_COMMANDS_REQUIRED_ROLE_ID
            )
            await ctx.send(f"You do not have the role {role_name}.", ephemeral=True)
            return

        settings.CURSOR.execute("SELECT version, unix_time FROM patch")
        versions = settings.CURSOR.fetchall()

        if not versions:
            await ctx.send("No versions stored.", ephemeral=True)
            return

        # Reverse the versions list to display from newest to oldest
        versions = list(reversed(versions))

        max_version_length = max(len(version) for version, _ in versions)

        async def get_page(page_index):
            results_per_page = 15
            start = (page_index - 1) * results_per_page
            end = start + results_per_page
            page_versions = versions[start:end]
            total_pages = helpers.pagination.Pagination.compute_total_pages(
                len(versions), results_per_page
            )

            version_list = "\n".join(
                [
                    f"**Version:** `{version.ljust(max_version_length)}` | **Stored:** <t:{unix_time}:R> <t:{unix_time}>"
                    for version, unix_time in page_versions
                ]
            )

            embed = discord.Embed(
                title=f"Versions (Page {page_index}/{total_pages})",
                description=version_list,
                color=discord.Color.blue(),
            )

            if settings.MEGA_LINK_ENABLED:
                embed.add_field(
                    name="Binaries:",
                    value=f"[*MEGA link to all.*]({settings.MEGA_LINK})",
                    inline=False,
                )

            return embed, total_pages

        view = helpers.pagination.Pagination(ctx.interaction, get_page)
        await view.navigate()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"This command is on cooldown. Please try again after {error.retry_after:.2f} seconds.",
                ephemeral=True,
            )
        else:
            raise error


async def setup(bot):
    await bot.add_cog(MemberCommands(bot))
