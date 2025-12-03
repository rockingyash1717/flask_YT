import os
import google.generativeai as genai
from dotenv import load_dotenv

# Assuming these are your local modules
# REMOVED: from new_summary import generate_newsummary (Using local function instead)
from generate_image import generate_image
from pytude_d import video_info, VideoIdError, VideoTitleError, VideoTranscriptError

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set. Please add it to your .env file.")

# Configure the Gemini API
genai.configure(api_key=api_key)

def summarize_text(text):
    """
    Uses Gemini to summarize text.
    Optimized for 'gemini-1.5-flash' for speed and large context (1M tokens).
    """
    try:
        # Use 'gemini-1.5-flash' for high speed and large context window (free tier friendly)
        # If you specifically want 2.5 and have the new SDK, change this string.
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        prompt = f"""
        Provide a very short summary, no more than three sentences, for the following video transcript.
        Focus on the main topic and key takeaways.
        
        Transcript:
        {text}
        
        Summary:
        """
        
        # Stream=False is standard for short outputs
        response = model.generate_content(prompt)
        
        if response.text:
            cleaned_text = ' '.join(response.text.split())
            return cleaned_text
            
        return "No summary generated."
        
    except Exception as e:
        print(f"Error in summarize_text: {e}")
        # Fallback return to prevent code from crashing later
        return "Summary unavailable due to error."

def process_video_from_url(video_url):
    """
    Fetches video info using pytude_d and generates a summary using local summarize_text.
    """
    try:
        # Initialize the video_info class with the URL
        info = video_info(video_url)
        
        # Access the attributes directly
        title = info.title
        transcript = info.transcript
        
        if not transcript:
            print(f"No transcript available for {title}.")
            return None

        print(f"Transcript found ({len(transcript)} characters). Generating summary...")

        # LIMIT CHECK: 1.5-Flash can handle ~700,000 words. 
        # We pass the whole transcript now, removing the previous 10k limit.
        summary = summarize_text(transcript)
        
        return {
            "summary": summary, 
            "title": title,
            "video_id": info.video_id,
            "thumbnail_url": info.current_thumbnail
        }

    except VideoIdError:
        print(f"Error: Invalid Video ID extracted from {video_url}")
        return None
    except VideoTitleError:
        print(f"Error: Could not retrieve title for {video_url}")
        return None
    except VideoTranscriptError:
        print(f"Error: Could not retrieve transcript for {video_url}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred processing video: {e}")
        return None

def Generate_promt(summary, include_human, include_text):
    """
    Constructs the prompt for the image generator.
    """
    # 1. Analyze the summary to get context using the SAME local summary function
    # (Reusing summarize_text logic but with a different prompt)
    
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        analysis_prompt = f"""
        Please extract the following information from this video summary to help design a YouTube thumbnail:
        Video Summary: {summary}
        
        Task:
        1. Video Topic: What is the main subject?
        2. Target Audience: Who is watching?
        3. Visual Vibe: Describe the color scheme and aesthetic.
        """
        
        response = model.generate_content(analysis_prompt)
        analysis_output = response.text if response.text else "General topic analysis."

        # 2. Set constraints
        human_constraint = "Include a photorealistic human or human face expressing emotion relevant to the topic." if include_human else "Do NOT include any human faces, people, or humanoid figures."
        text_constraint = "Include the video title or catchy keywords in big bold letters." if include_text else "Do NOT include any text, letters, or words in the image. Focus purely on the visual art."

        # 3. Create the final style prompt
        final_prompt_request = f"""
        Create a detailed image generation prompt for a YouTube thumbnail based on this analysis:
        {analysis_output}

        Constraints:
        - {human_constraint}
        - {text_constraint}
        - High quality, 4k, trending on artstation.

        Output ONLY the prompt string.
        """
        
        final_response = model.generate_content(final_prompt_request)
        final_prompt = final_response.text if final_response.text else "A high quality youtube thumbnail."
        
        return ' '.join(final_prompt.split())

    except Exception as e:
        print(f"Error generating prompt: {e}")
        return "A high quality abstract youtube thumbnail."

def generate_thumbnail_flow(summary, include_human, include_text):
    """
    Orchestrates the prompt generation and image creation.
    """
    image_prompt = Generate_promt(summary, include_human, include_text)
    print(f"\nGenerated Image Prompt: {image_prompt}\n")
    
    # Call your external image generation function
    return generate_image(image_prompt)

if __name__ == '__main__':
    # Test Video URL
    video_url = "https://youtu.be/IMslBEcYXhk?si=ZCfbJnddDIx3AglV"

    print(f"--- Processing {video_url} ---")
    
    # 1. Get Video Data & Summary
    video_data = process_video_from_url(video_url)

    if video_data:
        print(f"Title: {video_data['title']}")
        print(f"Video ID: {video_data['video_id']}")
        print(f"Original Thumb: {video_data['thumbnail_url']}")
        print(f"Summary: {video_data['summary']}")
        
        # 2. Generate a new AI Thumbnail
        print("\n--- Generating AI Thumbnail ---")
        try:
            # Adjust these booleans as needed
            generated_image_url = generate_thumbnail_flow(
                video_data['summary'], 
                include_human=False, 
                include_text=False
            )
            print(f"Generated Image URL: {generated_image_url}")
        except Exception as e:
            print(f"Image generation failed: {e}")
    else:
        print("Failed to process video.")