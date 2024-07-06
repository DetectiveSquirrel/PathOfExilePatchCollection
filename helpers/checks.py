from discord.ext import commands
import settings
import discord


async def same_server_as_requester(ctx: commands.Context):
    return ctx.guild.id == settings.BASE_SERVER_ID.id


async def requester_is_owner(ctx: commands.Context):
    return ctx.author.id == settings.BASE_OWNER_ID


async def requester_has_role(ctx: commands.Context, role_id: int):
    member = ctx.guild.get_member(ctx.author.id)
    if member is None:
        return False

    role = discord.utils.get(member.roles, id=role_id)
    return role is not None


async def same_server_and_owner(ctx: commands.Context):
    return await same_server_as_requester(ctx) and await requester_is_owner(ctx)
