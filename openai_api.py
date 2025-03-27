import json
import logging
from typing import Dict, Any, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIAPI:
    """API client for OpenAI to generate wiki entries."""
    
    def __init__(self, api_key: str):
        """Initialize the OpenAI API client.
        
        Args:
            api_key: The API key for OpenAI
        """
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = "gpt-4o"
        
    def generate_wiki_entry(self, game_data: Dict[str, Any]) -> Tuple[str, str]:
        """Generate a wiki entry for a game.
        
        Args:
            game_data: Information about the game
            
        Returns:
            A tuple containing (wiki_entry, references)
        """
        try:
            # Prepare a detailed prompt with all available game information
            prompt = self._prepare_wiki_prompt(game_data)
            
            logger.info(f"Generating wiki entry for {game_data.get('name', 'unknown game')}")
            
            # Make the request to OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a video game historian and journalist who writes professional wiki "
                                  "entries about video games. Your entries are well-structured, factual, "
                                  "comprehensive and engaging for readers. Focus on the game's development, "
                                  "gameplay, reception, and cultural impact. Use a neutral, encyclopedic tone. "
                                  "Feel free to integrate relevant visual elements such as 'As shown in the game's artwork, ...' "
                                  "or 'The visual style of the game depicts...' when the game has images available."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=2000
            )
            
            # Extract the response
            result = json.loads(response.choices[0].message.content)
            
            wiki_entry = result.get("wiki_entry", "")
            references = result.get("references", "")
            
            return wiki_entry, references
            
        except Exception as e:
            logger.error(f"Error generating wiki entry: {e}")
            return (
                "Error generating wiki entry. Please try again later.",
                "No references available due to error."
            )
            
    def _prepare_wiki_prompt(self, game_data: Dict[str, Any]) -> str:
        """Prepare a detailed prompt for the wiki entry generation.
        
        Args:
            game_data: Information about the game
            
        Returns:
            A formatted prompt string
        """
        game_name = game_data.get('name', 'Unknown Game')
        description = game_data.get('description', 'No description available.')
        release_date = game_data.get('released', 'Unknown release date')
        developers = ', '.join(game_data.get('developers', ['Unknown developer']))
        publishers = ', '.join(game_data.get('publishers', ['Unknown publisher']))
        genres = ', '.join(game_data.get('genres', ['Unknown genre']))
        platforms = ', '.join(game_data.get('platforms', ['Unknown platform']))
        tags = ', '.join(game_data.get('tags', []))
        rating = game_data.get('rating', 'No rating available')
        website = game_data.get('website', 'No official website available')
        image_url = game_data.get('image_url', 'No image available')
        
        prompt = f"""
Please create a professional wiki entry for the video game "{game_name}".

Here is the information available about the game:
- Description: {description}
- Release Date: {release_date}
- Developers: {developers}
- Publishers: {publishers}
- Genres: {genres}
- Platforms: {platforms}
- Tags: {tags}
- Rating: {rating}
- Official Website: {website}
- Image URL: {image_url}

Write a comprehensive wiki entry that is 3-5 paragraphs long. Cover the game's development, gameplay mechanics, story/setting (if applicable), reception, and cultural impact.

Also include a list of references that would be appropriate for this wiki entry. These can include gaming websites, reviews, interviews, and other reliable sources.

Format your response as a JSON object with two fields:
1. "wiki_entry": The full 3-5 paragraph wiki entry text
2. "references": A formatted list of references in APA style

Note: If the description is in HTML format, please parse it and use the actual content rather than the HTML tags.
The image URL will be displayed alongside your wiki entry, so you don't need to describe the image in detail. Focus on the game itself.
"""
        return prompt
