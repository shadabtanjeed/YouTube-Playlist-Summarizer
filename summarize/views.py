import os
import json
import requests
import subprocess
import tempfile
import time
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from pathlib import Path
import sys
import re

# Import Google's Generative AI library
import google.generativeai as genai


def extract_video_id_from_url(url):
    """
    Extract the video ID from a YouTube URL

    Args:
        url (str): YouTube URL

    Returns:
        str: YouTube video ID or None if not found
    """
    youtube_regex = (
        r'(youtu\.be\/|youtube\.com\/(watch\?(.*&)?v=|(embed|v)\/))([^?&"\'>]+)'
    )
    match = re.search(youtube_regex, url)

    if match:
        return match.group(5)

    # If the input is already just an ID
    if re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url

    return None


def ensure_youtube_url(video_input):
    """
    Ensure the input is a valid YouTube URL

    Args:
        video_input (str): Either a YouTube URL or a video ID

    Returns:
        str: A properly formatted YouTube URL
    """
    if "youtube.com" in video_input or "youtu.be" in video_input:
        return video_input
    else:
        # Assume it's just the video ID
        return f"https://youtu.be/{video_input}"


def summarize_youtube_video_with_gemini(video_input, style="detailed", retries=3):
    """
    Get a transcript and summary of a YouTube video using Google's Gemini model with
    direct API integration and prompt engineering

    Args:
        video_input (str): YouTube video URL or ID
        style (str): Summary style (detailed, short, academic, descriptive)
        retries (int): Number of retry attempts

    Returns:
        dict: Transcript and summary data or error message
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            return {
                "error": "Gemini API key not configured. Please set GEMINI_API_KEY in your .env file."
            }

        # Configure the Gemini API
        genai.configure(api_key=api_key)

        # Initialize the model - starting with most capable model, can fall back to others
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
        except Exception as e:
            print(f"Error initializing model: {str(e)}, trying fallback model")
            model = genai.GenerativeModel("gemini-1.0-pro")

        # Ensure we have a proper YouTube URL
        video_url = ensure_youtube_url(video_input)
        video_id = extract_video_id_from_url(video_url)

        # Create style-specific prompt enhancement
        style_prompt = ""
        if style == "short":
            style_prompt = "Provide a concise summary in 3-5 bullet points with only the most important information."
        elif style == "academic":
            style_prompt = "Provide an academic analysis of the content with formal language, critical evaluation of arguments, and references to key concepts."
        elif style == "descriptive":
            style_prompt = "Provide a detailed descriptive summary, focusing on the visuals, setting, and presentation style along with the content."
        elif style == "technical":
            style_prompt = "Focus on technical details, specifications, methodologies, and processes mentioned in the video."
        else:  # detailed is default
            style_prompt = "Provide a comprehensive summary that captures all key points, arguments, examples, and conclusions."

        # Create the prompt with clear instructions
        prompt = f"""
        You're analyzing a YouTube video: {video_url}
        
        First, provide a complete transcript of the video in a section titled "TRANSCRIPT".
        
        Then, in a section titled "SUMMARY", summarize the video content.
        {style_prompt}
        
        Format your response exactly like this:
        
        TRANSCRIPT:
        [Full transcript text here]
        
        SUMMARY:
        [Your summary here]
        """

        for attempt in range(retries):
            try:
                print(f"Attempt {attempt+1}/{retries} for video {video_url}")

                # Make the API request with the video URL
                response = model.generate_content(prompt)

                # Extract the text response
                if hasattr(response, "text"):
                    generated_text = response.text
                else:
                    generated_text = str(response)

                # Parse the generated text to separate transcript and summary
                transcript = ""
                summary = ""

                if (
                    "TRANSCRIPT" in generated_text.upper()
                    and "SUMMARY" in generated_text.upper()
                ):
                    parts = generated_text.split("SUMMARY", 1)
                    transcript = parts[0].replace("TRANSCRIPT", "", 1).strip()
                    summary = parts[1].strip()
                else:
                    # If the format is different, just use the whole text as a summary
                    summary = generated_text

                return {
                    "title": f"Video URL: {video_url}",
                    "video_id": video_id,
                    "transcript": transcript,
                    "summary": summary,
                    "raw_response": generated_text,
                    "style": style,
                }

            except Exception as e:
                print(f"Error on attempt {attempt+1}: {str(e)}")
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 3
                    print(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                else:
                    return {"error": f"Failed after {retries} attempts: {str(e)}"}

        return {"error": "Failed to generate summary after multiple attempts"}

    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": f"Error summarizing video: {str(e)}"}


def summarize_youtube_video_with_simple_prompt(video_input, style="detailed"):
    """
    Simplified version using just the video URL in prompt

    Args:
        video_input (str): YouTube video URL or ID
        style (str): Summary style

    Returns:
        dict: Summary data or error message
    """
    try:
        # Get API key from environment
        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            return {
                "error": "Gemini API key not configured. Please set GEMINI_API_KEY in your .env file."
            }

        # Configure the Gemini API
        genai.configure(api_key=api_key)

        # Initialize the model
        model = genai.GenerativeModel("gemini-1.5-pro")

        # Ensure we have a proper YouTube URL
        video_url = ensure_youtube_url(video_input)
        video_id = extract_video_id_from_url(video_url)

        # Style-specific prompt
        style_instruction = ""
        if style == "short":
            style_instruction = "Make it concise with 3-5 bullet points."
        elif style == "academic":
            style_instruction = "Use academic language and critical analysis."
        elif style == "descriptive":
            style_instruction = "Be descriptive about visuals and presentation style."
        elif style == "technical":
            style_instruction = "Focus on technical details and methodologies."

        # Simple, direct prompt
        prompt = f"Summarize the video: {video_url}. {style_instruction}"

        # Make the request
        response = model.generate_content(prompt)

        # Extract and return the response
        summary = response.text if hasattr(response, "text") else str(response)

        return {
            "title": f"Video URL: {video_url}",
            "video_id": video_id,
            "summary": summary,
            "style": style,
        }

    except Exception as e:
        return {"error": f"Error with simple prompt: {str(e)}"}


@csrf_exempt
def get_video_summary(request):
    """
    API endpoint that takes a YouTube video URL or ID and returns its transcript and summary

    Request (POST JSON):
        {
            "video_id": "VIDEO_ID"  OR  "video_url": "VIDEO_URL",
            "style": "detailed|short|academic|descriptive|technical" (optional, default: "detailed"),
            "save_to_file": true/false (optional, default: false)
        }

    Response:
        {
            "success": true/false,
            "transcript": "video transcript",
            "summary": "video summary",
            "file_path": "/path/to/saved/file.txt" (if save_to_file is true),
            "error": "Error message if any"
        }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        video_input = data.get("video_url") or data.get("video_id")
        style = data.get("style", "detailed")
        save_to_file = data.get("save_to_file", False)

        if not video_input:
            return JsonResponse(
                {"error": "Missing video_url or video_id parameter"}, status=400
            )

        # Get the summary with the selected style
        response_data = summarize_youtube_video_with_gemini(video_input, style)

        # If first method fails, try a simpler approach
        if isinstance(response_data, dict) and "error" in response_data:
            print(
                f"Detailed method failed: {response_data['error']}. Trying simple approach..."
            )
            response_data = summarize_youtube_video_with_simple_prompt(
                video_input, style
            )

        if isinstance(response_data, dict) and "error" in response_data:
            return JsonResponse(response_data, status=400)

        result = {
            "success": True,
            "transcript": response_data.get("transcript", ""),
            "summary": response_data.get("summary", ""),
            "style": response_data.get("style", style),
        }

        # Save to file if requested
        if save_to_file:
            output_dir = Path(settings.BASE_DIR) / "summary_files"
            output_dir.mkdir(exist_ok=True)

            # Extract video ID for filename
            video_id = response_data.get(
                "video_id", extract_video_id_from_url(video_input)
            )
            if not video_id:
                video_id = "unknown"

            output_file = output_dir / f"summary_{video_id}_{style}.txt"

            # Format the transcript and summary for the file
            with open(output_file, "w", encoding="utf-8") as f:
                if "title" in response_data:
                    f.write(f"Title: {response_data['title']}\n\n")

                if "style" in response_data:
                    f.write(f"Style: {response_data['style']}\n\n")

                if "transcript" in response_data and response_data["transcript"]:
                    f.write("Transcript:\n\n")
                    f.write(response_data["transcript"])
                    f.write("\n\n")

                if "summary" in response_data and response_data["summary"]:
                    f.write("Summary:\n\n")
                    f.write(response_data["summary"])

            result["file_path"] = str(output_file)

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def test_api_connection(request):
    """
    Test endpoint to verify API key and connection
    """
    try:
        # Get API key
        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "API key not found in environment variables",
                },
                status=400,
            )

        # Test with the Google Generative AI library directly
        genai.configure(api_key=api_key)

        # Try to initialize the model
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Error initializing Gemini model: {str(e)}",
                },
                status=400,
            )

        # Simple test prompt
        test_prompt = "Hello! This is a test to verify the API connection."

        try:
            response = model.generate_content(test_prompt)
            response_text = (
                response.text if hasattr(response, "text") else str(response)
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Gemini API connection successful",
                    "response_preview": (
                        response_text[:100] + "..."
                        if len(response_text) > 100
                        else response_text
                    ),
                    "model": "gemini-1.5-pro",
                }
            )
        except Exception as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Error generating content: {str(e)}",
                },
                status=400,
            )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return JsonResponse(
            {"status": "error", "message": f"Error testing API connection: {str(e)}"},
            status=500,
        )


