import openai
import streamlit as st
import time
import json
import os
import html
import random

st.set_page_config(page_title="ThoughtFlowAI", page_icon=":speech_balloon:")

assistant_id = "asst_Ck3R41NmsbSM0kDxUYuEVDFf"

client = openai

# Initialize session state variables
if "start_chat" not in st.session_state:
    st.session_state.start_chat = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_summary" not in st.session_state:
    st.session_state.conversation_summary = None
if "generated_image_urls" not in st.session_state:
    st.session_state.generated_image_urls = []  # List to store all generated image URLs
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False  # To track if a conversation has started
if "summary_generated" not in st.session_state:
    st.session_state.summary_generated = False  # Track if summary has been generated
if "image_regenerated" not in st.session_state:
        st.session_state.image_regenerated = False

# Sidebar controls: Start, Clear & Restart
with st.sidebar:
    if st.button("Start Chat"):
        st.session_state.start_chat = True
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

# Function to generate a detailed, safe conversation summary for DALL-E (used at the backend only)
def generate_summary():
    summary_run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_id,
        instructions=(
            # "Please summarize the conversation in an appropriate, detailed prompt for generating an image that promotes preventive healthcare services (e.g., routine check-ups, vaccinations, or sexual health screenings)."
            # "Ensure to include context and details for each aspect the user provided. For example, instead of just 'adult,' describe it as 'an Asian adult patient smiling during a healthcare check-up with a doctor.' "
            # "Make sure the summary is coherent and suitable for generating a healthcare-related image while adhering to safety guidelines."
            "Please summarize the conversation in a detailed, appropriate, and descriptive prompt for generating an image that encourages LGBTQ+ communities"
            "to utilize preventive healthcare services (e.g., routine check-ups, vaccinations, or sexual health screenings). "
            "Ensure to include context and details for each aspect the user provided, such as the patient's gender identity, sexual orientation, "
            "age group, racial or ethnic background, health condition, and how the patient and doctor are interacting. "
            "For example, instead of just 'Asian,' describe it as 'an Asian adult patient smiling during a healthcare check-up with a doctor.' "
            "Make sure the summary is in a complete, coherent form ready to be used for generating a healthcare-related image."
        )
    )

    # Wait for the summary to complete
    while summary_run.status != 'completed':
        time.sleep(1)
        summary_run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id,
            run_id=summary_run.id
        )
    
    # Fetch the conversation summary
    summary_messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id
    )
    summary_message = next(
        message for message in summary_messages 
        if message.run_id == summary_run.id and message.role == "assistant"
    )
    return summary_message.content[0].text.value


# Function to generate the image and store the URL
def generate_image(prompt):
    try:
        response = openai.images.generate(
            model="dall-e-3",
            prompt=prompt + " Please generate healthcare-related, high-resolution realistic photographs with real humans and details.",
            n=1,  # Number of images to generate
            size="1024x1024",  # Image size
            quality="standard"
        )
        image_url = response.data[0].url
        
        # Check if the URL is valid
        if image_url and image_url.startswith("http"):
            st.session_state.generated_image_urls.append(image_url)  # Append the valid URL
            return image_url
        else:
            st.error("Invalid image URL received from API.")
            return None

    except openai.BadRequestError as e:
        # Handle bad requests (e.g., content policy violations)
        if 'content_policy_violation' in str(e):
            st.error("Failed request due to content policy. Please wait 10 seconds and then click 'Generate Image' to try again.")
        else:
            st.error(f"Bad request error: {e}")
        return None

    except openai.OpenAIError as e:
        # Handle all other OpenAI-related errors
        st.error(f"An error occurred with OpenAI API: {e}")
        return None

    except Exception as e:
        # Handle any other unexpected errors
        st.error(f"Unexpected error: {str(e)}")
        return None

#######################################################Conversation starts########################################################
if st.session_state.start_chat:
    st.title("ThoughtFlowAI")
    
    st.write("Hi! I am ThoughtFlowAI, here to assist you in image generation.")

    if "openai_model" not in st.session_state:
        st.session_state.openai_model = "gpt-4o-mini"
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Let's generate an image."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )
        
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
            instructions="Play the role of an AI image generation assistant in the context of preventive healthcare. The tone should be helpful and personal. Be concise. "
            "The first remark from you should be welcoming them. Gently remind them they just have one chance. Ask gently whether they are ready to proceed. "
            "The second remark should invite the user to describe their image in a unpressed way. Don't ask any follow-up questions. "
            "After receiving the user's input, thank them and summarize their prompt."
            "Ask whether they are satisfied with their prompts, if not, please revise. Then provide a new summary of the user’s prompts using the following phrase: 'Thanks! Here's an summary of your prompts'."
            "And we'll get started once they click 'Generate Image'."
        )

        # Waiting for the assistant's run to complete
        while run.status != 'completed':
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
        
        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread_id
        )

        # Process and display assistant messages
        assistant_messages_for_run = [
            message for message in messages 
            if message.run_id == run.id and message.role == "assistant"
        ]
        for message in assistant_messages_for_run:
            st.session_state.messages.append({"role": "assistant", "content": message.content[0].text.value})
            with st.chat_message("assistant"):
                st.markdown(message.content[0].text.value)

        # Track that the conversation has started
        st.session_state.conversation_started = True
        
    # Display the summary and check if "a summary of your prompts" is in the messages
    if st.session_state.conversation_started:
        for message in st.session_state.messages:
            if "a summary of your prompts" in message["content"] or "a summary of your prompt" in message["content"]:
                st.session_state.conversation_summary = message["content"]  # Assign summary content
                st.session_state.summary_generated = True

    # Display the "Generate Image" button only after the summary
    if st.session_state.summary_generated and st.session_state.conversation_summary is not None:
        if st.button("Generate Image"):
            st.write("Generating your image, please wait 10-20s...")

            detailed_summary = generate_summary()
            new_image_url = generate_image(detailed_summary)
            
            # Append new image URL if it's valid and not already in the list
            if new_image_url and new_image_url not in st.session_state.generated_image_urls:
                st.session_state.generated_image_urls.append(new_image_url)
            
            st.session_state.summary_generated = False  # Reset summary for next step

        # Display the first image with the caption "Generated Image"
        if st.session_state.generated_image_urls:
            st.image(st.session_state.generated_image_urls[0], caption="Generated Image")

            # Provide instructions to save the chat after regeneration
            st.write("Thank you! Now please save the image and upload the file to Qualtrics.")
        
else:
    st.write("Welcome! Please click 'Start Chat' to begin.")






