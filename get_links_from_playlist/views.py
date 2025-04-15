import os
import json
import subprocess
import tempfile
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from pathlib import Path


def extract_playlist_videos_ytdlp(playlist_url):
    """
    Extract videos from a YouTube playlist using yt-dlp

    Args:
        playlist_url (str): YouTube playlist URL

    Returns:
        list: List of video dictionaries with title and url
        or dict: Error message if something fails
    """
    try:
        # Create a temporary file to store the URLs
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_path = temp_file.name

        # Extract URLs using yt-dlp
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "-i",
            "--print-to-file",
            "url,title",
            temp_path,
            playlist_url,
        ]
        process = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if process.returncode != 0:
            return {"error": f"yt-dlp error: {process.stderr}"}

        # Read the temporary file
        videos = []
        with open(temp_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Process in pairs (url, title)
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                url = lines[i].strip()
                title = lines[i + 1].strip()

                # Extract video ID from URL
                video_id = (
                    url.split("v=")[-1].split("&")[0]
                    if "v=" in url
                    else url.split("/")[-1]
                )

                videos.append({"title": title, "id": video_id, "url": url})

        # Clean up the temporary file
        os.unlink(temp_path)

        return videos

    except Exception as e:
        return {"error": f"Error extracting playlist: {str(e)}"}


def save_to_text_file(videos, filename):
    """
    Save video links to a text file

    Args:
        videos (list): List of video dictionaries
        filename (str): File path to save the links

    Returns:
        str: Path to the saved file
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        for video in videos:
            f.write(f"{video['title']} - {video['url']}\n")

    return filename


@csrf_exempt
def get_playlist_links_to_file(request):
    """
    API endpoint that takes a YouTube playlist link and saves video links to a text file

    Request (POST JSON):
        {
            "playlist_url": "https://www.youtube.com/playlist?list=PLAYLIST_ID"
        }

    Response:
        {
            "success": true/false,
            "file_path": "/path/to/saved/file.txt",
            "video_count": 42,
            "error": "Error message if any"
        }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        playlist_url = data.get("playlist_url")

        if not playlist_url:
            return JsonResponse({"error": "Missing playlist_url parameter"}, status=400)

        # Extract playlist ID for filename
        if "list=" in playlist_url:
            playlist_id = playlist_url.split("list=")[1].split("&")[0]
        else:
            playlist_id = "playlist"

        # Get videos from the playlist
        videos = extract_playlist_videos_ytdlp(playlist_url)

        if isinstance(videos, dict) and "error" in videos:
            return JsonResponse(videos, status=400)

        # Create output directory in the project root
        output_dir = Path(settings.BASE_DIR) / "playlist_files"
        os.makedirs(output_dir, exist_ok=True)

        # Save to file
        output_file = output_dir / f"playlist_{playlist_id}.txt"
        file_path = save_to_text_file(videos, output_file)

        return JsonResponse(
            {"success": True, "file_path": str(file_path), "video_count": len(videos)}
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def get_playlist_links_as_json(request):
    """
    API endpoint that takes a YouTube playlist link and returns video links as JSON

    Request (POST JSON):
        {
            "playlist_url": "https://www.youtube.com/playlist?list=PLAYLIST_ID"
        }

    Response:
        {
            "success": true/false,
            "videos": [
                {"title": "Video Title", "id": "videoId", "url": "https://youtube.com/watch?v=videoId"},
                ...
            ],
            "video_count": 42,
            "error": "Error message if any"
        }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        playlist_url = data.get("playlist_url")

        if not playlist_url:
            return JsonResponse({"error": "Missing playlist_url parameter"}, status=400)

        # Get videos from the playlist
        videos = extract_playlist_videos_ytdlp(playlist_url)

        if isinstance(videos, dict) and "error" in videos:
            return JsonResponse(videos, status=400)

        return JsonResponse(
            {"success": True, "videos": videos, "video_count": len(videos)}
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
