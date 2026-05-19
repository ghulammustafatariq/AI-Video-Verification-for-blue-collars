# 🚀 Fixly AI Verification Engine

**[🔴 Live UI Demo: Click Here] (Replace with your Vercel Link when ready)**

An automated, end-to-end AI pipeline built to verify the skills of blue-collar workers by analyzing trade videos. It utilizes a custom split-stack architecture to handle heavy multi-modal AI processing alongside a seamless React frontend.

### 🛠️ Tech Stack
* **Frontend:** React (Tailwind CSS, Vercel)
* **Backend:** Flask / Python (Render / Railway)
* **AI/ML:** OpenCV, Twelve Labs API (Pegasus 1.2 + Marengo 3.0), Domain RAG
* **Video Processing:** MoviePy, Parallel Threading

---

## 🧠 System Architecture & Data Flow
1. **Input:** Technician uploads a trade video via the React web interface.
2. **Quality Gate:** Flask backend runs an OpenCV script to detect excessive blur and lighting issues before processing.
3. **Processing:** The video is chunked into 40-second segments via MoviePy and uploaded using parallel threads.
4. **AI Layer:** Twelve Labs API performs a 3-run statistical calibration and temporal consistency analysis, while a Domain RAG injects Pakistan Trade Standards (IPC/NEC/PEC).
5. **Output:** A structured JSON response populates the frontend with a verified skill score, SOP violations, and a skill-gap roadmap.

---

## 📸 Application Previews

### 1. AI Analysis & Pipeline Progress
*(Drag and drop your 'AI is analyzing your video' screenshot here)*

### 2. Comprehensive Scoring Dashboard (80/100)
*(Drag and drop your 'AI Analysis Results' screenshot here)*

### 3. Segment Breakdown & Temporal Consistency
*(Drag and drop your detailed violations and temporal consistency graph screenshots here)*

---

## ⚙️ Quick Start (Local Setup)

To run the Flask backend server locally:

```bash
# Clone the repository
git clone [https://github.com/ghulammustafatariq/AI-Video-Verification-for-blue-collars.git](https://github.com/ghulammustafatariq/AI-Video-Verification-for-blue-collars.git)

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask API
python app.py
