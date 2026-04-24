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
# Format: {
#     guild_id: {
#         'active': True,
#         'dm_id': user_id,
#         'channel_id': channel_id,
#         'players': {user_id: {'name': str, 'last_action': datetime}},
#         'enemies': [{'name': str, 'hp': int}],
#         'in_combat': False
#     }
# }

# Random campaign opening scenarios
CAMPAIGN_STARTS = [
    "You find yourselves in a dim tavern. The barkeep eyes you suspiciously as rain pounds against the windows. A hooded figure approaches your table...",
    "The caravan jolts to a stop. Screams echo from up ahead. Something is blocking the road...",
    "You awaken in a dungeon cell with no memory of how you got here. Footsteps echo down the corridor...",
    "A merchant's ship crashes on an uncharted island. You're stranded with limited supplies and unknown dangers lurking in the jungle...",
    "The king summons you to his chamber. 'Something ancient has awoken,' he whispers, trembling. 'Something that should have stayed buried...'"
]

# Random event types
RANDOM_EVENTS = [
    {'type': 'combat', 'desc': 'Enemies appear!'},
    {'type': 'discovery', 'desc': 'You discover something interesting...'},
    {'type': 'npc', 'desc': 'A stranger approaches...'},
    {'type': 'trap', 'desc': 'Something seems off about this place...'},
    {'type': 'treasure', 'desc': 'You spot something valuable!'}
]

INACTIVITY_THRESHOLD = 300  # 5 minutes

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}')

