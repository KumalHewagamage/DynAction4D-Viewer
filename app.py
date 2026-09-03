import streamlit as st
import streamlit.components.v1 as components
import json
import os
import glob
import cv2
import base64

# --- Configuration ---
st.set_page_config(page_title="DynAction4D Viewer", layout="wide")
DATA_DIR = "data/Sample_DynAction4D"

# --- Helper Functions ---
def load_pcd(filepath):
    x, y, z, colors, labels = [], [], [], [], []
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    data_idx = next(i for i, line in enumerate(lines) if line.startswith("DATA")) + 1
            
    for line in lines[data_idx:]:
        parts = line.strip().split()
        if len(parts) >= 8:
            x.append(float(parts[0]))
            y.append(float(parts[1]))
            z.append(float(parts[2]))
            
            rgb_int = int(parts[6])
            r, g, b = (rgb_int >> 16) & 255, (rgb_int >> 8) & 255, rgb_int & 255
            colors.append(f'rgb({r}, {g}, {b})')
            labels.append(parts[7])
            
    return {"x": x, "y": y, "z": z, "colors": colors, "labels": labels}

@st.cache_data
def process_sequence_data(seq_pcd_dir):
    frames_list = []
    frames = sorted(glob.glob(os.path.join(seq_pcd_dir, "frame_*.pcd")))
    
    min_x, max_x, min_y, max_y, min_z, max_z = float('inf'), float('-inf'), float('inf'), float('-inf'), float('inf'), float('-inf')
    
    for f in frames:
        data = load_pcd(f)
        frames_list.append(data)
        if data['x']:
            min_x, max_x = min(min_x, min(data['x'])), max(max_x, max(data['x']))
            min_y, max_y = min(min_y, min(data['y'])), max(max_y, max(data['y']))
            min_z, max_z = min(min_z, min(data['z'])), max(max_z, max(data['z']))
            
    max_span = max(max_x - min_x, max_y - min_y, max_z - min_z)
    cx, cy, cz = (max_x + min_x)/2, (max_y + min_y)/2, (max_z + min_z)/2
    pad = max_span * 0.55
    
    return frames_list, [cx-pad, cx+pad], [cy-pad, cy+pad], [cz-pad, cz+pad]

@st.cache_data
def extract_video_frames(video_path, max_width=600):
    """Extracts video frames as base64 JPEGs, resized to prevent browser memory issues."""
    frames = []
    if not os.path.exists(video_path):
        return frames
        
    cap = cv2.VideoCapture(video_path)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        if w > max_width:
            frame = cv2.resize(frame, (max_width, int(h * (max_width / w))))
            
        # Encode as JPEG for lower payload size
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        b64 = base64.b64encode(buffer).decode('utf-8')
        frames.append(f"data:image/jpeg;base64,{b64}")
        
    cap.release()
    return frames

# --- Main App UI ---
st.title("🏃‍♂️ Dynamic 3D Action Viewer")

sequences = sorted([d for d in os.listdir(os.path.join(DATA_DIR, "pcd")) if d.startswith("sequence_")])
if not sequences:
    st.error("No sequences found.")
    st.stop()

col_seq, col_fps = st.columns([3, 1])
with col_seq:
    selected_seq = st.selectbox("Select Sequence", sequences)
with col_fps:
    target_fps = st.number_input("PCD Playback FPS", min_value=1, max_value=60, value=20)

seq_pcd_dir = os.path.join(DATA_DIR, "pcd", selected_seq)
video_path = os.path.join(DATA_DIR, "video", f"{selected_seq}.mp4")

with st.spinner("Extracting frames and processing point clouds..."):
    pcd_frames_data, range_x, range_y, range_z = process_sequence_data(seq_pcd_dir)
    vid_frames_data = extract_video_frames(video_path)

