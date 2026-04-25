import discord
from discord import app_commands
import os
import random
import asyncio
from datetime import datetime, timedelta

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Campaign state
campaigns = {}

# Game constants
SETTINGS = ["Medieval Fantasy", "Cyberpunk", "Space Opera", "Western", "Pirate"]
DIFFICULTIES = ["Easy", "Normal", "Hard", "Deadly"]
CLASSES = ["Warrior", "Mage", "Rogue", "Paladin", "Ranger"]

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}')

@tree.command(name="start_campaign", description="Start a customized D&D campaign (DM only)")
@app_commands.describe(setting="The theme of the campaign", difficulty="Game difficulty level")
async def start_campaign(interaction: discord.Interaction, setting: str = "Medieval Fantasy", difficulty: str = "Normal"):
    guild_id = interaction.guild_id
    
    if guild_id in campaigns and campaigns[guild_id]['active']:
        await interaction.response.send_message("A campaign is already running!", ephemeral=True)
        return
    
    # Check permissions
    if not interaction.guild.me.guild_permissions.create_public_threads:
        await interaction.response.send_message("❌ I need the 'Create Public Threads' permission to start a campaign!", ephemeral=True)
        return
    # Defer response
    await interaction.response.defer()
    try:
        # Create thread
        thread_name = f"Campaign: {setting} ({difficulty})"
        thread = await interaction.channel.create_thread(name=thread_name, auto_archive_duration=60)
        
        campaigns[guild_id] = {
            'active': True,
            'dm_id': interaction.user.id,
            'thread_id': thread.id,
            'setting': setting,
            'difficulty': difficulty,
            'players': {},
            'enemies': [],
            'in_combat': False,
            'turn_order': [],
            'current_turn_index': 0,
            'last_activity': datetime.now()
        }
        
        embed = discord.Embed(title="⚔️ New Campaign Started!", color=discord.Color.purple())
        embed.add_field(name="Theme", value=setting, inline=True)
        embed.add_field(name="Difficulty", value=difficulty, inline=True)
        embed.description = f"The adventure begins in <#{thread.id}>!\n\n**Players:** Join by using `/create_character` inside the thread."
        
        await interaction.followup.send(embed=embed)
        await thread.send(f"🌌 **Welcome to the {setting} Campaign!**\nDifficulty: {difficulty}\n\nPlayers, please create your characters to begin. The DM (<@{interaction.user.id}>) will decide when the story advances.")
    except discord.Forbidden:
        await interaction.followup.send("❌ I don't have permission to create threads in this channel. Please check my permissions or try a different channel.")
    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")

@tree.command(name="create_character", description="Create your character for the active campaign")
async def create_character(interaction: discord.Interaction, name: str, char_class: str):
    guild_id = interaction.guild_id
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign found!", ephemeral=True)
        return
    
    if interaction.channel_id != campaigns[guild_id]['thread_id']:
        await interaction.response.send_message("Please use this command inside the campaign thread!", ephemeral=True)
        return
    player_id = interaction.user.id
    if player_id in campaigns[guild_id]['players']:
        await interaction.response.send_message("You already have a character!", ephemeral=True)
        return
    # Basic stats
    stats = {
        'HP': 20,
        'MaxHP': 20,
        'Level': 1,
        'XP': 0,
        'Inventory': ["Basic Rations", "Water Skin"],
        'Class': char_class
    }
    
    campaigns[guild_id]['players'][player_id] = {
        'name': name,
        'stats': stats,
        'last_active': datetime.now()
    }
    
    await interaction.response.send_message(f"✅ Character **{name}** the **{char_class}** has been created!")

@tree.command(name="inventory", description="View your character's inventory")
async def inventory(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in campaigns or interaction.user.id not in campaigns[guild_id]['players']:
        await interaction.response.send_message("You don't have a character in this campaign!", ephemeral=True)
        return
    
    player = campaigns[guild_id]['players'][interaction.user.id]
    items = ", ".join(player['stats']['Inventory'])
    await interaction.response.send_message(f"🎒 **{player['name']}'s Inventory:** {items}")

@tree.command(name="roll", description="Roll a dice (e.g., d20)")
async def roll(interaction: discord.Interaction, dice: str = "1d20"):
    try:
        num, sides = map(int, dice.lower().split('d'))
        results = [random.randint(1, sides) for _ in range(num)]
        total = sum(results)
        await interaction.response.send_message(f"🎲 Rolled {dice}: **{total}** ({results})")
    except:
        await interaction.response.send_message("Invalid dice format! Use something like '1d20'.", ephemeral=True)

# Keep bot running
client.run(os.getenv('DISCORD_TOKEN'))