@tree.command(name="start_campaign", description="Start a D&D campaign (DM only)")
async def start_campaign(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id in campaigns and campaigns[guild_id]['active']:
        await interaction.response.send_message("A campaign is already running! Use /end_campaign first.", ephemeral=True)
        return
    
    # Random campaign start
    opening = random.choice(CAMPAIGN_STARTS)
    
    campaigns[guild_id] = {
        'active': True,
        'dm_id': interaction.user.id,
        'channel_id': interaction.channel_id,
        'players': {},
        'enemies': [],
        'in_combat': False
    }
    
    embed = discord.Embed(
        title="Campaign Started!",
        description=opening,
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"DM: {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="join", description="Join the campaign")
async def join_campaign(interaction: discord.Interaction, character_name: str):
    guild_id = interaction.guild_id
    
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
    
    campaigns[guild_id]['players'][interaction.user.id] = {
        'name': character_name,
        'last_action': datetime.now()
    }
    
    await interaction.response.send_message(f"{character_name} has joined the adventure!") 

@tree.command(name="next_event", description="Trigger the next random event (DM only)")
async def next_event(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
    
    # Only DM can trigger
    if interaction.user.id != campaigns[guild_id]['dm_id']:
        await interaction.response.send_message("Only the DM can trigger the next event!", ephemeral=True)
        return
    
    # RNG decides what happens
    event = random.choice(RANDOM_EVENTS)
    
    embed = discord.Embed(
        title=f"Random Event: {event['type'].title()}",
        description=event['desc'],
        color=discord.Color.orange()
    )
    
    # If combat, spawn enemies
    if event['type'] == 'combat':
        num_enemies = random.randint(1, 4)
        campaigns[guild_id]['enemies'] = [
            {'name': f"Enemy {i+1}", 'hp': random.randint(20, 50)}
            for i in range(num_enemies)
        ]
        campaigns[guild_id]['in_combat'] = True
        
        enemy_list = "\n".join([f"{e['name']} (HP: {e['hp']})" for e in campaigns[guild_id]['enemies']])
        embed.add_field(name="Enemies", value=enemy_list, inline=False)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="action", description="Take an action")
async def action(interaction: discord.Interaction, description: str):
    guild_id = interaction.guild_id
    
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
    
    if interaction.user.id not in campaigns[guild_id]['players']:
        await interaction.response.send_message("You haven't joined the campaign! Use /join first.", ephemeral=True)
        return
    
    # Update activity
    campaigns[guild_id]['players'][interaction.user.id]['last_action'] = datetime.now()
    char_name = campaigns[guild_id]['players'][interaction.user.id]['name']
    
    await interaction.response.send_message(f"**{char_name}** {description}")

@tree.command(name="attack", description="Attack an enemy")
async def attack(interaction: discord.Interaction, enemy_name: str):
    guild_id = interaction.guild_id
    
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
    
    if not campaigns[guild_id]['in_combat']:
        await interaction.response.send_message("Not in combat!", ephemeral=True)
        return
    
    if interaction.user.id not in campaigns[guild_id]['players']:
        await interaction.response.send_message("You haven't joined!", ephemeral=True)
        return
    
    # Update activity
    campaigns[guild_id]['players'][interaction.user.id]['last_action'] = datetime.now()
    
    # Find enemy
    enemy = None
    for e in campaigns[guild_id]['enemies']:
        if e['name'].lower() == enemy_name.lower():
            enemy = e
            break
    
    if not enemy:
        await interaction.response.send_message(f"Enemy '{enemy_name}' not found!", ephemeral=True)
        return
    
    # Roll damage
    damage = random.randint(5, 20)
    enemy['hp'] -= damage
    char_name = campaigns[guild_id]['players'][interaction.user.id]['name']
    
    result = f"**{char_name}** attacks {enemy['name']} for {damage} damage!"
    
    if enemy['hp'] <= 0:
        campaigns[guild_id]['enemies'].remove(enemy)
        result += f"\n{enemy['name']} is defeated!"
        
        if len(campaigns[guild_id]['enemies']) == 0:
            campaigns[guild_id]['in_combat'] = False
            result += "\n\n**Combat ended! All enemies defeated!**"
    else:
        result += f"\n{enemy['name']} has {enemy['hp']} HP remaining."
    
    await interaction.response.send_message(result)
    
    # Enemy turn (targets active players preferentially)
    if campaigns[guild_id]['in_combat']:
        await asyncio.sleep(2)
        await enemy_turn(interaction.channel, guild_id)

async def enemy_turn(channel, guild_id):
    if not campaigns[guild_id]['in_combat']:
        return
    
    # Get active players (acted recently)
    now = datetime.now()
    active_players = []
    inactive_players = []
    
    for user_id, player_data in campaigns[guild_id]['players'].items():
        time_since_action = (now - player_data['last_action']).total_seconds()
        if time_since_action < INACTIVITY_THRESHOLD:
            active_players.append((user_id, player_data))
        else:
            inactive_players.append((user_id, player_data))
    
    # Enemy AI: preferentially target active players
    # 80% chance to target active, 20% inactive
    if active_players and random.random() < 0.8:
        target_id, target_data = random.choice(active_players)
    elif inactive_players:
        target_id, target_data = random.choice(inactive_players)
    elif active_players:
        target_id, target_data = random.choice(active_players)
    else:
        return  # No players to target
    
    enemy = random.choice(campaigns[guild_id]['enemies'])
    damage = random.randint(3, 15)
    
    await channel.send(f"{enemy['name']} attacks **{target_data['name']}** for {damage} damage!")

@tree.command(name="end_campaign", description="End the campaign (DM only)")
async def end_campaign(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
    
    if interaction.user.id != campaigns[guild_id]['dm_id']:
        await interaction.response.send_message("Only the DM can end the campaign!", ephemeral=True)
        return
    
    campaigns[guild_id]['active'] = False
    await interaction.response.send_message("Campaign ended!")

@tree.command(name="status", description="Show campaign status")
async def status(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    
    if guild_id not in campaigns or not campaigns[guild_id]['active']:
        await interaction.response.send_message("No active campaign!", ephemeral=True)
        return
    
    campaign = campaigns[guild_id]
    
    embed = discord.Embed(
        title="Campaign Status",
        color=discord.Color.blue()
    )
    
    # Players
    player_list = "\n".join([
        f"{p['name']} (Active: {'Yes' if (datetime.now() - p['last_action']).total_seconds() < INACTIVITY_THRESHOLD else 'No'})"
        for p in campaign['players'].values()
    ]) or "No players"
    embed.add_field(name="Players", value=player_list, inline=False)
    
    # Combat status
    if campaign['in_combat']:
        enemy_list = "\n".join([f"{e['name']} (HP: {e['hp']})" for e in campaign['enemies']])
        embed.add_field(name="Enemies", value=enemy_list, inline=False)
    else:
        embed.add_field(name="Combat", value="Not in combat", inline=False)
    
    await interaction.response.send_message(embed=embed)

# Bot token
TOKEN = os.environ.get('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError('DISCORD_TOKEN environment variable not set')

client.run(TOKEN)
