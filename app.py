import streamlit as st
import requests
import tempfile
import os
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_audioclips
import speech_recognition as sr
import pyttsx3
import numpy as np
from moviepy.audio.AudioClip import AudioArrayClip

API_KEY = "22ec84421ec24230a3638d1b51e3a7dc"
ENDPOINT_URL = "https://internshala.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-08-01-preview"

st.title("AI-Powered Video Audio Correction")

uploaded_file = st.file_uploader("Upload a Video", type=["mp4", "mov", "avi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
        tmp_video.write(uploaded_file.read())
        video_path = tmp_video.name

    st.video(video_path)

    video = VideoFileClip(video_path)
    audio_path = "extracted_audio.wav"
    video.audio.write_audiofile(audio_path)

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            transcript = recognizer.recognize_google(audio_data)
    except sr.RequestError as e:
        st.error(f"Error with speech recognition service: {e}")
    except sr.UnknownValueError:
        st.error("Could not understand the audio")
    else:
        st.write("Original Transcript:")
        st.text(transcript)

        headers = {"Content-Type": "application/json", "api-key": API_KEY}
        payload = {
            "messages": [
                {"role": "system", "content": "Correct grammatical mistakes in the transcript."},
                {"role": "user", "content": transcript}
            ],
            "temperature": 0.5,
            "max_tokens": 1000,
        }

        response = requests.post(ENDPOINT_URL, json=payload, headers=headers)
        
        if response.status_code == 401:
            st.error("Unauthorized: Check your API key or permissions.")
        elif response.status_code != 200:
            st.error(f"Error: {response.text}")
        else:
            corrected_transcript = response.json()["choices"][0]["message"]["content"]
            st.write("Corrected Transcript:")
            st.text(corrected_transcript)

            # Using pyttsx3 for offline text-to-speech
            engine = pyttsx3.init()
            corrected_audio_path = "corrected_audio.wav"
            engine.save_to_file(corrected_transcript, corrected_audio_path)
            engine.runAndWait()

            # Check if corrected audio file exists
            if os.path.exists(corrected_audio_path):
                corrected_audio = AudioFileClip(corrected_audio_path)

                # Ensure the corrected audio matches the length of the original video
                if corrected_audio.duration < video.duration:
                    silence_duration = video.duration - corrected_audio.duration
                    silence = AudioArrayClip(np.zeros((int(silence_duration * corrected_audio.fps), 2)), fps=corrected_audio.fps)
                    corrected_audio = concatenate_audioclips([corrected_audio, silence])

                # Now corrected_audio should be ready to use
                final_video_path = "final_video_with_corrected_audio.mp4"
                final_video = video.set_audio(corrected_audio)
                final_video.write_videofile(final_video_path, codec="libx264")

                st.success("Video processed successfully!")
                st.video(final_video_path)
            else:
                st.error("Corrected audio file not found.")

    # Cleanup only after successful processing
    if os.path.exists(audio_path):
        os.remove(audio_path)
    if os.path.exists(corrected_audio_path):
        os.remove(corrected_audio_path)
    if os.path.exists(video_path):
        os.remove(video_path)
