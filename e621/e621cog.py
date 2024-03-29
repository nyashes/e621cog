import discord
from discord.ext import commands
from redbot.core import Config, checks, commands
from urllib import parse
import os
import aiohttp

class E621(commands.Cog):
    def __init__(self):
        self.config = Config.get_conf(self, identifier=5800862169)
        self.default_guild = {
            "verbose": False,
            "split_search": False,
            "server_filter": ["-scat", "-watersport", "-cub"],
        }
        self.default_member = {
            "user_filter": [],
        }
        self.config.register_guild(**self.default_guild)
        self.config.register_member(**self.default_member)
        commands.Cog.__init__(self)

    @commands.command(pass_context=True, no_pm=True)
    async def e621(self, ctx, *text):
        """Retrieves the latest result from e621"""
        if len(text) > 0:
            await fetch_image(self=self, ctx=ctx, randomize=False, tags=text)

    @commands.command(pass_context=True, no_pm=True)
    async def e621r(self, ctx, *text):
        """Retrieves a random result from e621"""
        await fetch_image(self=self, ctx=ctx, randomize=True, tags=text)

    @commands.group(pass_context=True)
    async def e621filter(self, ctx):
        """Manages e621 filters
           Warning: Can be used to allow NSFW images
           Filters automatically apply tags to each search"""

    @e621filter.command(name="add", pass_context=True, no_pm=True)
    @checks.is_owner()
    async def _add_e621filter(self, ctx, filtertag : str):
        """Adds a tag to the server's e621 filter list
           Example: !e621filter add rating:s"""
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.server_filter() as server_filter:
            if len(server_filter) < 50:
                if filtertag not in server_filter:
                    server_filter.append(filtertag)
                    await ctx.send("Filter '{}' added to the server's e621 filter list.".format(filtertag))
                else:
                    await ctx.send("Filter '{}' is already in the server's e621 filter list.".format(filtertag))
            else:
                await ctx.send("This server has exceeded the maximum filters ({}/{}). https://www.youtube.com/watch?v=1MelZ7xaacs".format(len(server_filter), 50))

    @e621filter.command(name="del", pass_context=True, no_pm=True)
    @checks.is_owner()
    async def _del_e621filter(self, ctx, filtertag : str=""):
        """Deletes a tag from the server's e621 filter list
            Without arguments, reverts to the default e621 filter list
            Example: !e621filter del rating:s"""

        guild_group = self.config.guild(ctx.guild)
        async with guild_group.server_filter() as server_filter:
            if len(filtertag) > 0:
                if filtertag in server_filter:
                    server_filter.remove(filtertag)
                    await ctx.send("Filter '{}' deleted from the server's e621 filter list.".format(filtertag))
                else:
                    await ctx.send("Filter '{}' does not exist in the server's e621 filter list.".format(filtertag))
            else:
                    server_filter = self.default_guild
                    await ctx.send("Reverted the server to the default e621 filter list.")

    @e621filter.command(name="list", pass_context=True)
    async def _list_e621filter(self, ctx):
        """Lists all of the filters currently applied to the current server"""
        
        guild_group = self.config.guild(ctx.guild)
        async with guild_group.server_filter() as server_filter:
            filterlist = '\n'.join(sorted(server_filter))
            await ctx.send("e621 filter list contains:```\n{}```".format(filterlist))

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def e621set(self, ctx):
        """Manages e621 settings"""

    @e621set.command(pass_context=True,name="verbose")
    @checks.is_owner()
    async def _verbose_e621set(self, ctx, toggle : str="toggle"):
        """Toggles verbose mode"""
        if toggle.lower() == "on" or toggle.lower() == "true" or toggle.lower() == "enable":
            await self.config.guild(ctx.guild).verbose.set(True)
            await ctx.send("Verbose mode is now enabled.")
        elif toggle.lower() == "off" or toggle.lower() == "false" or toggle.lower() == "disable":
            await self.config.guild(ctx.guild).verbose.set(False)
            await ctx.send("Verbose mode is now disabled.")

    @e621set.command(pass_context=True,name="split_search")
    @checks.is_owner()
    async def _split_search_e621set(self, ctx, toggle : str="toggle"):
        """Toggles split search mode"""
        if toggle.lower() == "on" or toggle.lower() == "true" or toggle.lower() == "enable":
            await self.config.guild(ctx.guild).split_search.set(True)
            await ctx.send("split_search mode is now enabled.")
        elif toggle.lower() == "off" or toggle.lower() == "false" or toggle.lower() == "disable":
            await self.config.guild(ctx.guild).split_search.set(False)
            await ctx.send("split_search mode is now disabled.")

