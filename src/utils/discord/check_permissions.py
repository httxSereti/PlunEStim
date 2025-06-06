import nextcord

async def check_permission(
    ctx: nextcord.Interaction, 
    permission: str,
) -> bool:
    """
    Check if Interaction author can perform this action.
    Args:
        ctx: discord context
        permission: permission required

    Returns: 
        true if authorized
    """    
    if permission == "administrator" and ctx.user and ctx.user.id in ctx.client.administrators:
        return True
    
    embed: nextcord.Embed = nextcord.Embed(
        title="**Permission Error**",
        description="You don't have the permission to perform this action!",
        color=nextcord.Color.red()
    )
    
    if ctx.user:
        embed.add_field(
            name="User:",
            value=f"<@{ctx.user.id}>",
            inline=True
        )
    
    embed.add_field(
        name="Permission:",
        value=f"```{permission}```",
        inline=True
    )
    
    await ctx.response.send_message(embed=embed)
    return False