@csrf_exempt
def summarize_playlist(request):
    """
    API endpoint that takes a YouTube playlist URL and summarizes all videos in the playlist

    Request (POST JSON):
        {
            "playlist_url": "https://www.youtube.com/playlist?list=PLAYLIST_ID",
            "style": "detailed|short|academic|descriptive|technical" (optional, default: "detailed"),
            "save_to_file": true/false (optional, default: true)
        }

    Response:
        {
            "success": true/false,
            "playlist_info": {
                "url": "playlist_url",
                "id": "playlist_id",
                "video_count": 10
            },
            "summaries": [
                {
                    "video_id": "VIDEO_ID1",
                    "title": "Video title",
                    "success": true/false,
                    "file_path": "/path/to/summary_VIDEO_ID1.txt" (if save_to_file is true)
                },
                ...
            ],
            "error": "Error message if any"
        }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        playlist_url = data.get("playlist_url")
        style = data.get("style", "detailed")
        save_to_file = data.get("save_to_file", True)

        if not playlist_url:
            return JsonResponse({"error": "Missing playlist_url parameter"}, status=400)

        # First, extract the videos from the playlist using the functionality from get_links_from_playlist
        from get_links_from_playlist.views import extract_playlist_videos_ytdlp

        videos = extract_playlist_videos_ytdlp(playlist_url)

        if isinstance(videos, dict) and "error" in videos:
            return JsonResponse(videos, status=400)

        # Extract playlist ID for identification purposes
        if "list=" in playlist_url:
            playlist_id = playlist_url.split("list=")[1].split("&")[0]
        else:
            playlist_id = "playlist"

        # Create output directory for summaries
        output_dir = Path(settings.BASE_DIR) / "summary_files"
        output_dir.mkdir(exist_ok=True)

        # Create a specific directory for this playlist's summaries
        playlist_dir = output_dir / f"playlist_{playlist_id}"
        playlist_dir.mkdir(exist_ok=True)

        # Also create a combined file for all summaries
        combined_file_path = playlist_dir / f"all_summaries_{style}.txt"

        # Process each video in the playlist
        summaries = []

        # Open the combined file
        with open(combined_file_path, "w", encoding="utf-8") as combined_file:
            combined_file.write(f"Summaries for playlist: {playlist_url}\n")
            combined_file.write(f"Summary style: {style}\n")
            combined_file.write(f"Total videos: {len(videos)}\n\n")
            combined_file.write("=" * 80 + "\n\n")

            # Process each video
            for i, video in enumerate(videos, 1):
                video_id = video.get("id")
                video_url = video.get("url")
                video_title = video.get("title")

                print(f"Processing video {i}/{len(videos)}: {video_title}")
                print(f"URL: {video_url}")

                # Get the summary with better error handling
                try:
                    # Try with detailed prompt first - use full URL instead of ID
                    summary_data = summarize_youtube_video_with_gemini(video_url, style)

                    # If that fails, try with simple prompt
                    if isinstance(summary_data, dict) and "error" in summary_data:
                        print(
                            f"Detailed prompt failed: {summary_data['error']}. Trying simple prompt..."
                        )
                        summary_data = summarize_youtube_video_with_simple_prompt(
                            video_url, style
                        )
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    summary_data = {"error": f"Exception in summarization: {str(e)}"}

                summary_result = {
                    "video_id": video_id,
                    "video_url": video_url,
                    "title": video_title,
                    "success": not (
                        isinstance(summary_data, dict) and "error" in summary_data
                    ),
                }

                if summary_result["success"]:
                    # If save_to_file is true, save the individual summary
                    if save_to_file:
                        # Individual file path
                        file_path = playlist_dir / f"summary_{video_id}_{style}.txt"

                        # Format the transcript and summary for the file
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(f"Title: {video_title}\n")
                            f.write(f"URL: {video_url}\n\n")
                            f.write(f"Style: {style}\n\n")

                            if isinstance(summary_data, dict):
                                # Write transcript if available
                                if (
                                    "transcript" in summary_data
                                    and summary_data["transcript"]
                                ):
                                    f.write("Transcript:\n\n")
                                    f.write(summary_data["transcript"])
                                    f.write("\n\n")

                                # Write summary if available
                                if (
                                    "summary" in summary_data
                                    and summary_data["summary"]
                                ):
                                    f.write("Summary:\n\n")
                                    f.write(summary_data["summary"])
                            else:
                                f.write(str(summary_data))

                        summary_result["file_path"] = str(file_path)

                    # Add to the combined file
                    combined_file.write(f"Video {i}: {video_title}\n")
                    combined_file.write(f"ID: {video_id}\n")
                    combined_file.write(f"URL: {video_url}\n\n")

                    if isinstance(summary_data, dict) and "summary" in summary_data:
                        combined_file.write("Summary:\n")
                        combined_file.write(summary_data["summary"])
                    else:
                        combined_file.write("No summary available")

                    combined_file.write("\n\n" + "=" * 80 + "\n\n")
                else:
                    # If there was an error, add it to the result
                    summary_result["error"] = summary_data.get("error", "Unknown error")

                    # Add error info to the combined file
                    combined_file.write(f"Video {i}: {video_title}\n")
                    combined_file.write(f"ID: {video_id}\n")
                    combined_file.write(f"URL: {video_url}\n\n")
                    combined_file.write(f"Error: {summary_result['error']}\n\n")
                    combined_file.write("=" * 80 + "\n\n")

                # Add to our results
                summaries.append(summary_result)

        # Return the results
        return JsonResponse(
            {
                "success": True,
                "playlist_info": {
                    "url": playlist_url,
                    "id": playlist_id,
                    "video_count": len(videos),
                    "style": style,
                },
                "summaries": summaries,
                "combined_file": str(combined_file_path),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        # Print exception details for debugging
        import traceback

        traceback.print_exc()
        return JsonResponse(
            {"error": f"Error processing playlist: {str(e)}"}, status=500
        )
