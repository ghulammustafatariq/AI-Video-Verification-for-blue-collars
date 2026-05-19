"""
AI Skill Verification System
Twelve Labs pipeline: chunk -> parallel upload -> index -> analyze -> combine
Single Flask server: API + static frontend.
"""

import os, sys, time, json, uuid, re, threading, traceback
from pathlib import Path
from collections import OrderedDict
from queue import Queue

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

from twelvelabs import TwelveLabs
from moviepy import VideoFileClip
from quality.gate import assess_video_quality
from quality.calibration import calibrate, verification_filter, aggregate_calibration
from quality.temporal import analyze_temporal_consistency, compute_fatigue_warning
from quality.roadmap import generate_roadmap

API_KEY = os.getenv("TWELVE_LABS_API_KEY")
if not API_KEY:
    print("[ERROR] TWELVE_LABS_API_KEY not set in .env")
    sys.exit(1)

client = TwelveLabs(api_key=API_KEY)
CHUNK_SECONDS = 40
INDEX_NAME = "fixly-skill-v1"
WORK_DIR = Path(__file__).parent / "work"
WORK_DIR.mkdir(exist_ok=True)
DIST_DIR = Path(__file__).parent / "dist"

app = Flask(__name__)
CORS(app)

# Track active analyses for SSE
active_jobs = {}

# ── Prompt (no markdown, structured JSON request) ──────────────────────────
def build_prompt(category):
    return (
        f'You are an expert trade skill assessor. A worker claims to be a "{category}" technician.\n'
        "Watch this video segment carefully and return ONLY a JSON object with these fields:\n"
        '  "detected_category": the trade actually shown,\n'
        '  "is_correct_category": true or false,\n'
        '  "score": integer 0-100 judging technique, safety, professionalism,\n'
        '  "skill_level": "Master"|"Experienced"|"Competent"|"Developing"|"Not Yet Ready",\n'
        '  "strengths": array of 2-3 specific things done well,\n'
        '  "violations": array of objects {type:"MINOR"|"MAJOR", reason:"..."},\n'
        '  "segments": array of objects {timeRange:"0:00-0:30", actions:"what happened", score:0-100, pass:boolean},\n'
        '  "summary": one sentence assessment.\n'
        "Reply with ONLY the JSON. No markdown, no code fences, no other text."
    )

# ── Twelve Labs helpers ────────────────────────────────────────────────────
def get_or_create_index():
    print("[INDEX] Looking up index...")
    for idx in client.indexes.list():
        name = getattr(idx, "name", getattr(idx, "index_name", ""))
        if name == INDEX_NAME:
            print(f"  Using: {idx.id}")
            return idx.id
    print("  Creating new index...")
    new_idx = client.indexes.create(
        index_name=INDEX_NAME,
        models=[
            {"model_name": "pegasus1.2", "model_options": ["visual", "audio"]},
            {"model_name": "marengo3.0", "model_options": ["visual", "audio"]},
        ],
    )
    print(f"  Created: {new_idx.id}")
    return new_idx.id

