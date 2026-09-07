import json

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1a202c; background: transparent; padding: 5px;}
        .controls { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; background: #ffffff; padding: 16px 20px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
        button { padding: 8px 24px; cursor: pointer; border: none; border-radius: 6px; background: #2b6cb0; color: white; font-weight: 600; font-size: 14px; transition: all 0.2s ease; }
        button:hover { background: #2c5282; box-shadow: 0 2px 4px rgba(43, 108, 176, 0.2); }
        button:active { transform: scale(0.98); }
        input[type=range] { flex-grow: 1; accent-color: #2b6cb0; cursor: pointer; }
        .container { display: flex; width: 100%; height: 550px; gap: 20px; }
        .panel { flex: 1; display: flex; flex-direction: column; background: #ffffff; border-radius: 12px; overflow: hidden; position: relative; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);}
        img { width: 100%; object-fit: contain; background: #f7fafc; height: 100%; }
        h3 { margin: 0; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; position: absolute; top: 16px; left: 16px; z-index: 10; color: #4a5568; background: rgba(255, 255, 255, 0.9); padding: 6px 12px; border-radius: 6px; border: 1px solid #e2e8f0; backdrop-filter: blur(4px);}
        #frame-counter { font-weight: 600; font-size: 14px; color: #4a5568; font-variant-numeric: tabular-nums; min-width: 70px; text-align: right; }
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
        const rangeX = __RANGE_X__;
        const rangeY = __RANGE_Y__;
        const rangeZ = __RANGE_Z__;
        
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval = null;
        
        const playBtn = document.getElementById('play-btn');
        const timeline = document.getElementById('timeline');
        const counter = document.getElementById('frame-counter');
        const vidImg = document.getElementById('vid-img');
        const pcdDiv = document.getElementById('pcd-div');
        
        timeline.max = pcdFrames.length - 1;

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xffffff); 

        const gridHelper = new THREE.GridHelper(5, 25, 0xe2e8f0, 0xf7fafc);
        gridHelper.position.y = 0; 
        scene.add(gridHelper);

        const camera = new THREE.PerspectiveCamera(50, pcdDiv.clientWidth / pcdDiv.clientHeight, 0.01, 100);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(pcdDiv.clientWidth, pcdDiv.clientHeight);
        pcdDiv.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;

        const cx = (rangeX[0] + rangeX[1]) / 2;
        const cy = (rangeY[0] + rangeY[1]) / 2;
        const cz = (rangeZ[0] + rangeZ[1]) / 2;
        controls.target.set(cx, cy, cz); 
        camera.position.set(cx, cy + 1.5, cz + 3);

        const geometry = new THREE.BufferGeometry();
        const material = new THREE.PointsMaterial({ size: 0.03, vertexColors: true });
        const points = new THREE.Points(geometry, material);
        scene.add(points);

        function parseRGB(rgbStr) {
            const parts = rgbStr.substring(4, rgbStr.length - 1).split(',');
            return [parseInt(parts[0]) / 255, parseInt(parts[1]) / 255, parseInt(parts[2]) / 255];
        }

        function updateGeometry(frameIdx) {
            const frame = pcdFrames[frameIdx];
            const numPoints = frame.x.length;
            
            const positions = new Float32Array(numPoints * 3);
            const colors = new Float32Array(numPoints * 3);

            for(let i = 0; i < numPoints; i++) {
                positions[i*3] = frame.x[i];
                positions[i*3+1] = frame.y[i]; 
                positions[i*3+2] = frame.z[i];

                const c = parseRGB(frame.colors[i]);
                colors[i*3] = c[0];
                colors[i*3+1] = c[1];
                colors[i*3+2] = c[2];
            }

            geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        }

        function updateData() {
            updateGeometry(currentFrame);
            
            if (vidFrames.length > 0) {
                let vidIdx = Math.floor((currentFrame / pcdFrames.length) * vidFrames.length);
                vidImg.src = vidFrames[Math.min(vidIdx, vidFrames.length - 1)];
            }
            
            timeline.value = currentFrame;
            counter.innerText = `${currentFrame + 1} / ${pcdFrames.length}`;
        }

        function step() {
            currentFrame = (currentFrame + 1) % pcdFrames.length;
            updateData();
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
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
            updateData();
        });

        window.addEventListener('resize', () => {
            camera.aspect = pcdDiv.clientWidth / pcdDiv.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(pcdDiv.clientWidth, pcdDiv.clientHeight);
        });

        updateData();
        animate();
    </script>
</body>
</html>
"""


def generate_player_html(pcd_frames, vid_frames, target_fps, range_x, range_y, range_z):
    html = HTML_TEMPLATE.replace("__PCD_FRAMES__", json.dumps(pcd_frames))
    html = html.replace("__VID_FRAMES__", json.dumps(vid_frames))
    html = html.replace("__FPS__", str(target_fps))
    html = html.replace("__RANGE_X__", json.dumps(range_x))
    html = html.replace("__RANGE_Y__", json.dumps(range_y))
    html = html.replace("__RANGE_Z__", json.dumps(range_z))
    return html
