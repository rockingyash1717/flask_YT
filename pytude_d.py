import re
import requests
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# --- 1. Define Custom Exceptions ---
class VideoIdError(Exception):
    """Raised when the Video ID cannot be extracted from the URL."""
    pass

class VideoTitleError(Exception):
    """Raised when the Video Title cannot be retrieved via API."""
    pass

class VideoTranscriptError(Exception):
    """Raised when the Transcript cannot be retrieved."""
    pass

# --- 2. Refactored Class ---
class video_info:
    def __init__(self, video_url: str):
        self.video_url = video_url
        
     
        self.video_id = self.extract_video_id()
        
        self.title = self.get_video_title()
        

        self.transcript = self.get_transcript()

        self.current_thumbnail=self.get_current_thumbnail()

    def extract_video_id(self) -> str:
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.video_url)
            if match:
                return match.group(1)
        
        # FAILED: Raise Exception 1
        raise VideoIdError("Could not extract a valid YouTube ID from the URL.")



    def get_video_title(self) -> str:
        try:
            ydl_opts = {
                'quiet': True,           # Suppress console output
                'skip_download': True,   # We only want metadata
                'no_warnings': True,
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                # download=False ensures we just fetch JSON info
                info_dict = ydl.extract_info(self.video_url, download=False)
                
                title = info_dict.get('title', None)
                if not title:
                    raise Exception("Title field missing in metadata")
                
                return title

        except Exception as e:
            # Passes the error to your custom exception handler
            raise VideoTitleError(f"Failed to retrieve title via yt-dlp: {str(e)}")
        
    

    def get_current_thumbnail(self) -> str:
        resolutions = [
            'maxresdefault',  # 1080p
            'sddefault',      # 640p
            'hqdefault',      # 480p
            'mqdefault',      # 320p
            'default'         # 120p
        ] 
        for resolution in resolutions:
            url = f'https://img.youtube.com/vi/{self.video_id}/{resolution}.jpg'
            response = requests.get(url)
            if response.status_code == 200:
                return url
        return None
    

    def get_transcript(self) -> str:
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(self.video_id)    

            # 1. Try Manual English
            try:
                manual_en = transcript_list.find_manually_created_transcript(['en'])
                data = manual_en.fetch()
                return " ".join(entry.text for entry in data)
            except NoTranscriptFound:
                pass

            # 2. Try Auto-generated English
            try:
                auto_en = transcript_list.find_generated_transcript(['en'])
                data = auto_en.fetch()
                return " ".join(entry.text for entry in data)
            except NoTranscriptFound:
                pass

            # 3. Try Translating any available transcript to English
            for transcript in transcript_list:
                if transcript.is_translatable:
                    try:
                        translated = transcript.translate('en')
                        data = translated.fetch()
                        return " ".join(entry.text for entry in data)
                    except Exception:
                        continue
            
            # If we reach here, we found transcripts object but couldn't get English text
            raise VideoTranscriptError("No English transcript (manual, auto, or translated) could be generated.")

        except (VideoTranscriptError):
            # Re-raise our custom error if we triggered it above
            raise
        except Exception as e:
            # Catch all library errors (TranscriptsDisabled, VideoUnavailable, etc.)
            # FAILED: Raise Exception 3
            raise VideoTranscriptError(f"Transcript unavailable: {str(e)}")