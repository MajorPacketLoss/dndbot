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
        'in_combat': False
    }
    
    embed = discord.Embed(title="New Campaign Started!", color=discord.Color.purple())
    embed.add_field(name="Setting", value=setting, inline=True)
    embed.add_field(name="Difficulty", value=difficulty, inline=True)
    embed.description = f"The adventure begins in <#{thread.id}>!"
    
    await interaction.response.send_message(embed=embed)
    await thread.send(f"Welcome adventurers! This is a {difficulty} {setting} campaign. Use `/create_character` to begin.")

@tree.command(name="create_character", description="Create your character for the current campaign")
@app_commands.describe(name="Character name", character_class="Character class")
async def create_character(interaction: discord.Interaction, name: str, character_class: str):
    guild_id = interaction.guild_id
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
        
    if character_class not in CLASSES:
        await interaction.response.send_message(f"Invalid class! Choose: {', '.join(CLASSES)}", ephemeral=True)
        return

    # Random stats
    stats = {
        "HP": 20 if character_class == "Warrior" else 15,
        "Strength": random.randint(10, 18),
        "Intelligence": random.randint(10, 18),
        "Agility": random.randint(10, 18)
    }
    
    campaigns[guild_id]['players'][interaction.user.id] = {
        'name': name,
        'class': character_class,
        'stats': stats,
        'inventory': ["Health Potion", "Small Torch"],
        'last_action': datetime.now()
    }
    
    embed = discord.Embed(title=f"Character Created: {name}", color=discord.Color.green())
    embed.add_field(name="Class", value=character_class)
    for stat, val in stats.items():
        embed.add_field(name=stat, value=val, inline=True)
        
    await interaction.response.send_message(embed=embed)

@tree.command(name="inventory", description="View your inventory")
async def inventory(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in campaigns or interaction.user.id not in campaigns[guild_id]['players']:
        await interaction.response.send_message("You don't have a character!", ephemeral=True)
        return
        
    player = campaigns[guild_id]['players'][interaction.user.id]
    items = ", ".join(player['inventory']) if player['inventory'] else "Empty"
    
    embed = discord.Embed(title=f"{player['name']}'s Inventory", description=items, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@tree.command(name="roll", description="Roll a dice")
async def roll(interaction: discord.Interaction, sides: int = 20):
    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 Rolled a D{sides}: **{result}**")

@tree.command(name="status", description="Show campaign and character status")
async def status(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
        
    camp = campaigns[guild_id]
    embed = discord.Embed(title="Campaign Status", color=discord.Color.blue())
    embed.add_field(name="Setting", value=camp['setting'])
    embed.add_field(name="Difficulty", value=camp['difficulty'])
    
    if interaction.user.id in camp['players']:
        p = camp['players'][interaction.user.id]
        char_info = f"**{p['name']}** ({p['class']})
HP: {p['stats']['HP']}"
        embed.add_field(name="Your Character", value=char_info, inline=False)
        
    await interaction.response.send_message(embed=embed)

# Bot token
TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    client.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in environment.")
