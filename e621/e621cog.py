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
        verbose     = False

        # Set verbosity to true if the current server has it set as such
        verbose = await self.config.guild(ctx.guild).verbose()

        # Assign tags to URL
        if tags:
            tagSearch += "{} ".format(" ".join(tags))

        tagSearch += " ".join(server_filter)

        # Randomize results
        if randomize:
            tagSearch += " order:random"
        search += parse.quote_plus(tagSearch)

        #Inform users about image retrieval
        message = await ctx.send("Fetching e621 image...")

        # Fetch and display the image or an error
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search, headers={'User-Agent': "Red 3.0 cog/1.0 (Nyashes)"}) as r:
                    website = await r.json()

            if website != []:
                if "success" not in website:
                    imageURL = website[0].get('file_url')
                    if verbose:
                        # Fetches the image ID
                        imageId = website[0].get('id')

                        # Sets the embed title
                        embedTitle = "e621 Image #{}".format(imageId)
        
                        # Sets the URL to be linked
                        embedLink = "https://e621.net/post/show/{}".format(imageId)

                        # Check for the rating and set an appropriate color
                        rating = website[0].get('rating')
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
                        artistList = website[0].get('artist')

                        # Determine if there are multiple artists
                        if len(artistList) == 1:
                            artist = artistList[0].replace('_', ' ')
                        elif len(artistList > 1):
                            artists = ", ".join(artistList).replace('_', ' ')

                        # Sets the tags to be listed
                        tagList = website[0].get('tags').replace(' ', ', ').replace('_', '\_')
                        
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
                        await message.edit(content="Image found.", embed=output)
                    else:
                        # Edits the pending message with the result
                        await message.edit(content=imageURL)
                else:
                    await message.edit(content="{}".format(website["message"]))
            else:
                await message.edit(content="Your search terms '{}' gave no results.".format(search))
        except Exception as e:
            await message.edit(content="{}".format(e))