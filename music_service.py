from youtube_search import YoutubeSearch
import json
import webbrowser
import time

class YouTubeHelper:
    def __init__(self):
        self.last_search = None
        
    def search_and_play(self, query):
        """Search for a song on YouTube, return results, and open top result"""
        try:
            results = YoutubeSearch(query, max_results=3).to_json()
            results = json.loads(results)
            
            if results and results.get('videos'):
                # Store first video URL for auto-play
                first_video = results['videos'][0]
                video_url = f"https://youtube.com{first_video.get('url_suffix')}"
                
                # Open URL in default browser
                webbrowser.open(video_url)
                
                # Construct response with all results
                response = f"Opening the top result in your browser and here are some matches I found:\n\n"
                for i, video in enumerate(results['videos'][:3], 1):
                    title = video.get('title')
                    duration = video.get('duration')
                    url = f"https://youtube.com{video.get('url_suffix')}"
                    channel = video.get('channel')
                    
                    response += f"{i}. {title}\n"
                    response += f"   Duration: {duration}\n"
                    response += f"   Channel: {channel}\n"
                    response += f"   Link: {url}\n\n"
                
                self.last_search = results
                return response
            return "Sorry, I couldn't find any matches for that song."
            
        except Exception as e:
            return f"Sorry, I encountered an error while searching: {str(e)}"
