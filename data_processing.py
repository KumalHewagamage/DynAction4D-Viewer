import os
import glob
import cv2
import base64
import streamlit as st


def get_datasets(root_dir):
    if not os.path.exists(root_dir):
        return []
    return sorted(
        [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))]
    )


def get_sequences(dataset_dir):
    pcd_dir = os.path.join(dataset_dir, "pcd")
    if not os.path.exists(pcd_dir):
        return []
    return sorted([d for d in os.listdir(pcd_dir) if d.startswith("sequence_")])


def load_pcd(filepath):
    x, y, z, colors, labels = [], [], [], [], []
    with open(filepath, "r") as f:
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
            colors.append(f"rgb({r}, {g}, {b})")
            labels.append(parts[7])

    return {"x": x, "y": y, "z": z, "colors": colors, "labels": labels}


@st.cache_data
def process_sequence_data(seq_pcd_dir):
    frames_list = []
    frames = sorted(glob.glob(os.path.join(seq_pcd_dir, "frame_*.pcd")))

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")

    for f in frames:
        data = load_pcd(f)
        frames_list.append(data)
        if data["x"]:
            min_x, max_x = min(min_x, min(data["x"])), max(max_x, max(data["x"]))
            min_y, max_y = min(min_y, min(data["y"])), max(max_y, max(data["y"]))
            min_z, max_z = min(min_z, min(data["z"])), max(max_z, max(data["z"]))

    max_span = max(max_x - min_x, max_y - min_y, max_z - min_z)
    cx, cy, cz = (max_x + min_x) / 2, (max_y + min_y) / 2, (max_z + min_z) / 2
    pad = max_span * 0.55

    return frames_list, [cx - pad, cx + pad], [cy - pad, cy + pad], [cz - pad, cz + pad]


@st.cache_data
def extract_video_frames(video_path, max_width=600):
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

        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        b64 = base64.b64encode(buffer).decode("utf-8")
        frames.append(f"data:image/jpeg;base64,{b64}")

    cap.release()
    return frames
