from discord import PartialEmoji, TextChannel, Embed
from discord.ext.commands import Context
from dislash import SelectOption, SelectMenu, MessageInteraction, SlashInteraction
from utils.bot_helper import prefix, set_prefix, get_faculty_roles
from utils.database import DB


class Commands:
    @staticmethod
    async def faculty_roles(ctx: SlashInteraction):
        options = []
        with DB.cursor() as cur:
            cur.execute("SELECT * FROM faculties order by title")
            for row in cur.fetchall():
                emoji = None
                try:
                    for e in ctx.guild.emojis:
                        if e.name.lower() == row['icon'].lower():
                            emoji = e
                except:
                    pass
                options.append(
                    SelectOption(
                        row['title'].strip(),
                        row['role'],
                        emoji=PartialEmoji(
                            name=emoji.name if emoji else None,
                            id=emoji.id if emoji else None
                        ) if emoji else None
                    )
                )

        options = SelectMenu(
            options=options,
            custom_id='facultiesSelect',
            max_values=1,
            placeholder='Please select your faculty'
        )
        msg = await ctx.channel.send(
            content="Please select your LU faculty (Choose your current/latest one)",
            components=[options]
        )
        with DB.cursor() as cur:
            cur.execute("INSERT INTO messages (channel, message, type) VALUES (?, ?, ?)", (msg.channel.id, msg.id, 'facultiesSelect'))

    @staticmethod
    async def on_faculty_role(ctx: MessageInteraction, selected: SelectOption):
        faculty_roles = []
        with DB.cursor() as cur:
            cur.execute("SELECT * FROM faculties order by title")
            for row in cur.fetchall():
                faculty_roles.append(row['role'])

        selected_role = int(selected.value)
        user_roles = [i for i in ctx.author.roles if i.id in faculty_roles and i.id != selected_role]

        await ctx.author.remove_roles(*user_roles, reason="Updated from roles dropdown")

        try:
            selected_role = ctx.guild.get_role(selected_role)
            await ctx.author.add_roles(selected_role, reason="Updated from roles dropdown")
        except Exception as e:
            print(e)

        await ctx.reply('Your roles were updated', ephemeral=True, hide_user_input=True)
        await Commands.update_faculty_stats(ctx)

    @staticmethod
    async def faculty_stats(ctx: SlashInteraction):
        roles = get_faculty_roles(ctx)
        embed = Embed(color=0xeaaa00)
        embed.title = 'Current count of faculty members in this server'
        for title, icon, role in roles:
            embed.add_field(
                name=f"{icon if icon else ''} {title}",
                value=f"{len(role.members)}",
                inline=True
            )
        msg = await ctx.channel.send(embed=embed)

        with DB.cursor() as cur:
            cur.execute("INSERT INTO messages (channel, message, type) VALUES (?, ?, ?)", (msg.channel.id, msg.id, 'facultiesStats'))

    @staticmethod
    async def update_faculty_stats(ctx):
        roles = get_faculty_roles(ctx)

        roles = sorted(roles, key=lambda x: len(x[2].members), reverse=True)

        embed = Embed(color=0xeaaa00)
        embed.title = 'Current count of faculty members in this server'
        for title, icon, role in roles:
            embed.add_field(
                name=f"{icon if icon else ''} {title}",
                value=f"{len(role.members)}",
                inline=True
            )
        with DB.cursor() as cur:
            cur.execute("SELECT * FROM messages")
            for row in cur.fetchall():
                if row['type'] == 'facultiesStats':
                    try:
                        chat = ctx.guild.get_channel(row['channel'])
                        msg = chat.get_partial_message(row['message'])
                        if msg:
                            await msg.edit(embed=embed)
                    except Exception as e:
                        pass