def upload_and_wait(index_id, file_path, chunk_num, total, job_id):
    """Upload one chunk, poll until indexed, return video_id."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        raise RuntimeError(f"Chunk {chunk_num+1} missing or empty")
    name = os.path.basename(file_path)
    print(f"  [CHUNK {chunk_num+1}/{total}] Uploading {name}...")
    with open(file_path, "rb") as f:
        task = client.tasks.create(index_id=index_id, video_file=f)
    tid = task.id
    print(f"    Task: {tid} | Polling index status...")
    while True:
        status = client.tasks.retrieve(tid)
        if status.status == "ready":
            print(f"    Chunk {chunk_num+1} indexed. Video ID: {status.video_id}")
            if job_id in active_jobs:
                active_jobs[job_id]["indexed"] += 1
            return status.video_id
        if status.status == "failed":
            raise RuntimeError(f"Chunk {chunk_num+1} indexing FAILED")
        time.sleep(3)

def analyze_video(video_id, prompt):
    gen = client.analyze(video_id=video_id, prompt=prompt)
    return getattr(gen, "data", str(gen))

# ── JSON parsing ───────────────────────────────────────────────────────────
def parse_one(text, chunk_idx):
    """Extract JSON from Twelve Labs text response."""
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        return {"score": 0, "skill_level": "Not Yet Ready", "strengths": [], "violations": [], "segments": [], "summary": text[:100], "_raw": True}
    try:
        return json.loads(match.group(0))
    except:
        return {"score": 0, "skill_level": "Not Yet Ready", "strengths": [], "violations": [], "segments": [], "summary": text[:100], "_raw": True}

def merge_results(parsed_list, category, per_chunk_calibration=None):
    """Combine per-chunk analysis into one final result with calibration data."""
    all_segments = []
    all_strengths = []
    all_violations = []
    scores = []
    detected = category

    time_offset = 0
    last_was_raw = False

    for i, p in enumerate(parsed_list):
        is_raw = p.get("_raw", False)
        if is_raw and not last_was_raw:
            continue  # skip raw fallback chunks
        last_was_raw = is_raw

        score = int(p.get("score", 0))
        if score > 0:
            scores.append(score)

        if p.get("detected_category") and not p.get("_raw"):
            detected = p["detected_category"]

        for seg in p.get("segments", []):
            all_segments.append({
                "id": len(all_segments) + 1,
                "timeRange": seg.get("timeRange", f"{time_offset}:00-{time_offset+CHUNK_SECONDS}:00"),
                "actions": seg.get("actions", "Segment analyzed"),
                "violations": seg.get("violations", 0),
                "score": int(seg.get("score", 50)),
                "pass": bool(seg.get("pass", int(seg.get("score", 50)) >= 55)),
            })
        time_offset += CHUNK_SECONDS

        for s in p.get("strengths", []):
            if s not in all_strengths and len(all_strengths) < 6:
                all_strengths.append(s)
        for v in p.get("violations", []):
            all_violations.append(v)

    avg_score = int(sum(scores) / len(scores)) if scores else 50
    skill_level = (
        "Master" if avg_score >= 90 else "Experienced" if avg_score >= 75 else
        "Competent" if avg_score >= 60 else "Developing" if avg_score >= 40 else "Not Yet Ready"
    )

    is_correct = detected.lower() == category.lower()

    # Zero out score if wrong category — no relevant skills demonstrated
    if not is_correct:
        avg_score = 0
        skill_level = "Not Yet Ready"
        for seg in all_segments:
            seg["score"] = 0
            seg["pass"] = False
        if per_chunk_calibration:
            for c in per_chunk_calibration:
                c.score = 0
                c.individual_scores = [0] * len(c.individual_scores)
                c.score_range = "0-0"

    # Collect verification data from per-chunk calibration
    all_verified_violations = []
    all_unverified_violations = []
    for p in parsed_list:
        vf = p.get("_verification", {})
        for v in vf.get("verified_violations", []):
            if v not in all_verified_violations:
                all_verified_violations.append(v)
        for v in vf.get("unverified_violations", []):
            if v not in all_unverified_violations:
                all_unverified_violations.append(v)

    # Deduplicate violations
    seen_voices = set()
    unique_violations = []
    for v in all_violations:
        key = v.get("reason", str(v))[:80]
        if key not in seen_voices:
            seen_voices.add(key)
            unique_violations.append(v)

    # If no segments from AI, create from time divisions
    if not all_segments:
        time_offset = 0
        for i in range(len(scores) or 1):
            sc = scores[i] if i < len(scores) else avg_score
            all_segments.append({
                "id": i + 1,
                "timeRange": f"{time_offset}:00-{time_offset+CHUNK_SECONDS}:00",
                "actions": "Segment analyzed",
                "violations": 0,
                "score": sc,
                "pass": sc >= 55,
            })
            time_offset += CHUNK_SECONDS

    return {
        "score": avg_score,
        "skillLevel": skill_level,
        "detected_category": detected,
        "is_correct_category": is_correct,
        "segments": all_segments,
        "strengths": all_strengths[:5],
        "violations": unique_violations[:5],
        "verified_violations": all_verified_violations,
        "unverified_violations": all_unverified_violations,
        "temporal": (
            {
                "data": analyze_temporal_consistency(
                    [s["score"] for s in all_segments],
                    [s["timeRange"] for s in all_segments],
                ),
                "fatigue": compute_fatigue_warning(
                    analyze_temporal_consistency(
                        [s["score"] for s in all_segments],
                        [s["timeRange"] for s in all_segments],
                    )
                ),
            }
            if all_segments else None
        ),
        "roadmap": generate_roadmap(unique_violations, avg_score, skill_level),
        "summary": (
            f"Video shows {detected}, not {category}. Score 0 — no relevant trade skills demonstrated."
            if not is_correct
            else f"{skill_level} proficiency in {detected}."
        ),
        "calibration": (
            {
                "aggregate": aggregate_calibration(per_chunk_calibration),
                "per_chunk": [
                    {
                        "chunk": i + 1,
                        "score": c.score,
                        "confidence": c.confidence,
                        "reliability": c.reliability,
                        "variance": c.variance,
                        "score_range": c.score_range,
                        "individual_scores": c.individual_scores,
                    }
                    for i, c in enumerate(per_chunk_calibration)
                ],
            }
            if per_chunk_calibration
            else None
        ),
        "mode": "twelvelabs",
    }

# ── SSE progress helper ────────────────────────────────────────────────────
def progress_event(job_id_data):
    job = active_jobs.get(job_id_data)
    if not job:
        return ""
    j = job
    total = j["total_chunks"]
    idx = j["indexed"]
    an  = j["analyzed"]
    pct = min(95, int(((idx + an) / (total * 2)) * 100)) if total > 0 else 0
    return f"data: {json.dumps({'indexed': idx, 'analyzed': an, 'total': total, 'pct': pct})}\n\n"

# ── Routes ─────────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "twelvelabs": bool(API_KEY)})

@app.route("/analyze", methods=["POST"])
def analyze():
    if "video" not in request.files:
        return jsonify({"error": "No video file"}), 400

    video_file = request.files["video"]
    category   = request.form.get("category", "Other")
    filename   = secure_filename(video_file.filename or f"upload_{uuid.uuid4().hex[:8]}.mp4")
    temp_path  = str(WORK_DIR / filename)
    video_file.save(temp_path)

    try:
        print(f"\n{'='*55}")
        print(f"[REQUEST] {category} | {filename} | {(os.path.getsize(temp_path)/1024/1024):.1f} MB")

        # ── Quality Gate ──
        gate_result = assess_video_quality(temp_path)
        print(f"[GATE] Passed: {gate_result.passed} | Score: {gate_result.quality_score} | Ratio: {gate_result.usability_ratio}")
        if gate_result.issues:
            for issue in gate_result.issues:
                print(f"  Issue: {issue}")

        # Hard-reject very poor quality
        if gate_result.quality_score < 30:
            return jsonify({
                "status": "quality_rejected",
                "quality": {
                    "passed": gate_result.passed,
                    "quality_score": gate_result.quality_score,
                    "usability_ratio": gate_result.usability_ratio,
                    "issues": gate_result.issues,
                    "recommendation": gate_result.recommendation,
                    "metrics": gate_result.metrics,
                }
            }), 422

        quality_info = {
            "passed": gate_result.passed,
            "quality_score": gate_result.quality_score,
            "usability_ratio": gate_result.usability_ratio,
            "issues": gate_result.issues,
            "recommendation": gate_result.recommendation,
            "metrics": gate_result.metrics,
        }

        clip = VideoFileClip(temp_path)
        if clip.h > 720:
            clip = clip.resized(height=720)
        duration = clip.duration

        # Build chunk list
        chunk_files = []
        for i, start in enumerate(range(0, int(duration), CHUNK_SECONDS)):
            end = min(start + CHUNK_SECONDS, duration)
            if end - start < 2:
                break
            cp = str(WORK_DIR / f"chunk_{i}_{uuid.uuid4().hex[:4]}.mp4")
            sub = clip.subclipped(start, end)
            try:
                sub.write_videofile(cp, codec="libx264", audio=False, logger=None)
            except Exception as we:
                print(f"  [WARN] Chunk {i} write failed with audio: {we}. Retrying without audio...")
                sub.write_videofile(cp, codec="libx264", audio=False, logger=None)
            sub.close()
            chunk_files.append({"path": cp, "start": start, "end": end, "index": i})
        clip.close()

        total_chunks = len(chunk_files)
        print(f"[CHUNKS] {total_chunks} chunks from {duration:.1f}s video")

        if total_chunks == 0:
            return jsonify({"error": "Video too short (min 2 seconds)"}), 400

        # Get index, build prompt
        index_id = get_or_create_index()
        prompt   = build_prompt(category)

        # Register job for SSE progress
        job_id = uuid.uuid4().hex
        active_jobs[job_id] = {"total_chunks": total_chunks, "indexed": 0, "analyzed": 0}

        # ── Phase 1: Upload ALL chunks in parallel ──
        print("[UPLOAD] Sending all chunks in parallel...")
        video_ids = [None] * total_chunks

        def upload_chunk(idx):
            cp = chunk_files[idx]
            video_ids[idx] = upload_and_wait(index_id, cp["path"], idx, total_chunks, job_id)

        threads = []
        for i in range(total_chunks):
            t = threading.Thread(target=upload_chunk, args=(i,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        print("[DONE] All chunks indexed.")

        # ── Phase 2: Calibrated analysis of all chunks ──
        print("[ANALYZE] Running calibrated skill assessment (3 runs/chunk)...")
        parsed = []
        per_chunk_calibration = []

        for i, vid in enumerate(video_ids):
            def _analyze(_vid, _prompt):
                return analyze_video(_vid, _prompt)

            print(f"  Calibrating chunk {i+1}/{total_chunks} (video {vid})...")
            try:
                best_result, cal = calibrate(
                    analyze_fn=_analyze,
                    video_id=vid,
                    prompt=prompt,
                    parse_fn=lambda t: parse_one(t, i),
                    num_runs=3,
                    run_verification=True,
                )

                print(f"    Score: {best_result.get('score', '?')} | "
                      f"Reliability: {cal.reliability} | "
                      f"Confidence: {cal.confidence} | "
                      f"Variance: {cal.variance} | "
                      f"Scores: {cal.individual_scores}")

                parsed.append(best_result)
                per_chunk_calibration.append(cal)
            except Exception as chunk_err:
                print(f"    [WARN] Chunk {i+1} analysis failed: {chunk_err}")
                traceback.print_exc()
                # Fallback: use a placeholder result so the rest continues
                fallback = {
                    "score": 50, "skill_level": "Competent",
                    "strengths": [], "violations": [],
                    "segments": [{
                        "timeRange": f"{i*CHUNK_SECONDS}:00-{(i+1)*CHUNK_SECONDS}:00",
                        "actions": "Analysis failed for this segment",
                        "score": 50, "pass": False,
                    }],
                    "summary": "Analysis incomplete",
                }
                parsed.append(fallback)
                from quality.calibration import CalibrationResult
                per_chunk_calibration.append(CalibrationResult(
                    score=50, confidence=0.0, reliability="LOW",
                    variance=99.0, score_range="0-100", num_runs=0,
                    individual_scores=[], recommendation=f"Analysis failed: {chunk_err}",
                ))

            if job_id in active_jobs:
                active_jobs[job_id]["analyzed"] += 1

        # ── Phase 3: Merge results ──
        print("[MERGE] Combining calibrated chunk results...")
        final = merge_results(parsed, category, per_chunk_calibration)
        final["quality"] = quality_info
        print(f"[FINAL] Score: {final['score']} | Level: {final['skillLevel']} | Segments: {len(final['segments'])}")

        if job_id in active_jobs:
            del active_jobs[job_id]

        return jsonify(final)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup with retry for locked files
        import gc
        gc.collect()
        time.sleep(0.5)
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except PermissionError:
            print(f"[WARN] Could not delete temp file: {temp_path}")
        for f in WORK_DIR.glob("chunk_*.mp4"):
            try: os.remove(f)
            except: pass

# ── SSE endpoint for live progress ─────────────────────────────────────────
@app.route("/progress/<job_id>")
def progress(job_id):
    def stream():
        while job_id in active_jobs:
            evt = progress_event(job_id)
            if evt:
                yield evt
            time.sleep(1)
        yield f"data: {json.dumps({'indexed': 0, 'analyzed': 0, 'total': 0, 'pct': 100})}\n\n"
    return Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ── Static frontend ────────────────────────────────────────────────────────
@app.route("/")
def index():
    if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
        return send_from_directory(str(DIST_DIR), "index.html")
    return jsonify({"message": "Frontend not built. Run: npm install && npm run build"})

@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(str(DIST_DIR / "assets"), filename)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n{'='*55}")
    print(f"  AI Skill Verification System")
    print(f"  http://localhost:{port}")
    print(f"  Twelve Labs: {'OK' if API_KEY else 'MISSING'}")
    print(f"  Index: {INDEX_NAME}")
    print(f"{'='*55}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
