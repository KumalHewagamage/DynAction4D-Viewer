import base64
import glob
import os

import cv2
import streamlit as st


def get_sequences(dataset_dir):
    pcd_dir = os.path.join(dataset_dir, "pcd")
    if not os.path.exists(pcd_dir):
        return []
    return sorted([d for d in os.listdir(pcd_dir) if d.startswith("sequence_")])


def load_pcd(filepath, solid_color=None):
    x, y, z, colors, labels = [], [], [], [], []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    data_idx = next(i for i, line in enumerate(lines) if line.startswith("DATA")) + 1

    for line in lines[data_idx:]:
        parts = line.strip().split()
        if len(parts) >= 8:
            x.append(float(parts[0]))
            y.append(float(parts[1]))
            z.append(float(parts[2]))

            if solid_color:
                colors.append(solid_color)
            else:
                rgb_int = int(parts[6])
                r, g, b = (rgb_int >> 16) & 255, (rgb_int >> 8) & 255, rgb_int & 255
                colors.append(f"rgb({r}, {g}, {b})")
            labels.append(parts[7])

    return {"x": x, "y": y, "z": z, "colors": colors, "labels": labels}


@st.cache_data
def process_sequence_data(
    seq_pcd_dir, solid_color=None, actor_label_prefixes=("male_", "female_")
):
    frames_list = []
    frames = sorted(glob.glob(os.path.join(seq_pcd_dir, "frame_*.pcd")))

    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    actor_x = []
    actor_z = []

    for f in frames:
        data = load_pcd(f, solid_color)
        frames_list.append(data)
        if data["x"]:
            min_x, max_x = min(min_x, *data["x"]), max(max_x, *data["x"])
            min_y, max_y = min(min_y, *data["y"]), max(max_y, *data["y"])
            min_z, max_z = min(min_z, *data["z"]), max(max_z, *data["z"])
            for x, z, label in zip(data["x"], data["z"], data["labels"]):
                if label.startswith(actor_label_prefixes):
                    actor_x.append(x)
                    actor_z.append(z)

    if not frames_list or min_x == float("inf"):
        return frames_list, [-1, 1], [0, 2], [-1, 1]

    actor_center_x = sum(actor_x) / len(actor_x) if actor_x else (max_x + min_x) / 2
    actor_center_z = sum(actor_z) / len(actor_z) if actor_z else (max_z + min_z) / 2
    horizontal_span = max(max_x - min_x, max_z - min_z, 0.1)
    horizontal_padding = horizontal_span * 0.1
    vertical_padding = max(max_y - min_y, 0.1) * 0.1

    for frame in frames_list:
        frame["x"] = [value - actor_center_x for value in frame["x"]]
        frame["y"] = [value - min_y for value in frame["y"]]
        frame["z"] = [value - actor_center_z for value in frame["z"]]

    return (
        frames_list,
        [
            min_x - actor_center_x - horizontal_padding,
            max_x - actor_center_x + horizontal_padding,
        ],
        [0, max_y - min_y + vertical_padding],
        [
            min_z - actor_center_z - horizontal_padding,
            max_z - actor_center_z + horizontal_padding,
        ],
    )


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
