from __future__ import annotations
import datetime
import logging
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands
from bot import Aswo
import re
from utils import default, error_codes, URL_RE
import socketio
from .views import UserView, RecentView

logger = logging.getLogger(__name__)

class osu(commands.Cog):
    def __init__(self, bot: Aswo):
        self.bot = bot
        self.cached_skins = {}
    
    replay = app_commands.Group(name="replay", description="Allows you to control various aspects of replay uploading")

    async def cog_load(self):
        self.sio = socketio.AsyncClient()
        try:
            await self.sio.connect('https://ordr-ws.issou.best')
        except socketio.exceptions.ConnectionError:
            pass
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            osr = message.attachments[0].url
            if osr.endswith('.osr') or URL_RE.findall(message.content):
                skin = await self.bot.pool.fetchval("SELECT skin_id FROM replay_config WHERE user_id = $1", message.author.id) or 1


                self.bot.logger.info(f"Skin : {skin}")

                async with self.bot.session.post("https://apis.issou.best/ordr/renders", data={"replayURL":osr, "username":"Aswo", "resolution":"1280x720", "skin": skin,"verificationKey":self.bot.replay_key}) as resp:
                    ordr_json = await resp.json()
                
                if ordr_json['errorCode'] in error_codes:
                    return await message.channel.send(error_codes.get(ordr_json['errorCode']))
                    
                mes = await message.channel.send("Osu replay file detected, a rendered replay will be sent shortly! May take a bit so relax :D!\nIll ping you when its finished!")
                render_id = ordr_json['renderID']

                @self.sio.event
                async def render_done_json(data):
                    if data['renderID'] == render_id:
                        data = data
                        self.bot.logger.info(data)
                        await mes.edit(content=f"Here's your rendered video {message.author.mention}!\n{data['videoUrl']}")

                await self.sio.wait()
        except IndexError:
            pass
        
    @app_commands.command()
    async def recent(self, interaction: discord.Interaction, user: Optional[str]):
        user_query = await self.bot.pool.fetchrow("SELECT osu_username FROM osu_user WHERE user_id = $1", interaction.user.id) 
        try:
            if user_query is None and user is None:
                user = await self.bot.osu.fetch_user(interaction.user.display_name)
            elif user_query is not None and user is None:
                user = await self.bot.osu.fetch_user(user_query.get("osu_username"))
            else:
                user = await self.bot.osu.fetch_user(user)
        except Exception as e:
            return await interaction.response.send_message(f"{e}", ephemeral=True)

        recents = await self.bot.osu.fetch_user_score(user.id, type="recent", limit=5, include_fails=True)

        await interaction.response.send_message(view=RecentView(recents))


    @app_commands.command()
    async def user(self, interaction: discord.Interaction, username: str = None):
        """Gets info on osu account"""

        user_query = await self.bot.pool.fetchrow("SELECT osu_username FROM osu_user WHERE user_id = $1", interaction.user.id) 
        try:
            if user_query is None and username is None:
                user = await self.bot.osu.fetch_user(interaction.user.display_name)
            elif user_query is not None and username is None:
                user = await self.bot.osu.fetch_user(user_query.get("osu_username"))
            else:
                user = await self.bot.osu.fetch_user(username)
        except Exception as e:
            return await interaction.response.send_message(f"{e}", ephemeral=True)


        ss_text = user.rank['ss']
        ssh_text = user.rank['ssh']
        s_text = user.rank['s']
        sh_text = user.rank['sh']
        a_text = user.rank['a']
        profile_order ='\n ​ ​ ​ ​ ​ ​ ​ ​  - '.join(x for x in user.profile_order)
        profile_order = profile_order.replace("_", " ")
        joined_date = datetime.datetime.fromisoformat(user.data.get('join_date'))
        country_code = user.country_code if user.country_code not in ["XX", "xx"] else None
        
        view = UserView(interaction.user.id,user)
    
    
        embed = discord.Embed(description=f"**{user.country_emoji if user.country_code not in ['XX', 'xx'] else 'No country'}  | Profile for [{user.username}](https://osu.ppy.sh/users/{user.id})**\n\n▹ **Bancho Rank**: #{user.global_rank:,} ({country_code}#{user.country_rank:,})\n▹ **Join Date**: {discord.utils.format_dt(joined_date)}\n▹ **PP**: {int(user.pp):,} **Acc**: {user.accuracy}%\n▹ **Ranks**: ``SS {ss_text:,}`` | ``SSH {ssh_text:,}`` | ``S {s_text:,}`` | ``SH {sh_text:,}`` | ``A {a_text:,}``\n▹ **Profile Order**: \n** ​ ​ ​ ​ ​ ​ ​ ​  - {profile_order}**", color=0x2F3136)
        embed.set_thumbnail(url=user.avatar_url)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command()
    @app_commands.describe(beatmap="Beatmap to get info on")
    async def beatmap(self, itr: discord.Interaction, beatmap: str):
        matches = re.findall(r"\d+", beatmap)
        if not matches:
            return await itr.response.send_message("No matches\nMake sure to use the second id in the beatmap url (thats the beatmap id) and not the first one (thats the beatmapset id)", ephemeral=True)
    
        try:
            beatmapid = matches[1]
        except IndexError:
            beatmapid = matches[0]
        

        try:
            rbeatmap = await self.bot.osu.fetch_beatmap(beatmapid)
        except Exception as e:
            return await  itr.response.send_message(f"{e}", ephemeral=True)
        
        ranked = discord.utils.format_dt(rbeatmap.ranked_date, style = "R") if rbeatmap.ranked_date else "Not ranked!"
        updated = discord.utils.format_dt(rbeatmap.last_updated, style = "R") if rbeatmap.last_updated else "Has not been updated"
        submitted = discord.utils.format_dt(rbeatmap.submitted_date, style = "R") if rbeatmap.submitted_date else "Not Submitted!"
        creator = await self.bot.osu.fetch_user(rbeatmap.creator)


        embed = discord.Embed(title=f"Info on {rbeatmap.title}", color=0x2F3136)
        embed.add_field(name="Info", value=f"Creator of map: [{creator.username}](https://osu.ppy.sh/users/{creator.id})\nBeatmap ID: {rbeatmap.id}\nSong Artist: {rbeatmap.artist}\nStatus: {rbeatmap.status}\nFavorite count: {rbeatmap.favorite_count:,}\nPlayed count: {rbeatmap.play_count:,}\nMode: {rbeatmap.mode}")
        embed.add_field(name="Gameplay", value=f"All info below was made for the ``{rbeatmap.difficulty} ({rbeatmap.difficulty_rating} stars)`` difficulty\nDrain: {rbeatmap.drain}\nAR: {rbeatmap.ar}\nCS: {rbeatmap.cs}\nBPM: {rbeatmap.bpm}\nMax Combo: {rbeatmap.max_combo:,}")
        embed.add_field(name="Dates", value=f"Ranked date: {ranked}\nSubmitted date: {submitted}\nLast updated: {updated}", inline=False)
        embed.add_field(name="Links", value=f"[Link to beatmap]({rbeatmap.url}) • [kitsu.moe](https://kitsu.moe/d/{rbeatmap.beatmapset_id})")
        embed.set_image(url=rbeatmap.covers("card@2x"))

        await itr.response.send_message(embed=embed)

    @replay.command(description="Allows control on replay settings")
    @app_commands.describe(skin_id = "ID of a skin | https://ordr.issou.best/skins")
    async def config(self, itr: discord.Interaction, skin_id: int):
        try: 
            async with self.bot.session.get("https://apis.issou.best/ordr/skins", params={"pageSize": 400, "page":1}) as resp:
                skins = (await resp.json())['skins']
                self.bot.logger.info((await resp.json())['maxSkins'])

            query = """
                INSERT INTO replay_config (skin_id, user_id) VALUES($1, $2)
                ON CONFLICT(user_id) DO 
                UPDATE SET skin_id = excluded.skin_id
                RETURNING skin_id
            """
            
            await self.bot.pool.execute(query, skin_id, itr.user.id)
            skin_info = {skin['id']:{'preview': skin['highResPreview'], 'skin':skin['skin'], 'download': skin['url'], "author": skin['author']} for skin in skins}
            try:
                skin = skin_info[skin_id]
            except KeyError:
                return await itr.response.send_message("That skin is not accessable or for some reason the ordr api did not give us it, Sorry!", ephemeral=True)

            embed = discord.Embed(title=f"Succesfully made replay skin to {skin['skin']}!")
            embed.add_field(name='Download link', value=f"[Click here to download]({skin['download']})")
            embed.add_field(name="Author", value=skin['author'])
            embed.set_image(url=skin['preview'])

            return await itr.response.send_message(embed=embed)

        except Exception as e:
            return await itr.response.send_message(f"Oh No! an error occured!\n\nError Class: **{e.__class__.__name__}**\n{default.traceback_maker(err=e)}If you're a coder and you think this is a fatal error, DM Sawsha#0598!", ephemeral=True)

    @config.autocomplete('skin_id')
    async def id(self, itr: discord.Interaction, current: str):
        if current in self.cached_skins:
            if current == '':
                return self.cached_skins
            
            return self.cached_skins[current]

        async with self.bot.session.get("https://apis.issou.best/ordr/skins", params={"pageSize": 400, "page":1}) as resp:
            skins = (await resp.json())['skins']

        if current == '':
            return [app_commands.Choice(name=skin['skin'], value=skin['id']) for skin in skins[:25]]

        self.cached_skins[current] = [app_commands.Choice(name=skin['skin'], value=skin['id']) for skin in skins]
         
        return [app_commands.Choice(name=skin['skin'], value=skin['id']) for skin in skins if skin['id'] is int(current)]

    @replay.command()
    async def upload(self, itr: discord.Interaction, file: discord.Attachment):
        skin = await self.bot.pool.fetchval("SELECT skin_id FROM replay_config WHERE user_id = $1", itr.user.id) or 1

        async with self.bot.session.post("https://apis.issou.best/ordr/renders", data={"replayURL": file.url, "username":"Aswo", "resolution":"1280x720", "skin": skin,"verificationKey":self.bot.replay_key}) as resp:
            ordr_json = await resp.json()
            logger.info(ordr_json)
                
        if ordr_json['errorCode'] in error_codes:
            return await itr.response.send_message(error_codes.get(ordr_json['errorCode']))
            
        mes = await itr.response.send_message("Osu replay file detected, a rendered replay will be sent shortly! May take a bit so relax :D!\nIll ping you when its finished!")
        render_id = ordr_json['renderID']

        @self.sio.event
        async def render_done_json(data):
            if data['renderID'] == render_id:
                data = data
                self.bot.logger.info(data)
                await itr.edit_original_response(content=f"Here's your rendered video {itr.user.mention}!\n{data['videoUrl']}")

        await self.sio.wait()


    @app_commands.command()
    async def set_user(self, interaction: discord.Interaction, username: str): 
        """Allows you to set your username""" 
        try:
            query = """
                INSERT INTO osu_user (osu_username, user_id) VALUES($1, $2)
                ON CONFLICT(user_id) DO 
                UPDATE SET osu_username = excluded.osu_username
            """

            await self.bot.pool.execute(query, username, interaction.user.id)

            await interaction.response.send_message(f"Sucessfullly set your osu username to: {username}")
        except Exception as e:
            return await interaction.response.send_message(f"Oh No! an error occured!\n\nError Class: **{e.__class__.__name__}**\n{default.traceback_maker(err=e)}If you're a coder and you think this is a fatal error, DM Sawsha#0598!", ephemeral=True)

async def setup(bot: Aswo):
    await bot.add_cog(osu(bot))	

async def teardown(bot: Aswo):
    cog = osu(bot)
    await cog.sio.disconnect()
    logger.info("Osu cog has been teardowned! sio disconnected")
