import json
import logging
from typing import Dict, Any, Tuple
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIAPI:
    """API client for OpenAI to generate wiki entries."""
    
    def __init__(self, api_key: str, model="gpt-3.5-turbo"):
        """Initialize the OpenAI API client.
        
        Args:
            api_key: The API key for OpenAI
            model: The model to use (default: gpt-3.5-turbo)
        """
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.rapid_mode = False
        
    def set_rapid_mode(self, enabled=True):
        """Enable or disable rapid processing mode.
        
        Args:
            enabled: Whether to enable rapid mode
        """
        self.rapid_mode = enabled
        logger.info(f"Rapid processing mode {'enabled' if enabled else 'disabled'}")
        
    def generate_wiki_entry(self, game_data: Dict[str, Any]) -> Tuple[str, str]:
        """Generate a wiki entry for a game.
        
        Args:
            game_data: Information about the game
            
        Returns:
            A tuple containing (wiki_entry, references)
        """
        try:
            # In ultra-rapid mode, generate minimal content
            if self.rapid_mode and self.model == "gpt-3.5-turbo-instruct":
                # Prepare minimalist prompt
                game_name = game_data.get('name', 'Unknown Game')
                description = game_data.get('description', '')[:300]  # Truncate for faster processing
                release_date = game_data.get('released', '')
                developers = ', '.join(game_data.get('developers', []))[:100]
                
                # Use the completion API for fastest possible response
                completion = self.client.completions.create(
                    model="gpt-3.5-turbo-instruct",
                    prompt=f"Write a 2-paragraph wiki entry for the game '{game_name}' (released {release_date} by {developers}). Include 3 references.",
                    max_tokens=500,
                    temperature=0.3,
                )
                
                text = completion.choices[0].text
                
                # Very basic split between wiki entry and references
                parts = text.split("References:")
                wiki_entry = parts[0].strip()
                references = f"<ol><li>{'</li><li>'.join(parts[1].strip().split('\\n')[:3] if len(parts) > 1 else ['Reference 1', 'Reference 2', 'Reference 3'])}</li></ol>"
                
                return wiki_entry, references
            
            # Regular processing for other models or when not in rapid mode
            # Prepare a detailed prompt with all available game information
            prompt = self._prepare_wiki_prompt(game_data)
            
            logger.info(f"Generating wiki entry for {game_data.get('name', 'unknown game')}")
            
            # Adjust parameters based on mode
            temperature = 0.5 if self.rapid_mode else 0.7
            max_tokens = 1000 if self.rapid_mode else 2000
            
            # Make the request to OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a video game historian and journalist who writes professional wiki "
                                  "entries about video games. Your entries are well-structured, factual, "
                                  "comprehensive and engaging for readers. Focus on the game's development, "
                                  "gameplay, reception, and cultural impact. Use a neutral, encyclopedic tone."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens
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
        
        # Use a more concise prompt in rapid mode
        if self.rapid_mode:
            prompt = f"""
Create a brief wiki entry for the game "{game_name}".

Game info:
- Description: {description}
- Release: {release_date}
- Dev: {developers}
- Publisher: {publishers}
- Genres: {genres}
- Platforms: {platforms}

Write 2-3 paragraphs covering gameplay, development, and reception.
Include 3 references in HTML format.

Format as JSON with:
1. "wiki_entry": HTML-formatted wiki entry
2. "references": HTML-formatted references list with <ol> and <li> tags
"""
        else:
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

Also include a list of references that would be appropriate for this wiki entry. These can include gaming websites, reviews, interviews, and other reliable sources. Each reference should be properly formatted in APA style.

Format your response as a JSON object with two fields:
1. "wiki_entry": The full 3-5 paragraph wiki entry text with HTML formatting
2. "references": A formatted HTML list of references. Each reference should be in an <ol> list with <li> items. If a reference has a URL, make it a clickable link using an <a> tag with target="_blank". Style the references with color: #9370DB and add margin-bottom: 0.5rem to each <li>.

Example reference format:
<ol class="ps-4">
  <li class="mb-2">
    <a href="https://example.com" target="_blank" style="color: #9370DB;">Author. (Year). Article Title.</a>
  </li>
  <li class="mb-2" style="color: #9370DB;">
    Author. (Year). Book Title [No URL available].
  </li>
</ol>

Note: If the description is in HTML format, please parse it and use the actual content rather than the HTML tags.
The image URL will be displayed alongside your wiki entry, so you don't need to describe the image in detail. Focus on the game itself.
"""
        return prompt
