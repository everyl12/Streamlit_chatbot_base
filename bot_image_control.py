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

# Path to save chat history
CHAT_HISTORY_PATH = "chat_history.json"

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_PATH):
        with open(CHAT_HISTORY_PATH, "r") as file:
            return json.load(file)
    return []

def save_chat_history(chat_history):
    with open(CHAT_HISTORY_PATH, "w") as file:
        json.dump(chat_history, file)

# Extract query parameters from the URL
#http://192.168.1.90:8501/?RV=1
# Use st.query_params to get query parameters from the URL
query_params = st.query_params

# Check if "RV" is in the query parameters
if "RV" in query_params:
    # Convert to an integer and set in session state
    st.session_state.random_variable = int(query_params["RV"][0])
else:
    # Generate a random binary variable (0 or 1) if not present in URL
    if "random_variable" not in st.session_state:
        st.session_state.random_variable = random.randint(0, 1)
        
def create_html_file():
    html_content = "<html><body>"
    html_content += "<h1>Chat History</h1>"

    # Iterate through chat messages and escape content for HTML
    for message in st.session_state.messages:
        role = message["role"]
        content = html.escape(message["content"])  # Escape special characters
        if role == "assistant":
            html_content += f"<p><strong>Assistant:</strong> {content}</p>"
        else:
            html_content += f"<p><strong>User:</strong> {content}</p>"

    # Check if there are any generated image URLs in the list
    if st.session_state.generated_image_urls:
        html_content += "<h2>Generated Images</h2>"
        for idx, image_url in enumerate(st.session_state.generated_image_urls):
            if image_url and image_url.startswith("http"):
                html_content += f"<p><strong>Generated Image {idx + 1} URL:</strong> <a href='{image_url}'>{image_url}</a></p>"
                html_content += f"<img src='{image_url}' alt='Generated Image {idx + 1}' width='300'>"
    
    # Add the random variable to the chat history in the downloadable file
    html_content += f"<p><strong>Random Variable:</strong> {st.session_state.random_variable}</p>"

    html_content += "</body></html>"
    return html_content

# Initialize session state variables
if "start_chat" not in st.session_state:
    st.session_state.start_chat = False
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()
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

# Sidebar controls: Start, Exit, and Download
with st.sidebar:
    if st.button("Start Chat"):
        st.session_state.start_chat = True
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    if st.button("Exit Chat"):
        st.session_state.messages = []  # Clear the chat history
        st.session_state.start_chat = False  # Reset the chat state
        st.session_state.thread_id = None
        st.session_state.conversation_started = False  # Reset conversation tracking
        st.session_state.summary_generated = False  # Reset summary tracking
        st.session_state.generated_image_urls = []

    # Add a Save Chat button
    if st.button("Save Chat"):
        # Save the latest chat history to ensure the most recent state is reflected
        save_chat_history(st.session_state.messages)
        
        # Mark that the chat has been saved, so we can show the download button
        st.session_state.chat_saved = True

        # Introduce an 10-second delay before enabling the Download Chat button
        time.sleep(10)

    # Show the Download Chat button only after the Save Chat button has been clicked and 8 seconds have passed
    if st.session_state.get("chat_saved", False):
        # Generate the latest HTML file for download
        html_file = create_html_file()

        # Single download button that triggers file download directly
        st.download_button(label="Download Chat", data=html_file, file_name="chat_history.html", mime="text/html")


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
            st.error("Failed request due to content policy. Please try again.")
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


# Function to combine the original summary with the user's feedback and regenerate the image - one chance
# def ask_for_regeneration():
#     # First ask whether the user is satisfied with the image, but only if an image exists
#     if st.session_state.generated_image_urls:
#         satisfied = st.radio("Are you satisfied with the image?", ("Yes", "No"))

