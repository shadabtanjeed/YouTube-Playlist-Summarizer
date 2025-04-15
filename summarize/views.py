import os
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


def summarize_youtube_video(video_id):
    """
    Get a transcript and summary of a YouTube video using RapidAPI

    Args:
        video_id (str): YouTube video ID

    Returns:
        dict: Transcript and summary data or error message
    """
    try:
        # Use the YouTube Video Summarizer GPT AI API
        url = "https://youtube-video-summarizer-gpt-ai.p.rapidapi.com/api/v1/get-transcript-v2"

        # Get API key from settings or environment
        api_key = os.environ.get("RAPID_API_KEY")

        if not api_key:
            return {
                "error": "RapidAPI key not configured. Please check your .env file or environment variables."
            }

        # Debug - print partial API key to verify it's loaded (only for development)
        print(f"Using API key starting with: {api_key[:5]}...")

        # Set up headers and parameters
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "youtube-video-summarizer-gpt-ai.p.rapidapi.com",
        }

        querystring = {"video_id": video_id, "platform": "youtube"}

        # Make the API request
        response = requests.get(url, headers=headers, params=querystring)

        # Debug information
        print(f"Response status: {response.status_code}")

        if response.status_code == 403:
            return {
                "error": "API access forbidden. Verify your RapidAPI key is valid and has access to this API."
            }
        elif response.status_code == 401:
            return {
                "error": "Unauthorized access. Your API key may be incorrect or expired."
            }
        elif response.status_code == 429:
            return {
                "error": "Too many requests. You may have exceeded your RapidAPI quota."
            }

        response.raise_for_status()

        # Return the JSON response
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"API request error: {str(e)}"}
    except Exception as e:
        return {"error": f"Error summarizing video: {str(e)}"}


@csrf_exempt
def get_video_summary(request):
    """
    API endpoint that takes a YouTube video ID and returns its transcript and summary

    Request (POST JSON):
        {
            "video_id": "VIDEO_ID",
            "save_to_file": true/false (optional, default: false)
        }

    Response:
        {
            "success": true/false,
            "transcript": {...transcript data...},
            "file_path": "/path/to/saved/file.txt" (if save_to_file is true),
            "error": "Error message if any"
        }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        video_id = data.get("video_id")
        save_to_file = data.get("save_to_file", False)

        if not video_id:
            return JsonResponse({"error": "Missing video_id parameter"}, status=400)

        # Get the summary
        response_data = summarize_youtube_video(video_id)

        if isinstance(response_data, dict) and "error" in response_data:
            return JsonResponse(response_data, status=400)

        result = {"success": True, "transcript": response_data}

        # Save to file if requested
        if save_to_file:
            output_dir = settings.BASE_DIR / "summary_files"
            output_dir.mkdir(exist_ok=True)

            output_file = output_dir / f"summary_{video_id}.txt"

            # Format the transcript and summary for the file
            with open(output_file, "w", encoding="utf-8") as f:
                if isinstance(response_data, dict):
                    # Write video title if available
                    if "title" in response_data:
                        f.write(f"Title: {response_data['title']}\n\n")

                    # Write transcript chunks if available
                    if "transcript" in response_data and isinstance(
                        response_data["transcript"], list
                    ):
                        f.write("Transcript:\n\n")
                        for chunk in response_data["transcript"]:
                            if isinstance(chunk, dict) and "text" in chunk:
                                f.write(
                                    f"[{chunk.get('start', '0:00')}] {chunk['text']}\n"
                                )

                    # Write summary if available
                    if "summary" in response_data:
                        f.write("\n\nSummary:\n\n")
                        f.write(response_data["summary"])
                else:
                    f.write(str(response_data))

            result["file_path"] = str(output_file)

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def test_api_connection(request):
    """
    Test endpoint to verify API key and connection
    """
    try:
        # Get API key
        api_key = os.environ.get("RAPID_API_KEY")

        if not api_key:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "API key not found in settings or environment variables",
                },
                status=400,
            )

        # Test with a simple request
        test_video_id = "dQw4w9WgXcQ"  # A popular video

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "youtube-video-summarizer-gpt-ai.p.rapidapi.com",
        }

        url = "https://youtube-video-summarizer-gpt-ai.p.rapidapi.com/api/v1/get-transcript-v2"
        querystring = {"video_id": test_video_id, "platform": "youtube"}

        response = requests.get(url, headers=headers, params=querystring)

        if response.status_code == 200:
            return JsonResponse(
                {
                    "status": "success",
                    "message": "API connection successful",
                    "response_code": response.status_code,
                    "response_preview": (
                        str(response.text)[:100] + "..."
                        if len(response.text) > 100
                        else response.text
                    ),
                }
            )
        else:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "API connection failed",
                    "response_code": response.status_code,
                    "response_text": response.text,
                },
                status=400,
            )

    except Exception as e:
        return JsonResponse(
            {"status": "error", "message": f"Error testing API connection: {str(e)}"},
            status=500,
        )
