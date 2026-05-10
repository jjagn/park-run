import json
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from flask import Flask, Response, redirect, render_template, request, url_for

from config import OUTPUT_DIR, RUNS_DIR, TEMPLATE_FILE
from db import get_all_runs, get_run, init_db, save_run
from download_public_access_areas import ensure_cache
from analyze_gpx import run_analysis
from view import build_map_html, gpx_stats, parse_gpx, parcel_points

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

init_db()


@app.route("/")
def index():
    return render_template("index.html", runs=get_all_runs())


@app.route("/upload")
def upload():
    return render_template("upload.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    name = request.form.get("name", "").strip()
    if not name:
        return "Run name is required", 400

    gpx_file = request.files.get("gpx")
    if not gpx_file:
        return "No file uploaded", 400
    if not gpx_file.filename.lower().endswith(".gpx"):
        return "File must be a .gpx file", 400

    is_public = request.form.get("public") == "on"

    with tempfile.NamedTemporaryFile(suffix=".gpx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        gpx_file.save(tmp_path)

    try:
        ensure_cache()
        visited, _ = run_analysis(tmp_path, OUTPUT_DIR)

        pts = parse_gpx(tmp_path)
        stats = gpx_stats(pts)
        total_score = sum(parcel_points(v["area_m2"]) for v in visited)
        intersected_count = len(visited)

        if is_public:
            run_id = save_run(
                name,
                stats["total_km"], stats["time"], stats["pace"],
                stats["ele_gain"], intersected_count, total_score,
            )
            run_dir = RUNS_DIR / str(run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(tmp_path, run_dir / "track.gpx")
            slim = [{"id": v["id"], "distance_through_m": v["distance_through_m"]} for v in visited]
            (run_dir / "analysis.json").write_text(json.dumps(slim))
            return redirect(url_for("view_run", run_id=run_id))

        html = build_map_html(tmp_path, OUTPUT_DIR, visited, TEMPLATE_FILE)
        return Response(html, mimetype="text/html")

    except ET.ParseError:
        return "Not a valid GPX file", 400
    except ValueError as e:
        return f"Invalid GPX: {e}", 422
    except Exception as e:
        return f"Analysis failed: {e}", 500
    finally:
        tmp_path.unlink(missing_ok=True)


@app.route("/run/<int:run_id>")
def view_run(run_id):
    run = get_run(run_id)
    if not run:
        return "Run not found", 404
    run_dir = RUNS_DIR / str(run_id)
    visited = json.loads((run_dir / "analysis.json").read_text())
    html = build_map_html(run_dir / "track.gpx", OUTPUT_DIR, visited, TEMPLATE_FILE)
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    app.run(debug=True)
