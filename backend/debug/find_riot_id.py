"""
Helper script to find your Riot ID
Usage: python find_riot_id.py
"""

print("=" * 60)
print("How to Find Your Riot ID")
print("=" * 60)
print()
print("1. Open League of Legends client")
print("2. Look at the top-left corner of the client")
print("3. Your Riot ID is shown as: GameName#TAG")
print()
print("Examples:")
print("  - Faker#KR1")
print("  - Doublelift#NA1")
print("  - gunoo#1234")
print()
print("=" * 60)
print()

game_name = input("Enter your Game Name (before the #): ").strip()
tag_line = input("Enter your Tag (after the #): ").strip()

print()
print(f"Your Riot ID is: {game_name}#{tag_line}")
print()
print("Now add these to your .env file:")
print(f'RIOT_GAME_NAME={game_name}')
print(f'RIOT_TAG_LINE={tag_line}')
print()
