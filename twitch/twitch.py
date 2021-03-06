from discord.ext import commands
from .utils.chat_formatting import *
import re
from .utils import checks
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
import os
import asyncio
from copy import deepcopy
import aiohttp
import logging
import discord
import datetime
import traceback
import json
import time

class Twitch:
    def __init__(self, bot):
        self.bot = bot
        self.intro_message = None
        self.twitch_streams = dataIO.load_json("data/streams/twitch.json")
        self.settings = dataIO.load_json("data/streams/settings.json")
        self.permitted_role_admin = "Admin"

        self.stream_channel = "288915802135199754"  # live server
        self.dev_channel = "185833952278347793"  # live server
        self.server_id = "184694956131221515"  # live server
        self.check_delay = 60  # live delay

        # self.stream_channel = "295033190870024202"  # dev server
        # self.dev_channel = "288790607663726602"  # dev server
        # self.server_id = "215477025735966722"  # dev server
        # self.check_delay = 5    # debug delay
        # self.twitch_online_debug = False

    @commands.group(name="twitch", pass_context=True)
    async def twitch(self, ctx):
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                if ctx.invoked_subcommand is None:
                    await send_cmd_help(ctx)
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    @twitch.command(name="set_channel", pass_context=True)
    async def set_channel(self, ctx, channel):
        """Sets the streaming channel.
        """
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                self.stream_channel = channel
                await self.bot.say("Channel sucessfully assigned.")
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    @twitch.command(name="alert", pass_context=True)
    async def alert(self, ctx, stream: str):
        """Adds/removes twitch alerts from the current channel"""
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                stream = escape_mass_mentions(stream)
                regex = r'^(https?\:\/\/)?(www\.)?(twitch\.tv\/)'
                stream = re.sub(regex, '', stream)

                session = aiohttp.ClientSession()
                url = "https://api.twitch.tv/kraken/streams/" + stream
                header = {'Client-ID': self.settings.get("TWITCH_TOKEN", "")}
                try:
                    async with session.get(url, headers=header) as r:
                        data = await r.json()
                    await session.close()
                    if r.status == 400:
                        await self.bot.say("Owner: Client-ID is invalid or not set. "
                                           "See `{}streamset twitchtoken`"
                                           "".format(ctx.prefix))
                        return
                    elif r.status == 404:
                        await self.bot.say("That stream doesn't exist.")
                        return
                except:
                    await self.bot.say("Couldn't contact Twitch API. Try again later.")
                    return

                done = False

                for i, s in enumerate(self.twitch_streams):
                    if s["NAME"] == stream:
                        self.twitch_streams.remove(s)
                        await self.bot.say("Alert has been removed "
                                           "from the stream channel.")
                        done = True

                if not done:
                    self.twitch_streams.append(
                        {"CHANNEL": self.stream_channel, "IMAGE": None, "LOGO": None,
                         "NAME": stream, "STATUS": None, "ALREADY_ONLINE": False,
                         "GAME": None, "VIEWERS": None, "LANGUAGE": None,
                         "MESSAGE": None})
                    await self.bot.say("Alert activated. I will notify the stream channel "
                                       "everytime {} is live.".format(stream))

                dataIO.save_json("data/streams/twitch.json", self.twitch_streams)
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    @twitch.command(name="stop", pass_context=True)
    async def stop_alert(self, ctx):
        """Stops all streams alerts in the stream channel"""
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                channel = ctx.message.channel

                to_delete = []

                for s in self.twitch_streams:
                    if channel.id in s["CHANNEL"]:
                        to_delete.append(s)

                for s in to_delete:
                    self.twitch_streams.remove(s)

                dataIO.save_json("data/streams/twitch.json", self.twitch_streams)

                await self.bot.say("There will be no more stream alerts in the stream "
                                   "channel.")
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    @twitch.command(name="reset", pass_context=True)
    async def reset(self, ctx, user : str=None):
        """Resets all user settings.
        """
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                userFound = False
                if (user == "bot"):
                    self.intro_message = None
                else:
                    for stream in self.twitch_streams:
                        if (user):
                            if (stream["NAME"] == user):
                                stream["MESSAGE"] = None
                                stream["ALREADY_ONLINE"] = False
                                stream["CHANNEL"] = self.stream_channel
                                userFound = True
                        else:
                            stream["MESSAGE"] = None
                            stream["ALREADY_ONLINE"] = False
                            stream["CHANNEL"] = self.stream_channel

                    if (user):
                        if (userFound):
                            await self.bot.say("Reset complete.")
                        else:
                            await self.bot.say("User does not exist!")
                    else:
                        await self.bot.say("Reset complete.")
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    @twitch.command(name="list", pass_context=True)
    async def list(self, ctx):
        """Lists all user entries.
        """
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                message = []
                message.append("```\n")
                if self.check_channel(ctx):
                    if self.check_permission(ctx) or ctx.message.author == cyphon:
                        if len(self.twitch_streams) > 0:
                            for stream in self.twitch_streams:
                                message.append(stream["NAME"] + "\n")
                        else:
                            message.append("No streams found!")
                message.append("```")
                output = ''.join(message)
                await self.bot.say(output)
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    @twitch.command(name="info", pass_context=True)
    async def info(self, ctx, user : str=None):
        """Lists a user's details.
        """
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        message = []
        message.append("```\n")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                if user:
                    for stream in self.twitch_streams:
                        if stream["NAME"] == user:
                            message.append("Stream name: " + str(stream["NAME"]) + "\n")

                            if stream["IMAGE"]:
                                message.append("Image URL: " + str(stream["IMAGE"]) + "\n")
                            else:
                                message.append("Image URL: N/A\n")

                            if stream["LOGO"]:
                                message.append("Logo URL: " + str(stream["LOGO"] + "\n"))
                            else:
                                message.append("Logo URL: N/A\n")

                            if stream["CHANNEL"]:
                                message.append("Assigned channel ID: " + str(stream["CHANNEL"]) + "\n")
                            else:
                                message.append("Assigned channel ID: N/A\n")

                            if stream["STATUS"]:
                                message.append("Status: " + str(stream["STATUS"]) + "\n")
                            else:
                                message.append("Status: N/A\n")

                            if stream["ALREADY_ONLINE"]:
                                message.append("ALREADY_ONLINE: " + str(stream["ALREADY_ONLINE"]) + "\n")
                            else:
                                message.append("ALREADY_ONLINE: N/A\n")

                            if stream["GAME"]:
                                message.append("Game: " + str(stream["GAME"]) + "\n")
                            else:
                                message.append("Game: N/A\n")

                            if stream["VIEWERS"]:
                                message.append("Viewers: " + str(stream["VIEWERS"]) + "\n")
                            else:
                                message.append("Viewers: N/A\n")

                            if stream["LANGUAGE"]:
                                message.append("Language: " + str(stream["LANGUAGE"]) + "\n")
                            else:
                                message.append("Language: N/A\n")

                            if stream["MESSAGE"]:
                                message.append("Message ID: " + str(stream["MESSAGE"]) + "\n")
                            else:
                                message.append("Message ID: N/A\n")

                            message.append("```\n")
                            output = ''.join(message)
                            await self.bot.say(output)

                else:
                    await self.bot.say("Please provide a user!")
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    def display_errors(self, stream):
        message = []
        message.append("```\n")

        message.append("Stream name: " + str(stream["NAME"]) + "\n")

        if stream["IMAGE"]:
            message.append("Image URL: " + str(stream["IMAGE"]) + "\n")
        else:
            message.append("Image URL: N/A\n")

        if stream["LOGO"]:
            message.append("Logo URL: " + str(stream["LOGO"] + "\n"))
        else:
            message.append("Logo URL: N/A\n")

        if stream["CHANNEL"]:
            message.append("Assigned channel ID: " + str(stream["CHANNEL"]) + "\n")
        else:
            message.append("Assigned channel ID: N/A\n")

        if stream["STATUS"]:
            message.append("Status: " + str(stream["STATUS"]) + "\n")
        else:
            message.append("Status: N/A\n")

        if stream["ALREADY_ONLINE"] or stream["ALREADY_ONLINE"] == False:
            message.append("ALREADY_ONLINE: " + str(stream["ALREADY_ONLINE"]) + "\n")
        else:
            message.append("ALREADY_ONLINE: N/A\n")

        if stream["GAME"]:
            message.append("Game: " + str(stream["GAME"]) + "\n")
        else:
            message.append("Game: N/A\n")

        if stream["VIEWERS"]:
            message.append("Viewers: " + str(stream["VIEWERS"]) + "\n")
        else:
            message.append("Viewers: N/A\n")

        if stream["LANGUAGE"]:
            message.append("Language: " + str(stream["LANGUAGE"]) + "\n")
        else:
            message.append("Language: N/A\n")

        if stream["MESSAGE"]:
            message.append("Message ID: " + str(stream["MESSAGE"]) + "\n")
        else:
            message.append("Message ID: N/A\n")

        message.append("```\n")
        output = ''.join(message)

        return output

    def check_channel(self, ctx):
        if ctx.message.channel.id == self.dev_channel:
            return True

        return False

    def check_permission(self, ctx):
        server_roles = [role for role in ctx.message.server.roles if not role.is_everyone]
        admin = discord.utils.get(server_roles, name=self.permitted_role_admin)

        user_roles = ctx.message.author.roles

        if admin in user_roles:
            return True

        return False

    @twitch.command()
    @checks.is_owner()
    async def twitchtoken(self):
        """Sets the Client-ID for Twitch

        https://blog.twitch.tv/client-id-required-for-kraken-api-calls-afbb8e95f843"""
        self.settings["TWITCH_TOKEN"] = "6mmlypg9emj6jebbpylmlpejwxj2pn"
        dataIO.save_json("data/streams/settings.json", self.settings)
        await self.bot.say('Twitch Client-ID set.')
        
    async def twitch_online(self, stream):
        session = aiohttp.ClientSession()
        url = "https://api.twitch.tv/kraken/streams/" + stream["NAME"]
        header = {'Client-ID': self.settings.get("TWITCH_TOKEN", "")}
        try:
            async with session.get(url, headers=header) as r:
                if r.status == 400:
                    return 400
                elif r.status == 404:
                    return 404
                elif r.status == 500:
                    return 500
                elif r.status == 502:
                    return 502
                elif r.status == 504:
                    return 504

                text = await r.text()
                data = await r.json()
            await session.close()

            if data["stream"]:
                if data["stream"]["game"]:
                    stream["GAME"] = data["stream"]["game"]
                else:
                    stream["GAME"] = "N/A"

                if data["stream"]["viewers"]:
                    stream["VIEWERS"] = data["stream"]["viewers"]
                else:
                    stream["VIEWERS"] = "0"

                if data["stream"]["channel"]["language"]:
                    stream["LANGUAGE"] = data["stream"]["channel"]["language"].upper()
                else:
                    stream["LANGUAGE"] = "N/A"

                if data["stream"]["preview"]["medium"]:
                    stream["IMAGE"] = data["stream"]["preview"]["medium"]
                else:
                    stream["IMAGE"] = None

                if data["stream"]["channel"]["logo"]:
                    stream["LOGO"] = data["stream"]["channel"]["logo"]
                else:
                    stream["LOGO"] = None

                if data["stream"]["channel"]["status"]:
                    stream["STATUS"] = data["stream"]["channel"]["status"]
                else:
                    stream["STATUS"] = "N/A"

                return True

            else:
                return False

        except json.decoder.JSONDecodeError:
            await session.close()
            cyphon = discord.utils.get(self.bot.get_server(self.server_id).members, id="186835826699665409")

            output = self.display_errors(stream)
            trcbck = traceback.format_exc()
            await self.bot.send_message(
                cyphon,
                trcbck + "\n" + output + "\n r.status: " + str(r.status))

            with open("data/streams/debug.txt", "w") as file:
                file.write(text)
            file.close()
            await self.bot.send_file(cyphon, "data/streams/debug.txt")

            return "error"

        except asyncio.TimeoutError:
            cyphon = discord.utils.get(self.bot.get_server(self.server_id).members, id="186835826699665409")

            trcbck = traceback.format_exc()
            await self.bot.send_message(
                cyphon,
                "Error caught!\n" + trcbck)

            return "error"

        except Exception:
            cyphon = discord.utils.get(self.bot.get_server(self.server_id).members, id="186835826699665409")

            output = self.display_errors(stream)
            trcbck = traceback.format_exc()
            await self.bot.send_message(
                cyphon,
                trcbck + "\n" + output + "\n r.status: " + str(r.status))

            dataIO.save_json("data/streams/debug.json", data)
            await self.bot.send_file(cyphon, "data/streams/debug.json")

            return "error"

    @twitch.command(name="restart", pass_context=True)
    async def restart(self, ctx):
        cyphon = discord.utils.get(ctx.message.server.members, id="186835826699665409")

        if self.check_channel(ctx):
            if self.check_permission(ctx) or ctx.message.author == cyphon:
                loop = asyncio.get_event_loop()
                loop.create_task(self.stream_checker())
                await self.bot.say("Twitch task was successfully restarted!")
            else:
                await self.bot.send_message(ctx.message.author, "You don't have permission to execute that command.")

    # DEBUG
    # @twitch.command(name="toggle", pass_context=True)
    # async def toggle(self):
    #     self.twitch_online_debug = not self.twitch_online_debug

    # DEBUG
    # async def twitch_online(self, stream):
    #     return self.twitch_online_debug

    async def stream_checker(self):
        CHECK_DELAY = self.check_delay
        counter = 0

        try:
            to_delete = []
            channel = self.bot.get_channel(self.stream_channel)
            async for message in self.bot.logs_from(channel):
                to_delete.append(message)

            await self.mass_purge(to_delete)

            while self == self.bot.get_cog("Twitch"):

                # print("ALIVE %s!" % counter)  # DEBUG
                # counter += 1  # DEBUG
                while True:
                    try:
                        if not self.intro_message:
                            await self.bot.send_message(
                                self.bot.get_channel(self.stream_channel),
                                "Welcome to " + self.bot.get_channel(self.stream_channel).mention + "! Find some new awesome streamers or see current tournaments!"
                                                                                                    "\n\n*To be added to this channel please ping a staff member.*")
                            await self.bot.send_message(
                                self.bot.get_channel(self.stream_channel),
                                "``Last check at: " + str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d, %H:%M:%S')) + " UTC+2``")
                            async for message in self.bot.logs_from(self.bot.get_channel(self.stream_channel), limit=1):
                                self.intro_message = message.id
                        else:
                            channel = self.bot.get_channel(self.stream_channel)
                            message = await self.bot.get_message(channel, self.intro_message)
                            await self.bot.edit_message(message,
                                                        "``Last check at: " + str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d, %H:%M:%S')) + " UTC+2``")
                    except discord.errors.NotFound:
                        self.intro_message = None
                        to_delete = []
                        channel = self.bot.get_channel(self.stream_channel)
                        async for message in self.bot.logs_from(channel):
                            to_delete.append(message)

                        await self.mass_purge(to_delete)
                        continue
                    except Exception:
                        cyphon = discord.utils.get(self.bot.get_server(self.server_id).members, id="186835826699665409")

                        output = self.display_errors(stream)
                        trcbck = traceback.format_exc()
                        await self.bot.send_message(
                            cyphon,
                            trcbck + "\n" + output)

                    break

                old = deepcopy(self.twitch_streams)

                for stream in self.twitch_streams:
                    online = await self.twitch_online(stream)

                    messageError = True
                    while messageError:
                        messageError = False
                        if online is True and not stream["ALREADY_ONLINE"]:
                            try:
                                stream["ALREADY_ONLINE"] = True
                                channel_obj = self.bot.get_channel(stream["CHANNEL"])
                                if channel_obj is None:
                                    continue
                                can_speak = channel_obj.permissions_for(channel_obj.server.me).send_messages
                                if channel_obj and can_speak:
                                    data = discord.Embed(title=stream["STATUS"],
                                                         timestamp=datetime.datetime.utcnow(),
                                                         colour=discord.Colour(value=int("05b207", 16)),
                                                         url="http://www.twitch.tv/%s" % stream["NAME"])
                                    data.add_field(name="Streamer", value=stream["NAME"])
                                    data.add_field(name="Status", value="Online")
                                    data.add_field(name="Game", value=stream["GAME"])
                                    data.add_field(name="Viewers", value=stream["VIEWERS"])
                                    data.set_footer(text="Language: %s" % stream["LANGUAGE"])
                                    if (stream["IMAGE"]):
                                        data.set_image(url=stream["IMAGE"] + "/?_=" + str(int(time.time())))
                                    if (stream["LOGO"]):
                                        data.set_thumbnail(url=stream["LOGO"])

                                    await self.bot.send_message(
                                        self.bot.get_channel(stream["CHANNEL"]),
                                        embed=data)
                                    async for message in self.bot.logs_from(self.bot.get_channel(stream["CHANNEL"]), limit=1):
                                        stream["MESSAGE"] = message.id
                            except Exception:
                                cyphon = discord.utils.get(self.bot.get_server(self.server_id).members, id="186835826699665409")

                                output = self.display_errors(stream)
                                trcbck = traceback.format_exc()
                                await self.bot.send_message(
                                    cyphon,
                                    trcbck + "\n" + output)

                        elif online is True and stream["ALREADY_ONLINE"]:
                            try:
                                data = discord.Embed(title=stream["STATUS"],
                                                     timestamp=datetime.datetime.utcnow(),
                                                     colour=discord.Colour(value=int("05b207",16)),
                                                     url="http://www.twitch.tv/%s" % stream["NAME"])
                                data.add_field(name="Streamer", value=stream["NAME"])
                                data.add_field(name="Status", value="Online")
                                data.add_field(name="Game", value=stream["GAME"])
                                data.add_field(name="Viewers", value=stream["VIEWERS"])
                                data.set_footer(text="Language: %s" % stream["LANGUAGE"])
                                if (stream["IMAGE"]):
                                    data.set_image(url=stream["IMAGE"] + "/?_=" + str(int(time.time())))
                                if (stream["LOGO"]):
                                    data.set_thumbnail(url=stream["LOGO"])

                                channel = self.bot.get_channel(stream["CHANNEL"])
                                message = await self.bot.get_message(channel, stream["MESSAGE"])

                                await self.bot.edit_message(message, embed=data)
                            except discord.errors.HTTPException:
                                messageError = True
                            except discord.errors.NotFound:
                                messageError = True
                                stream["ALREADY_ONLINE"] = False
                            except Exception:
                                cyphon = discord.utils.get(self.bot.get_server(self.server_id).members, id="186835826699665409")

                                output = self.display_errors(stream)
                                trcbck = traceback.format_exc()
                                await self.bot.send_message(
                                    cyphon,
                                    trcbck + "\n" + output)

                        else:
                            if stream["ALREADY_ONLINE"] and not online:
                                stream["ALREADY_ONLINE"] = False
                                try:
                                    # data = discord.Embed(title=stream["STATUS"],
                                    #                      timestamp=datetime.datetime.now(),
                                    #                      colour=discord.Colour(value=int("990303", 16)),
                                    #                      url="http://www.twitch.tv/%s" % stream["NAME"])
                                    # data.add_field(name="Status", value="Offline")
                                    # data.set_footer(text="Language: %s" % stream["LANGUAGE"])
                                    # if (stream["LOGO"]):
                                    #     data.set_thumbnail(url=stream["LOGO"])
                                    #
                                    channel = self.bot.get_channel(stream["CHANNEL"])
                                    message = await self.bot.get_message(channel, stream["MESSAGE"])

                                    await self.bot.delete_message(message)
                                except discord.errors.NotFound:
                                    continue
                                except Exception:
                                    cyphon = discord.utils.get(self.bot.get_server(self.server_id).members,
                                                               id="186835826699665409")

                                    output = self.display_errors(stream)
                                    trcbck = traceback.format_exc()
                                    await self.bot.send_message(
                                        cyphon,
                                        trcbck + "\n" + output)

                                stream["MESSAGE"] = None

                        await asyncio.sleep(0.5)

                if old != self.twitch_streams:
                    dataIO.save_json("data/streams/twitch.json", self.twitch_streams)

                await asyncio.sleep(CHECK_DELAY)

        except Exception:
            cyphon = discord.utils.get(self.bot.get_server(self.server_id).members, id="186835826699665409")

            trcbck = traceback.format_exc()
            await self.bot.send_message(
                cyphon,
                trcbck)

    async def mass_purge(self, messages):
        while messages:
            if len(messages) > 1:
                await self.bot.delete_messages(messages[:100])
                messages = messages[100:]
            else:
                await self.bot.delete_message(messages[0])
                messages = []
            await asyncio.sleep(1.5)

def check_folders():
    if not os.path.exists("data/streams"):
        print("Creating data/streams folder...")
        os.makedirs("data/streams")


def check_files():
    f = "data/streams/twitch.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty twitch.json...")
        dataIO.save_json(f, [])

    f = "data/streams/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty settings.json...")
        dataIO.save_json(f, {})



def setup(bot):
    logger = logging.getLogger('aiohttp.client')
    logger.setLevel(50)  # Stops warning spam
    check_folders()
    check_files()
    n = Twitch(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n.stream_checker())
    bot.add_cog(n)