#     if satisfied == "Yes":
#         # If they are satisfied, instruct them to save and download the chat
#         st.write("Awesome! Just hit 'Save Chat', wait 10 seconds, and then click 'Download Chat'. Don't forget to upload the chat histroy to Qualtrics.")
#     else:
#         # If not satisfied, ask them for modifications
#         st.write("Let me know what you'd like to modify below.")
#         user_feedback = st.text_input("Your modification:")
        
#         if user_feedback:
#             if st.button("Regenerate Image"):
#                 # Regenerate the image using the user's feedback (you'd have the logic to handle this)
#                 detailed_summary = generate_summary()
#                 new_prompt = f"{detailed_summary} Additionally, {user_feedback}."
#                 new_image_url = generate_image(new_prompt)

#                 if new_image_url and new_image_url not in st.session_state.generated_image_urls:
#                     st.session_state.generated_image_urls.append(new_image_url)
#                     # Automatically save the chat history after generating an image
#                     #save_chat_history(st.session_state.messages)
                
#                 st.image(new_image_url, caption="Re-generated Image")

#                 # Set the flag to prevent the form from showing again
#                 st.session_state.image_regenerated = True

#                 # Provide instructions to save the chat after regeneration
#                 st.write("To save the chat and images, hit 'Save Chat', wait 10 seconds, and then go ahead and click 'Download Chat'. Please upload the chat histroy to Qualtrics.")

#######################################################Conversation starts########################################################
if st.session_state.start_chat:
    st.title("ThoughtFlowAI")
    
    # Vary the message based on the random binary variable
    if st.session_state.random_variable == 0:
        st.write("Hi! I am ThoughtFlowAI, here to assist you in image generation."
                 " I am an AI model fine-tuned to **optimize efficiency over diversity**."
                 " I’ll ask you a simple question to understand what you have in mind.")
    else:
        st.write("Hi! I am ThoughtFlowAI, here to assist you in image generation."
                 " I am an AI model fine-tuned to **optimize diversity over efficiency**."
                 " I’ll ask you a simple question to understand what you have in mind.")

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
            instructions="Play the role of an AI image generation assistant in the context of preventive healthcare. "
            "The first remark from you should be welcoming them and ask whether they are ready. "
            "The second remark is to ask them to describe their image. Don't ask any follow-up questions. "
            "Following user input, provide a summary of user input by using the following phrase 'Here is a summary of your prompts'."
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
        
        save_chat_history(st.session_state.messages)  # Save chat history after each interaction

    # Display the summary and check if "a summary of your prompts" is in the messages
    if st.session_state.conversation_started:
        for message in st.session_state.messages:
            if "a summary of your prompts" in message["content"] or "a summary of your prompt" in message["content"]:
                st.session_state.conversation_summary = message["content"]  # Assign summary content
                st.session_state.summary_generated = True

    # Display the "Generate Image" button only after the summary
    if st.session_state.summary_generated and st.session_state.conversation_summary is not None:
        if st.button("Generate Image"):
            st.write("Generating your image, please wait...")

            detailed_summary = generate_summary()
            new_image_url = generate_image(detailed_summary)
            
            # Append new image URL if it's valid and not already in the list
            if new_image_url and new_image_url not in st.session_state.generated_image_urls:
                st.session_state.generated_image_urls.append(new_image_url)
            
            st.session_state.summary_generated = False  # Reset summary for next step

        # Display the first image with the caption "Generated Image"
        if st.session_state.generated_image_urls:
            st.image(st.session_state.generated_image_urls[0], caption="Generated Image")

        # If there are more images (re-generated ones), display them as "Re-generated Image"
        # if len(st.session_state.generated_image_urls) > 1:
        #     for idx, image_url in enumerate(st.session_state.generated_image_urls[1:], start=1):
        #         st.image(image_url, caption=f"Re-generated Image {idx}")

            # Provide instructions to save the chat after regeneration
            st.write("Now click 'Save Chat', wait 10 seconds, and then go ahead and click 'Download Chat'. Please upload the file to Qualtrics.")
        
else:
    st.write("Click 'Start Chat' to begin.")




