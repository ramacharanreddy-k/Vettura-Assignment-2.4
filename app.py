import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import re
from gtts import gTTS
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chunk_text(text, chunk_size=4000):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def extract_video_id(url):
    pattern = r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        st.error(f"Error fetching transcript: {str(e)}")
        return None

def generate_content(transcript):
    chunks = chunk_text(transcript)
    summaries = []
    
    progress_text = "Summarizing transcript chunks..."
    progress_bar = st.progress(0)
    
    for i, chunk in enumerate(chunks):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Summarize this transcript chunk."
                },
                {
                    "role": "user",
                    "content": chunk
                }
            ],
            max_tokens=500
        )
        summaries.append(response.choices[0].message.content)
        progress_bar.progress((i + 1) / len(chunks))
    
    combined_summary = " ".join(summaries)
    
    st.info("Generating final article...")
    final_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Generate a blog article with title and subtitle from this summary."
            },
            {
                "role": "user",
                "content": combined_summary
            }
        ],
        max_tokens=1000
    )
    return final_response.choices[0].message.content

def generate_image_prompt(title):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Generate a detailed image prompt for DALL-E based on the blog title."
            },
            {
                "role": "user",
                "content": f"Generate an image prompt for this title: {title}"
            }
        ]
    )
    return response.choices[0].message.content

def generate_image(prompt):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url

def generate_audio(text, output_file="article_audio.mp3"):
    tts = gTTS(text=text, lang='en')
    tts.save(output_file)
    return output_file

def main():
    st.title("AI Blog Generator")
    
    with st.form("url_form"):
        url = st.text_input("Enter YouTube URL:")
        submitted = st.form_submit_button("Generate Blog")
    
    if submitted and url:
        video_id = extract_video_id(url)
        
        if video_id:
            st.video(url)
            transcript = get_transcript(video_id)
            
            if transcript:
                st.info("Generating content... This may take a few minutes.")
                
                # Generate content
                content = generate_content(transcript)
                lines = content.split('\n')
                title = lines[0].replace('Title: ', '')
                subtitle = lines[1].replace('Subtitle: ', '')
                article = '\n'.join(lines[2:])
                
                # Generate image
                st.info("Generating image...")
                image_prompt = generate_image_prompt(title)
                image_url = generate_image(image_prompt)
                
                # Display results
                st.image(image_url, caption="Generated Featured Image")
                st.title(title)
                st.header(subtitle)
                st.markdown("---")
                st.write(article)
                
                # Generate audio
                st.info("Generating audio...")
                audio_file = generate_audio(article)
                st.audio(audio_file)
                os.remove(audio_file)
                
                st.success("Blog generation complete!")

if __name__ == "__main__":
    main()