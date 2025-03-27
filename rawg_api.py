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
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make a request to the RAWG API.
        
        Args:
            endpoint: The API endpoint to request
            params: Optional query parameters
            
        Returns:
            The JSON response or None if there was an error
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
            if response.status_code == 429:  # Too Many Requests
                logger.warning("Rate limit exceeded, waiting before retrying")
                time.sleep(60)  # Wait a minute before retrying
                return self._make_request(endpoint, params)
            else:
                logger.error(f"HTTP error occurred: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error occurred: {e}")
        except ValueError as e:
            logger.error(f"JSON parsing error: {e}")
            
        return None
    
    def get_indie_games(self, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """Get a list of indie games.
        
        Args:
            page: The page number to request
            page_size: The number of results per page
            
        Returns:
            A list of games or an empty list if there was an error
        """
        params = {
            'page': page,
            'page_size': page_size,
            'genres': 'indie',
            'ordering': '-added'  # Sort by most recently added
        }
        
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
            
        return game_data
    
    def search_games(self, query: str, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """Search for games by name.
        
        Args:
            query: The search query
            page: The page number to request
            page_size: The number of results per page
            
        Returns:
            A list of games matching the search query
        """
        params = {
            'search': query,
            'page': page,
            'page_size': page_size
        }
        
        response = self._make_request('games', params)
        
        if response and 'results' in response:
            return response['results']
        
        return []
