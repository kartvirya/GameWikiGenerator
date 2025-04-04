import os
import json
from rawg_api import RawgAPI

# Get API key from environment
api_key = os.environ.get("RAWG_API_KEY", "")
if not api_key:
    print("RAWG_API_KEY environment variable not set")
    exit(1)

# Initialize the API client
api = RawgAPI(api_key)

# Test getting indie games with ratings_count
print("Testing get_indie_games with ratings_count parameter...")
games = api.get_indie_games(page=1, page_size=5, min_reviews=1)

print(f"Returned {len(games)} games")
for i, game in enumerate(games):
    ratings_count = game.get('ratings_count', 'N/A')
    rating = game.get('rating', 'N/A')
    name = game.get('name', 'Unknown')
    print(f"Game {i+1}: {name} - Rating: {rating} - Ratings Count: {ratings_count}")

# Test one specific game that should have ratings
print("\nTesting get_game_details for a popular game (Minecraft)...")
game_details = api.get_game_details(22509)  # Minecraft's ID
if game_details:
    print(f"Game: {game_details.get('name', 'Unknown')}")
    print(f"Rating: {game_details.get('rating', 'N/A')}")
    print(f"Ratings Count: {game_details.get('ratings_count', 'N/A')}")
    print(f"Available fields: {list(game_details.keys())}")
else:
    print("Failed to get game details") 