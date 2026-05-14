#!/usr/bin/env python3
"""
FocusFlow Smart Workload Planner - Optional Local Web UI
Run this file with: python app.py   (Mac: python3 app.py)
Then open: http://localhost:8000

This web interface uses only Python built-in libraries and reuses main.py.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from datetime import date, timedelta
import json
import os
import webbrowser

from main import FocusFlowPlanner, DATE_FORMAT, ALLOWED_CATEGORIES

HOST = "localhost"
PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
planner = FocusFlowPlanner(os.path.join(BASE_DIR, "tasks.json"))


def task_to_dict(task):
    return {
        "task_id": task.task_id,
        "title": task.title,
        "category": task.category,
        "priority": task.priority,
        "duration_minutes": task.duration_minutes,
        "deadline": task.deadline,
        "status": task.status,
        "created_on": task.created_on,
        "days_left": task.days_left(),
        "deadline_bucket": task.deadline_bucket(),
        "risk_score": task.risk_score(),
        "risk_label": task.risk_label(),
    }


class FocusFlowHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename, content_type):
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            self.send_error(404, "File not found")
            return
        with open(path, "rb") as file:
            body = file.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ["/", "/index.html"]:
            self._send_file("index.html", "text/html; charset=utf-8")
        elif path == "/style.css":
            self._send_file("style.css", "text/css; charset=utf-8")
        elif path == "/script.js":
            self._send_file("script.js", "application/javascript; charset=utf-8")
        elif path == "/api/tasks":
            self._send_json([task_to_dict(task) for task in planner.sorted_pending_tasks() + [t for t in planner.tasks if t.status == "Completed"]])
        elif path == "/api/summary":
            self._send_json(planner.summary())
        elif path == "/api/analysis":
            self._send_json({
                "deadline_analysis": planner.deadline_analysis(),
                "category_analysis": planner.category_analysis(),
                "recommendations": planner.recommendations(),
            })
        elif path == "/api/export":
            filename = planner.export_summary(os.path.join(BASE_DIR, "focusflow_summary.txt"))
            self._send_json({"message": f"Summary exported to {os.path.basename(filename)}"})
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._read_body()
            if path == "/api/tasks":
                task = planner.add_task(
                    data.get("title", ""),
                    data.get("category", "Other"),
                    int(data.get("priority", 3)),
                    int(data.get("duration_minutes", 60)),
                    data.get("deadline", date.today().strftime(DATE_FORMAT)),
                )
                self._send_json({"message": "Task saved successfully.", "task": task_to_dict(task)}, 201)
            elif path == "/api/tasks/done":
                success = planner.mark_done(int(data.get("task_id", 0)))
                self._send_json({"success": success})
            elif path == "/api/tasks/delete":
                success = planner.delete_task(int(data.get("task_id", 0)))
                self._send_json({"success": success})
            elif path == "/api/plan":
                minutes = int(data.get("available_minutes", 180))
                plan, remaining = planner.generate_focus_plan(minutes)
                self._send_json({
                    "available_minutes": minutes,
                    "planned_minutes": min(sum(task.duration_minutes for task in plan), minutes),
                    "remaining_minutes": remaining,
                    "tasks": [task_to_dict(task) for task in plan],
                })
            elif path == "/api/sample":
                sample_data = [
                    ("Submit Python project zip", "Study", 5, 90, date.today().strftime(DATE_FORMAT)),
                    ("Prepare 3-minute project presentation", "Study", 4, 70, (date.today() + timedelta(days=1)).strftime(DATE_FORMAT)),
                    ("Revise weekly lecture notes", "Study", 3, 60, (date.today() + timedelta(days=3)).strftime(DATE_FORMAT)),
                    ("Exercise and reset routine", "Health", 2, 30, (date.today() + timedelta(days=2)).strftime(DATE_FORMAT)),
                    ("Organise assignment files", "Personal", 3, 45, (date.today() + timedelta(days=6)).strftime(DATE_FORMAT)),
                ]
                existing_titles = {task.title.lower() for task in planner.tasks}
                added = 0
                for title, category, priority, duration, deadline in sample_data:
                    if title.lower() not in existing_titles:
                        planner.add_task(title, category, priority, duration, deadline)
                        added += 1
                self._send_json({"message": f"Added {added} sample task(s)."})
            else:
                self.send_error(404, "Not found")
        except (ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, 400)


def run_server():
    server = HTTPServer((HOST, PORT), FocusFlowHandler)
    print(f"FocusFlow web UI is running at http://{HOST}:{PORT}")
    print("Press CTRL+C to stop the server.")
    try:
        webbrowser.open(f"http://{HOST}:{PORT}")
    except Exception:
        pass
    server.serve_forever()


if __name__ == "__main__":
    run_server()
