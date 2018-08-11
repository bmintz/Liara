import asyncio
import typing

import discord
from discord.ext.commands import Context


class Paginator:
    def __init__(self, ctx: Context, pages: typing.Iterable, *, timeout=300, delete_message=True,
                 delete_message_on_timeout=False):

        self.pages = list(pages)
        self.timeout = timeout
        self._author = ctx.author
        self.target = ctx.channel
        self.delete_msg = delete_message
        self.delete_msg_timeout = delete_message_on_timeout

        self._stopped = None  # we use this later
        self._embed = None
        self._message = None
        self._client = ctx.bot

        self.footer = 'Page {} of {}'
        self.navigation = {
            '\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}': self.first_page,
            '\N{BLACK LEFT-POINTING TRIANGLE}': self.previous_page,
            '\N{BLACK RIGHT-POINTING TRIANGLE}': self.next_page,
            '\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}': self.last_page,
            '\N{BLACK SQUARE FOR STOP}': self.stop
        }

        self._page = None
 
    async def begin(self):
        """Starts pagination"""
        self._stopped = False
        self._embed = discord.Embed(description='Please wait, pages are loading...')
        self._message = await self.target.send(embed=self._embed)
        for button in self.navigation:
            await self._message.add_reaction(button)
        await self.first_page()
        while not self._stopped:
            try:
                reaction, user = await self._client.wait_for('reaction_add', check=self._react_check, timeout=self.timeout)
            except asyncio.TimeoutError:
                await self.stop(delete=self.delete_msg_timeout)
                continue

            reaction = reaction.emoji

            if reaction not in self.navigation:
                continue  # not worth our time

            try:
                await self._message.remove_reaction(reaction, user)
            except discord.Forbidden:
                pass  # oh well, we tried

            await self.navigation[reaction]()

    def _react_check(self, reaction, user):
        if user is None or user != self._author:
            return False
        if reaction.message.id != self._message.id:
            return False
        return bool(discord.utils.find(lambda emoji: reaction.emoji == emoji, self.navigation))
  
    async def stop(self, *, delete=None):
        """Aborts pagination."""
        if delete is None:
            delete = self.delete_msg

        if delete:
            await self._message.delete()
        else:
            await self._clear_reactions()
        self._stopped = True

    async def _clear_reactions(self):
        try:
            await self._message.clear_reactions()
        except discord.Forbidden:
            for button in self.navigation:
                await self._message.remove_reaction(button, self._message.author)

    async def format_page(self):
        self._embed.description = self.pages[self._page]
        self._embed.set_footer(text=self.footer.format(self._page + 1, len(self.pages)))
        await self._message.edit(embed=self._embed)

    async def first_page(self):
        self._page = 0
        await self.format_page()

    async def next_page(self):
        self._page += 1
        if self._page == len(self.pages):  # avoid the inevitable IndexError
            self._page = 0
        await self.format_page()

    async def previous_page(self):
        self._page -= 1
        if self._page < 0:  # ditto
            self._page = len(self.pages) - 1
        await self.format_page()

    async def last_page(self):
        self._page = len(self.pages) - 1
        await self.format_page()


class ListPaginator(Paginator):
    def __init__(self, ctx, _list: list, per_page=10, **kwargs):
        pages = []
        page = ''
        c = 0
        l = len(_list)
        for i in _list:
            if c > l:
                break
            if c % per_page == 0 and page:
                pages.append(page.strip())
                page = ''
            page += '{}. {}\n'.format(c+1, i)

            c += 1
        pages.append(page.strip())
        # shut up, IDEA
        # noinspection PyArgumentList
        super().__init__(ctx, pages, **kwargs)
        self.footer += ' ({} entries)'.format(l)