async def sub_fetch_image(self, ctx, limit, tags : list=[]):
    search      = "http://e621.net/post/index.json?limit={}&tags=".format(limit) + " ".join(tags)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search, headers={'User-Agent': "Red 3.0 cog/1.0 (Nyashes)"}) as r:
                website = await r.json()
                statusCode = r.status

        if website != []:
            if "success" not in website:
                return website
            else:
                await ctx.send(content="{} (http returned: {})".format(website["reason"], statusCode))
        else:
            await ctx.send(content="Your search terms '{}' gave no results.".format(search))
    except Exception as e:
        await ctx.send(content="{}".format(e))
    
    return False

async def fetch_image(self, ctx, randomize : bool=False, tags : list=[]):
    guild_group = self.config.guild(ctx.guild)
    async with guild_group.server_filter() as server_filter:
        # Initialize variables
        artist      = "unknown artist"
        artists     = ""
        artistList  = []
        embedLink   = ""
        embedTitle  = ""
        imageId     = ""
        message     = ""
        output      = None
        rating      = ""
        ratingColor = "FFFFFF"
        ratingWord  = "unknown"
        search      = "http://e621.net/post/index.json?limit=1&tags="
        tagSearch   = ""

        # Set verbosity to true if the current server has it set as such
        verbose = await self.config.guild(ctx.guild).verbose()

        # check for split search mode
        split_search = await self.config.guild(ctx.guild).split_search()

        #Inform users about image retrieval
        message = await ctx.send("Fetching e621 image...")
        
        tags = list(tags)
        tags.extend(server_filter)

        if randomize:
            tags.append("order:random")

        # remove duplicates, tags are a limited ressource
        tags = list(dict.fromkeys(tags))

        if not split_search:
            # just take the first result
            result = await sub_fetch_image(self, ctx, 1, tags)
            if not result:
                return await message.edit(content="Error.")
        else:
            special_tags = []
            normal_tags = []
            negative_tags = []
            for tag in tags:
                if ":" in tag or "~" in tag:
                    special_tags.append(tag)
                elif "-" in tag:
                    negative_tags.append(tag[1:])
                else:
                    normal_tags.append(tag)

            while len(special_tags) < 6 and len(normal_tags) > 0:
                special_tags.append(normal_tags.pop(0))

            while len(special_tags) < 6 and len(negative_tags) > 0:
                special_tags.append("-" + negative_tags.pop(0))
                
            website = await sub_fetch_image(self, ctx, max(250, (len(negative_tags) + len(normal_tags)) * 100), special_tags)
            if not website:
                return await message.edit(content="Error.")

            def filter_fun(mt, nt, x):
                normal_set = set(mt)
                negative_set = set(nt)
                current_set = set(x.get('tags').split(' '))
                return normal_set.issubset(current_set) and negative_set.isdisjoint(current_set)

            result = list(filter(lambda x: filter_fun(normal_tags, negative_tags, x), website))
            
            if len(result) == 0:
                return await message.edit(content="Error: split search unsuccessful with {} items and MS='{}', SS='{}', NS='{}'".format(
                    max(250, (len(negative_tags) + len(normal_tags)) * 100)
                    , ", ".join(special_tags)
                    , ", ".join(normal_tags)
                    , ", ".join(negative_tags)))

        result = result[0]
        
        imageURL = result.get('file_url')
        if verbose:
            # Fetches the image ID
            imageId = result.get('id')

            # Sets the embed title
            embedTitle = "e621 Image #{}".format(imageId)

            # Sets the URL to be linked
            embedLink = "https://e621.net/post/show/{}".format(imageId)

            # Check for the rating and set an appropriate color
            rating = result.get('rating')
            if rating == "s":
                ratingColor = "00FF00"
                ratingWord = "safe"
            elif ratingWord == "q":
                ratingColor = "FF9900"
                ratingWord = "questionable"
            elif rating == "e":
                ratingColor = "FF0000"
                ratingWord = "explicit"

            # Grabs the artist(s)
            artistList = result.get('artist')

            # Determine if there are multiple artists
            if len(artistList) == 1:
                artist = artistList[0].replace('_', ' ')
            elif len(artistList > 1):
                artists = ", ".join(artistList).replace('_', ' ')

            # Sets the tags to be listed
            tagList = result.get('tags').replace(' ', ', ').replace('_', '\_')
            
            # Initialize verbose embed
            output = discord.Embed(title=embedTitle, url=embedLink, colour=discord.Colour(value=int(ratingColor, 16)))

            # Sets the thumbnail and adds the rating, artist, and tag fields to the embed
            output.add_field(name="Rating", value=ratingWord)
            if artist:
                output.add_field(name="Artist", value=artist)
            elif artist:
                output.add_field(name="Artists", value=artists)
            output.add_field(name="Tags", value=tagList, inline=False)
            output.set_thumbnail(url=imageURL)

            # Edits the pending message with the results
            await message.edit(embed=output)
        else:
            # Edits the pending message with the result
            await message.edit(content=imageURL)