# --- Custom JS/HTML Sync Engine ---
html_template = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <style>
        body { margin: 0; font-family: sans-serif; color: #fff; }
        .controls { display: flex; align-items: center; gap: 15px; margin-bottom: 15px; background: #1e1e1e; padding: 10px; border-radius: 8px;}
        button { padding: 8px 16px; cursor: pointer; border: none; border-radius: 4px; background: #ff4b4b; color: white; font-weight: bold; }
        input[type=range] { flex-grow: 1; }
        .container { display: flex; width: 100%; height: 550px; gap: 15px; }
        .panel { flex: 1; display: flex; flex-direction: column; background: #0e1117; border-radius: 8px; overflow: hidden;}
        img { width: 100%; object-fit: contain; background: #000; height: 100%; }
        h3 { margin: 10px 15px; font-weight: 500; font-size: 1.1rem; }
    </style>
</head>
<body>
    <div class="controls">
        <button id="play-btn">Play</button>
        <input type="range" id="timeline" min="0" step="1" value="0">
        <span id="frame-counter">0 / 0</span>
    </div>

    <div class="container">
        <div class="panel">
            <h3>Video Reference</h3>
            <img id="vid-img" src="" alt="Video Frame">
        </div>
        <div class="panel">
            <h3>Interactive Point Cloud</h3>
            <div id="pcd-div" style="width: 100%; height: 100%;"></div>
        </div>
    </div>
    
    <script>
        const pcdFrames = __PCD_FRAMES__;
        const vidFrames = __VID_FRAMES__;
        const fps = __FPS__;
        
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        
        const playBtn = document.getElementById('play-btn');
        const timeline = document.getElementById('timeline');
        const counter = document.getElementById('frame-counter');
        const vidImg = document.getElementById('vid-img');
        
        timeline.max = pcdFrames.length - 1;

        const layout = {
            scene: {
                aspectmode: 'cube',
                xaxis: {title: 'X', range: __RANGE_X__},
                yaxis: {title: 'Depth (Z)', range: __RANGE_Z__},
                zaxis: {title: 'Height (Y)', range: __RANGE_Y__}
            },
            margin: {l: 0, r: 0, b: 0, t: 0},
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: {color: 'white'}
        };
        
        const getTrace = (idx) => ({
            type: 'scatter3d',
            mode: 'markers',
            x: pcdFrames[idx].x,
            y: pcdFrames[idx].z,
            z: pcdFrames[idx].y,
            text: pcdFrames[idx].labels,
            hoverinfo: 'text',
            marker: { size: 2.5, color: pcdFrames[idx].colors, opacity: 0.9 }
        });

        function renderFrame() {
            // 1. Update 3D Plot
            Plotly.react('pcd-div', [getTrace(currentFrame)], layout);
            
            // 2. Update Image (Aligned by duration ratio)
            if (vidFrames.length > 0) {
                let vidIdx = Math.floor((currentFrame / pcdFrames.length) * vidFrames.length);
                if (vidIdx >= vidFrames.length) vidIdx = vidFrames.length - 1;
                vidImg.src = vidFrames[vidIdx];
            }
            
            // 3. Update UI
            timeline.value = currentFrame;
            counter.innerText = `${currentFrame + 1} / ${pcdFrames.length}`;
        }

        function step() {
            currentFrame = (currentFrame + 1) % pcdFrames.length;
            renderFrame();
        }

        playBtn.addEventListener('click', () => {
            isPlaying = !isPlaying;
            if (isPlaying) {
                playBtn.innerText = "Pause";
                playInterval = setInterval(step, 1000 / fps);
            } else {
                playBtn.innerText = "Play";
                clearInterval(playInterval);
            }
        });

        timeline.addEventListener('input', (e) => {
            currentFrame = parseInt(e.target.value);
            renderFrame();
        });

        // Initialize first frame
        Plotly.newPlot('pcd-div', [getTrace(0)], layout).then(() => {
            renderFrame();
        });
    </script>
</body>
</html>
"""

html_content = html_template.replace("__PCD_FRAMES__", json.dumps(pcd_frames_data))
html_content = html_content.replace("__VID_FRAMES__", json.dumps(vid_frames_data))
html_content = html_content.replace("__FPS__", str(target_fps))
html_content = html_content.replace("__RANGE_X__", json.dumps(range_x))
html_content = html_content.replace("__RANGE_Y__", json.dumps(range_y))
html_content = html_content.replace("__RANGE_Z__", json.dumps(range_z))

components.html(html_content, height=750)