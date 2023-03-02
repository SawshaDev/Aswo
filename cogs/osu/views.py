from __future__ import annotations
import logging
import typing
import discord
from osu import User, Beatmapset, Beatmap, Score
from typing import List
import datetime

logger = logging.getLogger(__name__)

class UserSelect(discord.ui.Select['UserView']):
    def __init__(self, user: User):
        self.user = user
        options = [
            discord.SelectOption(label='Account Avatar', description=f'Shows the avatar of: {user.username}'),
            discord.SelectOption(label='Info', description=f'Info about: {user.username}'),
            discord.SelectOption(label="Statistics", description=f"Statistics about {user.username}"),
            discord.SelectOption(label="Beatmaps", description=f"Beatmaps {user.username} has.")
        ]

        super().__init__(min_values=1, max_values=1, options=options, custom_id="OsuSelectID")

    async def callback(self, interaction: discord.Interaction):      
        await interaction.response.defer()
    
        if self.values[0] == "Beatmaps":
            embed = discord.Embed(color=0x2F3136)
            favorite: List[Beatmapset] = await interaction.client.osu.fetch_user_beatmaps(self.user.id, type="favourite", limit=5)
            embed.add_field(name="Favorite", value='\n'.join(f"[{beatmap.title}](https://osu.ppy.sh/beatmapsets/{beatmap.id})" for beatmap in favorite) if len(favorite) != 0 else "No Favorite Beatmaps!")
            await interaction.edit_original_response(embed=embed)
   
        if self.values[0] == "Account Avatar":
            embed = discord.Embed(color=0x2F3136)
            avatar_url = self.user.avatar_url

            embed.title = f"{self.user.username}'s Osu avatar"
            embed.set_image(url=avatar_url)

            await interaction.edit_original_response(embed=embed, view = UserView(interaction.user.id,self.user))

        if self.values[0] == "Statistics":
            embed = discord.Embed(title=f"{self.user.username}'s Statistics", color=0x2F3136)
            max_combo = self.user.max_combo
            play_style = ', '.join(self.user.playstyle) if type(self.user.playstyle) is list else f"{self.user.username} has no playstyles selected"
            embed.add_field(name="Total Statistics", value=f"Total Hits: {self.user.total_hits:,}\nTotal Score: {self.user.total_score:,}\nMaximum Combo: {max_combo:,}\nPlay Count: {self.user.play_count:,}", inline=True)
            embed.add_field(name="Play Styles", value=f"Play Styles: {play_style}\nFavorite Play Mode: {self.user.playmode}", inline=True)
            await interaction.edit_original_response(embed=embed, view = UserView(interaction.user.id,self.user))    

        if self.values[0] == "Info":
            embed = discord.Embed(color=0x2F3136)
            view = UserView(interaction.user.id,self.user)
            
            ss_text = self.user.rank['ss']
            ssh_text = self.user.rank['ssh']
            s_text = self.user.rank['s']
            sh_text = self.user.rank['sh']
            a_text = self.user.rank['a']
            profile_order ='\n ​ ​ ​ ​ ​ ​ ​ ​  - '.join(x for x in self.user.profile_order)
            profile_order = profile_order.replace("_", " ")
            joined_date = datetime.datetime.fromisoformat(self.user.data.get('join_date'))
            country_code = self.user.country_code if self.user.country_code not in ["XX", "xx"] else "No country"
            embed.description = f"**{self.user.country_emoji if self.user.country_code not in ['XX', 'xx'] else 'No country'} | Profile for [{self.user.username}](https://osu.ppy.sh/users/{self.user.id})**\n\n▹ **Bancho Rank**: #{self.user.global_rank:,} ({country_code}#{self.user.country_rank:,})\n▹ **Join Date**: {discord.utils.format_dt(joined_date)}\n▹ **PP**: {int(self.user.pp):,} **Acc**: {self.user.accuracy}%\n▹ **Ranks**: ``SS {ss_text:,}`` | ``SSH {ssh_text:,}`` | ``S {s_text:,}`` | ``SH {sh_text:,}`` | ``A {a_text:,}``\n▹ **Profile Order**: \n** ​ ​ ​ ​ ​ ​ ​ ​  - {profile_order}**"
            embed.set_thumbnail(url=self.user.avatar_url)
            await interaction.edit_original_response(embed=embed, view=view)

class UserView(discord.ui.View):
    def __init__(self, author_id: int ,user: User):
        super().__init__(timeout=None)
        self.user = user
        self.author_id = author_id
        # Adds the dropdown to our view object.
        self.add_item(UserSelect(self.user))


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True
        await interaction.response.defer()
        await interaction.followup.send(f"You cant use this as you're not the command invoker, only the author (<@{interaction.guild.get_member(self.author_id).id}>) Can Do This!", ephemeral=True)
        return False


class RecentDropdown(discord.ui.Select['RecentView']):
    def __init__(self, myrecent: typing.List[Score]):
        self.recent = myrecent
        super().__init__(options=[discord.SelectOption(label=f"{count} - {recent.beatmapset.title}", value=recent.id) for count, recent in enumerate(myrecent, start=1)])

    async def callback(self, itr: discord.Interaction):
        await itr.response.defer()


        for score in self.recent:
            if int(self.values[0]) == score.id:
                embed = discord.Embed(color=0x2F3136)
                embed.add_field(name="Statistics", value=f"{score.accuracy * 100:,.2f}\n{score.beatmap.version}")
                await itr.edit_original_response(embed=embed)

class RecentView(discord.ui.View):
    def __init__(self, recent: typing.List[Score]):
        super().__init__(timeout=None)
        self.add_item(RecentDropdown(recent))