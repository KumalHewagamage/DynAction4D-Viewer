import streamlit as st
import streamlit.components.v1 as components
import os
import json

from data_processing import (
    get_datasets,
    get_sequences,
    process_sequence_data,
    extract_video_frames,
)
from html_renderer import generate_player_html

# --- Configuration ---
st.set_page_config(page_title="CL4D-DynAction4D", layout="wide")
st.markdown(
    """
    <style>
    /* Hide Streamlit default fluff */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Clean up the main container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Style headers */
    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        color: #1a202c;
    }
    </style>
""",
    unsafe_allow_html=True,
)
ROOT_DATA_DIR = "data"

# --- Main App UI ---
st.title("🏃‍♂️ CL4D-DynAction4D")

datasets = get_datasets(ROOT_DATA_DIR)
if not datasets:
    st.error(f"No dataset directories found in '{ROOT_DATA_DIR}/'.")
    st.stop()

# Layout styling for the controls
col_data, col_seq, col_fps = st.columns([2, 2, 1])

with col_data:
    selected_dataset = st.selectbox("Select Dataset", datasets)

current_dataset_dir = os.path.join(ROOT_DATA_DIR, selected_dataset)
sequences = get_sequences(current_dataset_dir)

if not sequences:
    st.warning(f"No sequences found in {current_dataset_dir}/pcd/")
    st.stop()

with col_seq:
    selected_seq = st.selectbox("Select Sequence", sequences)
with col_fps:
    target_fps = st.number_input(
        "PCD Playback FPS", min_value=1, max_value=60, value=15
    )


seq_pcd_dir = os.path.join(current_dataset_dir, "pcd", selected_seq)
video_path = os.path.join(current_dataset_dir, "video", f"{selected_seq}.mp4")
json_path = os.path.join(current_dataset_dir, "pcd", selected_seq, "report.json")

# Extract Description
description = "No description available."
if os.path.exists(json_path):
    try:
        with open(json_path, "r") as f:
            report_data = json.load(f)
            full_desc = report_data.get("description", "")
            description = full_desc.split(".")[0].strip() + "."
    except Exception:
        pass

# Process Data
with st.spinner("Extracting frames and processing point clouds..."):
    pcd_frames_data, range_x, range_y, range_z = process_sequence_data(seq_pcd_dir)
    vid_frames_data = extract_video_frames(video_path)

# Render Custom Component
html_content = generate_player_html(
    pcd_frames_data, vid_frames_data, target_fps, range_x, range_y, range_z, description
)


components.html(html_content, height=800)
