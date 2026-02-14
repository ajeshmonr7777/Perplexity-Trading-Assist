import os
import glob
import re
from yt_dlp import YoutubeDL

class YouTubeService:
    def __init__(self):
        pass

    def get_transcript(self, url: str) -> str:
        """
        Extract transcript/subtitles from a YouTube video using yt-dlp.
        Returns plain text of the subtitles.
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            return "Error: Invalid YouTube URL"
            
        # Configure yt-dlp options
        # We want subtitles (manual or auto), English preferred, no video download
        base_path = f"/tmp/{video_id}"
        
        # Clean up existing files first
        self._cleanup(base_path)
        
        ydl_opts = {
            'skip_download': True,      # Don't download video
            'writesubtitles': True,     # Write subtitle file
            'writeautomaticsub': True,  # Write auto-generated subs if no manual
            'subtitleslangs': ['en'],   # English only
            'outtmpl': base_path,       # Output template
            'quiet': True,
            'no_warnings': True
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # Check for subtitle files
                # yt-dlp saves as base_path.en.vtt or base_path.en.ttml etc
                
                # Find the downloaded subtitle file
                extensions = ['.vtt', '.ttml', '.srt']
                subtitle_file = None
                
                # Check for manual subs first (e.g. .en.vtt)
                for ext in extensions:
                    path = f"{base_path}.en{ext}"
                    if os.path.exists(path):
                        subtitle_file = path
                        break
                
                # Check for auto subs (might be named slightly differently depending on version)
                if not subtitle_file:
                    # Search pattern match
                    files = glob.glob(f"{base_path}*")
                    for f in files:
                        if any(f.endswith(ext) for ext in extensions):
                            subtitle_file = f
                            break
                
                if not subtitle_file:
                    return "No English subtitles found for this video."
                
                # Parse the subtitle file
                transcript_text = self._parse_subtitle_file(subtitle_file)
                
                # Cleanup
                self._cleanup(base_path)
                
                title = info.get('title', 'YouTube Video')
                return f"Video Title: {title}\n\nTranscript:\n{transcript_text}"

        except Exception as e:
            self._cleanup(base_path)
            return f"Error extracting transcript: {str(e)}"

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from URL"""
        # Supports youtu.be/ID and youtube.com/watch?v=ID
        if "youtu.be" in url:
            return url.split("/")[-1].split("?")[0]
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        return None

    def _parse_subtitle_file(self, filepath: str) -> str:
        """Parse VTT/SRT file to plain text"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple VTT/SRT parsing (remove timestamps and metadata)
            lines = content.splitlines()
            text_lines = []
            
            # Regex to match timestamps (00:00:00.000 --> 00:00:05.000)
            timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}')
            
            seen_lines = set()
            
            for line in lines:
                line = line.strip()
                if not line: continue
                if "WEBVTT" in line: continue
                if "Kind:" in line or "Language:" in line: continue
                if timestamp_pattern.search(line): continue
                if line.isdigit(): continue # Sequnce numbers
                
                # Remove HTML tags like <c> or <font>
                line = re.sub(r'<[^>]+>', '', line)
                
                # Deduplicate consecutive identical lines (common in VTT)
                if line not in seen_lines:
                    text_lines.append(line)
                    seen_lines.add(line)
                    # Reset seen for non-consecutive duplicates? 
                    # Actually standard transcripts just flow.
                    # Simplest is just append.
            
            # Join and clean up
            full_text = ' '.join(text_lines)
            # Remove extra spaces
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            return full_text
            
        except Exception as e:
            return f"[Error parsing subtitle file: {str(e)}]"

    def _cleanup(self, base_path: str):
        """Remove temporary files"""
        try:
            files = glob.glob(f"{base_path}*")
            for f in files:
                os.remove(f)
        except:
            pass

# Singleton instance
youtube_service = YouTubeService()
