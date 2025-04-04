import time
import requests
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class RawgAPI:
    """API client for RAWG.io video game database."""
    
    def __init__(self, api_key: str):
        """Initialize the RAWG API client.
        
        Args:
            api_key: The API key for RAWG.io
        """
        self.api_key = api_key
        self.base_url = "https://api.rawg.io/api"
        self.session = requests.Session()
        self.rate_limit_remaining = 1000  # Default high value, will be updated with API responses
        self.rate_limit_reset = 0
        
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Handle rate limiting by checking response headers.
        
        Args:
            response: The response from the API
        """
        # Check for rate limit headers if they exist
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset = response.headers.get('X-RateLimit-Reset')
        
        if remaining is not None:
            self.rate_limit_remaining = int(remaining)
        
        if reset is not None:
            self.rate_limit_reset = int(reset)
            
        # If we're approaching the rate limit, sleep to avoid hitting it
        if self.rate_limit_remaining < 5:
            sleep_time = max(self.rate_limit_reset - time.time(), 0) + 1
            logger.warning(f"Rate limit approaching, sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the RAWG API.
        
        Args:
            endpoint: The API endpoint to request
            params: Optional query parameters
            
        Returns:
            The JSON response as dict or empty dict if there was an error
        """
        if params is None:
            params = {}
            
        # Add API key to all requests
        params['key'] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.debug(f"Making request to {url} with params {params}")
            response = self.session.get(url, params=params)
            
            # Handle rate limiting
            self._handle_rate_limit(response)
            
            # Check if the request was successful
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            response_obj = locals().get('response')
            if response_obj and response_obj.status_code == 429:  # Too Many Requests
                logger.warning("Rate limit exceeded, waiting before retrying")
                time.sleep(60)  # Wait a minute before retrying
                return self._make_request(endpoint, params)
            else:
                logger.error(f"HTTP error occurred: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error occurred: {e}")
        except ValueError as e:
            logger.error(f"JSON parsing error: {e}")
            
        return {}
    
    def get_indie_games(self, page: int = 1, page_size: int = 20, metacritic_min: Optional[int] = None, min_reviews: Optional[int] = 1) -> List[Dict[str, Any]]:
        """Get a list of indie games.
        
        Args:
            page: The page number to request
            page_size: The number of results per page
            metacritic_min: Optional minimum metacritic score for filtering
            min_reviews: Optional minimum number of ratings/reviews
            
        Returns:
            A list of games or an empty list if there was an error
        """
        params = {
            'page': page,
            'page_size': page_size,
            'genres': 'indie',
            'ordering': '-added'  # Sort by most recently added
        }
        
        # Add metacritic filter if specified
        if metacritic_min:
            params['metacritic'] = f"{metacritic_min},100"  # Range from min to 100
            
        # Add ratings count filter to get games with at least some reviews
        if min_reviews:
            params['ratings_count'] = f"{min_reviews},1000000"
        
        response = self._make_request('games', params)
        
        if response and 'results' in response:
            return response['results']
        
        return []
    
    def get_game_details(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific game.
        
        Args:
            game_id: The ID of the game
            
        Returns:
            The game details or None if there was an error
        """
        # First, get the basic game details
        game_data = self._make_request(f'games/{game_id}')
        
        if not game_data:
            return None
        
        # Then get developers and publishers
        developers = self._make_request(f'games/{game_id}/development-team')
        if developers and 'results' in developers:
            game_data['developers'] = developers['results']
        else:
            game_data['developers'] = []
            
        # Sleep briefly to prevent hitting rate limits
        time.sleep(0.5)
        
        # Get game screenshots
        screenshots = self._make_request(f'games/{game_id}/screenshots')
        if screenshots and 'results' in screenshots:
            game_data['screenshots'] = screenshots['results']
        else:
            game_data['screenshots'] = []
        
        # Get store information
        stores = self._make_request(f'games/{game_id}/stores')
        if stores and 'results' in stores:
            game_data['stores'] = stores['results']
        else:
            # Check if store data is already in the basic details
            if 'stores' not in game_data:
                game_data['stores'] = []
                
        # Process store links for easy access
        if 'stores' in game_data:
            # Create a dictionary of store links by store name
            game_data['store_links'] = {}
            for store_data in game_data['stores']:
                if isinstance(store_data, dict) and 'store' in store_data:
                    # Get the store information (name, slug)
                    store = store_data.get('store', {})
                    store_name = store.get('name', '')
                    
                    # Get the URL if available
                    store_url = store_data.get('url', '')
                    
                    # Only add if we have a store name
                    if store_name:
                        game_data['store_links'][store_name] = store_url
                
        # Process Steam store link specifically
        if 'store_links' in game_data and 'Steam' in game_data['store_links']:
            game_data['steam_url'] = game_data['store_links']['Steam']
        else:
            game_data['steam_url'] = ''
            
        return game_data
    
    def search_games(self, query: str, page: int = 1, page_size: int = 20, min_reviews: Optional[int] = 1) -> List[Dict[str, Any]]:
        """Search for games by name.
        
        Args:
            query: The search query
            page: The page number to request
            page_size: The number of results per page
            min_reviews: Optional minimum number of ratings/reviews
            
        Returns:
            A list of games matching the search query
        """
        params = {
            'search': query,
            'page': page,
            'page_size': page_size
        }
        
        # Add ratings count filter to get games with at least some reviews
        if min_reviews:
            params['ratings_count'] = f"{min_reviews},1000000"
        
        response = self._make_request('games', params)
        
        if response and 'results' in response:
            return response['results']
        
        return []
