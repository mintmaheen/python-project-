#!/usr/bin/env python3
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
import json
import os
from typing import Dict, List, Optional, Tuple

DATA_FILE = "tasks.json"
DATE_FORMAT = "%Y-%m-%d"
ALLOWED_CATEGORIES = ["Study", "Personal", "Health", "Work", "Other"]
ALLOWED_STATUS = ["Pending", "Completed"]


@dataclass
class Task:
    """Represents one task with the information needed for workload analysis."""
    task_id: int
    title: str
    category: str
    priority: int
    duration_minutes: int
    deadline: str
    status: str = "Pending"
    created_on: str = ""

    def __post_init__(self) -> None:
        if not self.created_on:
            self.created_on = date.today().strftime(DATE_FORMAT)
        if self.category not in ALLOWED_CATEGORIES:
            self.category = "Other"
        if self.status not in ALLOWED_STATUS:
            self.status = "Pending"

    def deadline_date(self) -> date:
        return datetime.strptime(self.deadline, DATE_FORMAT).date()

    def days_left(self) -> int:
        return (self.deadline_date() - date.today()).days

    def is_overdue(self) -> bool:
        return self.status == "Pending" and self.days_left() < 0

    def deadline_bucket(self) -> str:
        """Places the task into a deadline group used by the dashboard."""
        days = self.days_left()
        if self.status == "Completed":
            return "Completed"
        if days < 0:
            return "Overdue"
        if days == 0:
            return "Due Today"
        if days <= 2:
            return "Due in 1-2 Days"
        if days <= 7:
            return "Due This Week"
        return "Later"

    def risk_score(self) -> float:
        """
        Calculates a meaningful workload risk score from priority, deadline pressure
        and task duration. A higher score means the task needs attention earlier.
        """
        if self.status == "Completed":
            return 0.0
        days = self.days_left()
        if days < 0:
            deadline_pressure = 45 + abs(days) * 4
        else:
            deadline_pressure = max(0, 35 - days * 5)
        priority_pressure = self.priority * 12
        duration_pressure = min(self.duration_minutes / 20, 12)
        return round(priority_pressure + deadline_pressure + duration_pressure, 2)

    def risk_label(self) -> str:
        score = self.risk_score()
        if self.status == "Completed":
            return "Completed"
        if score >= 85:
            return "Critical"
        if score >= 65:
            return "High"
        if score >= 40:
            return "Medium"
        return "Low"

    def productivity_points(self) -> int:
        """A simple reward score for completed tasks used in the summary."""
        if self.status != "Completed":
            return 0
        return self.priority * 10 + max(1, self.duration_minutes // 30)


class FocusFlowPlanner:
    """Main application class that manages tasks, analysis and recommendations."""

    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.tasks: List[Task] = []
        self.load_tasks()

    def load_tasks(self) -> None:
        """Loads saved tasks from JSON. Starts safely if the file is missing/corrupt."""
        if not os.path.exists(self.data_file):
            self.tasks = []
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as file:
                raw_tasks = json.load(file)
            self.tasks = [Task(**item) for item in raw_tasks]
        except (json.JSONDecodeError, TypeError, OSError) as error:
            print(f"Warning: Could not load saved tasks because: {error}")
            print("Starting with an empty task list.")
            self.tasks = []

    def save_tasks(self) -> None:
        with open(self.data_file, "w", encoding="utf-8") as file:
            json.dump([asdict(task) for task in self.tasks], file, indent=4)

    def next_task_id(self) -> int:
        return max((task.task_id for task in self.tasks), default=0) + 1

    def validate_task_input(self, title: str, category: str, priority: int,
                            duration: int, deadline: str) -> None:
        if not title.strip():
            raise ValueError("Task title cannot be empty.")
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(ALLOWED_CATEGORIES)}")
        if priority < 1 or priority > 5:
            raise ValueError("Priority must be between 1 and 5.")
        if duration < 10 or duration > 720:
            raise ValueError("Duration must be between 10 and 720 minutes.")
        try:
            datetime.strptime(deadline, DATE_FORMAT).date()
        except ValueError as exc:
            raise ValueError("Deadline must use YYYY-MM-DD format.") from exc

    def add_task(self, title: str, category: str, priority: int, duration: int, deadline: str) -> Task:
        self.validate_task_input(title, category, priority, duration, deadline)
        task = Task(
            task_id=self.next_task_id(),
            title=title.strip(),
            category=category,
            priority=priority,
            duration_minutes=duration,
            deadline=deadline,
        )
        self.tasks.append(task)
        self.save_tasks()
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        return next((task for task in self.tasks if task.task_id == task_id), None)

    def mark_done(self, task_id: int) -> bool:
        task = self.get_task(task_id)
        if not task:
            return False
        task.status = "Completed"
        self.save_tasks()
        return True

    def delete_task(self, task_id: int) -> bool:
        original_count = len(self.tasks)
        self.tasks = [task for task in self.tasks if task.task_id != task_id]
        changed = len(self.tasks) != original_count
        if changed:
            self.save_tasks()
        return changed

    def pending_tasks(self) -> List[Task]:
        return [task for task in self.tasks if task.status == "Pending"]

    def sorted_pending_tasks(self) -> List[Task]:
        return sorted(
            self.pending_tasks(),
            key=lambda task: (-task.risk_score(), task.deadline_date(), -task.priority, task.duration_minutes),
        )

    def summary(self) -> Dict[str, object]:
        total = len(self.tasks)
        completed = len([task for task in self.tasks if task.status == "Completed"])
        pending = total - completed
        overdue = len([task for task in self.pending_tasks() if task.is_overdue()])
        due_today = len([task for task in self.pending_tasks() if task.days_left() == 0])
        due_week = len([task for task in self.pending_tasks() if 0 <= task.days_left() <= 7])
        pending_minutes = sum(task.duration_minutes for task in self.pending_tasks())
        avg_risk = 0 if pending == 0 else round(sum(task.risk_score() for task in self.pending_tasks()) / pending, 2)
        category_load: Dict[str, int] = {}
        for task in self.pending_tasks():
            category_load[task.category] = category_load.get(task.category, 0) + task.duration_minutes
        heaviest_category = max(category_load, key=category_load.get) if category_load else "None"
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "due_today": due_today,
            "due_week": due_week,
            "pending_minutes": pending_minutes,
            "pending_hours": round(pending_minutes / 60, 1),
            "completion_rate": 0 if total == 0 else round((completed / total) * 100, 1),
            "average_risk": avg_risk,
            "heaviest_category": heaviest_category,
            "productivity_points": sum(task.productivity_points() for task in self.tasks),
        }

    def deadline_analysis(self) -> Dict[str, int]:
        buckets = {
            "Overdue": 0,
            "Due Today": 0,
            "Due in 1-2 Days": 0,
            "Due This Week": 0,
            "Later": 0,
            "Completed": 0,
        }
        for task in self.tasks:
            buckets[task.deadline_bucket()] += 1
        return buckets

    def category_analysis(self) -> Dict[str, Dict[str, int]]:
        analysis: Dict[str, Dict[str, int]] = {}
        for task in self.tasks:
            if task.category not in analysis:
                analysis[task.category] = {"tasks": 0, "pending": 0, "minutes": 0}
            analysis[task.category]["tasks"] += 1
            if task.status == "Pending":
                analysis[task.category]["pending"] += 1
                analysis[task.category]["minutes"] += task.duration_minutes
        return analysis

    def generate_focus_plan(self, available_minutes: int) -> Tuple[List[Task], int]:
        """
        Builds a realistic daily plan. It first chooses urgent tasks, then fills any
        remaining time with smaller tasks. This keeps the feature beyond CRUD.
        """
        if available_minutes <= 0:
            raise ValueError("Available minutes must be above 0.")
        selected: List[Task] = []
        remaining = available_minutes
        urgent_order = self.sorted_pending_tasks()

        for task in urgent_order:
            if task.duration_minutes <= remaining:
                selected.append(task)
                remaining -= task.duration_minutes

        # If no full task fits, recommend the highest-risk task as a partial-start item.
        if not selected and urgent_order:
            selected.append(urgent_order[0])
            remaining = 0
        return selected, remaining

    def recommendations(self) -> List[str]:
        """Creates human-readable recommendations based on task data."""
        summary = self.summary()
        pending = self.sorted_pending_tasks()
        advice: List[str] = []

        if summary["pending"] == 0:
            return ["All tasks are complete. Add a new meaningful goal for the week."]
        if summary["overdue"]:
            advice.append(f"Start with overdue tasks first: {summary['overdue']} task(s) have passed their deadline.")
        if summary["due_today"]:
            advice.append(f"Protect time today: {summary['due_today']} pending task(s) are due today.")
        if pending:
            top = pending[0]
            advice.append(f"Recommended next task: '{top.title}' because it has {top.risk_label().lower()} risk and deadline pressure.")
        if summary["pending_minutes"] > 480:
            advice.append("Your pending workload is above 8 hours. Split large tasks or move lower-priority tasks to another day.")
        if summary["average_risk"] >= 65:
            advice.append("Average workload risk is high. Focus on fewer tasks and complete the top 2-3 before adding new work.")
        if summary["heaviest_category"] != "None":
            advice.append(f"Most remaining time is in the {summary['heaviest_category']} category, so review whether that area needs extra planning.")
        return advice[:5]

    def export_summary(self, filename: str = "focusflow_summary.txt") -> str:
        """Exports analysis and recommendations for submission/demo evidence."""
        summary = self.summary()
        deadline = self.deadline_analysis()
        category = self.category_analysis()
        lines = [
            "FocusFlow Smart Workload Planner - Summary Report",
            "=================================================",
            f"Generated on: {date.today().strftime(DATE_FORMAT)}",
            "",
            "Overall Summary",
            f"Total tasks: {summary['total']}",
            f"Completed tasks: {summary['completed']}",
            f"Pending tasks: {summary['pending']}",
            f"Completion rate: {summary['completion_rate']}%",
            f"Pending workload: {summary['pending_minutes']} minutes ({summary['pending_hours']} hours)",
            f"Average risk score: {summary['average_risk']}",
            "",
            "Deadline Analysis",
        ]
        for bucket, count in deadline.items():
            lines.append(f"- {bucket}: {count}")
        lines.append("")
        lines.append("Category Workload")
        for category_name, values in category.items():
            lines.append(f"- {category_name}: {values['pending']} pending task(s), {values['minutes']} minutes")
        lines.append("")
        lines.append("Recommendations")
        for number, recommendation in enumerate(self.recommendations(), start=1):
            lines.append(f"{number}. {recommendation}")
        with open(filename, "w", encoding="utf-8") as file:
            file.write("\n".join(lines))
        return filename


def input_integer(prompt: str, minimum: int, maximum: int) -> int:
    while True:
        try:
            value = int(input(prompt))
            if value < minimum or value > maximum:
                print(f"Please enter a number between {minimum} and {maximum}.")
                continue
            return value
        except ValueError:
            print("Please enter a valid whole number.")


def input_deadline() -> str:
    while True:
        value = input("Deadline (YYYY-MM-DD): ").strip()
        try:
            datetime.strptime(value, DATE_FORMAT).date()
            return value
        except ValueError:
            print("Please use the correct format, for example 2026-05-24.")


def print_task_table(tasks: List[Task]) -> None:
    if not tasks:
        print("No tasks to show.")
        return
    print("\nID | Priority | Risk | Deadline | Duration | Status    | Category | Title")
    print("-" * 92)
    for task in tasks:
        print(
            f"{task.task_id:<2} | {task.priority:<8} | {task.risk_label():<8} | "
            f"{task.deadline:<10} | {task.duration_minutes:<8} | {task.status:<9} | "
            f"{task.category:<8} | {task.title}"
        )


def add_task_flow(planner: FocusFlowPlanner) -> None:
    print("\nAdd a New Task")
    title = input("Task title: ").strip()
    print("Categories:", ", ".join(ALLOWED_CATEGORIES))
    category = input("Category: ").strip().title()
    priority = input_integer("Priority (1 low - 5 high): ", 1, 5)
    duration = input_integer("Estimated duration in minutes (10-720): ", 10, 720)
    deadline = input_deadline()
    try:
        task = planner.add_task(title, category, priority, duration, deadline)
        print(f"Saved task #{task.task_id}: {task.title}")
    except ValueError as error:
        print(f"Task was not saved: {error}")


def dashboard_flow(planner: FocusFlowPlanner) -> None:
    summary = planner.summary()
    print("\nSmart Workload Dashboard")
    print("=" * 30)
    print(f"Total tasks: {summary['total']}")
    print(f"Completed: {summary['completed']} | Pending: {summary['pending']} | Completion: {summary['completion_rate']}%")
    print(f"Overdue: {summary['overdue']} | Due today: {summary['due_today']} | Due this week: {summary['due_week']}")
    print(f"Pending workload: {summary['pending_minutes']} minutes ({summary['pending_hours']} hours)")
    print(f"Average risk score: {summary['average_risk']} | Heaviest category: {summary['heaviest_category']}")
    print(f"Productivity points earned: {summary['productivity_points']}")
    print("\nDeadline Analysis:")
    for bucket, count in planner.deadline_analysis().items():
        print(f"- {bucket}: {count}")
    print("\nRecommendations:")
    for number, item in enumerate(planner.recommendations(), start=1):
        print(f"{number}. {item}")


def plan_flow(planner: FocusFlowPlanner) -> None:
    minutes = input_integer("How many minutes are available today? ", 1, 720)
    try:
        plan, remaining = planner.generate_focus_plan(minutes)
    except ValueError as error:
        print(error)
        return
    print("\nRecommended Focus Plan")
    print("=" * 28)
    if not plan:
        print("No pending tasks available.")
        return
    total = sum(task.duration_minutes for task in plan)
    for index, task in enumerate(plan, start=1):
        note = ""
        if task.duration_minutes > minutes and len(plan) == 1:
            note = " (start this task, even if you cannot finish it today)"
        print(f"{index}. {task.title} - {task.duration_minutes} min, {task.risk_label()} risk, due {task.deadline}{note}")
    print(f"Planned minutes: {min(total, minutes)}")
    print(f"Remaining free minutes: {remaining}")


def seed_sample_tasks(planner: FocusFlowPlanner) -> None:
    sample_data = [
        ("Submit Python project zip", "Study", 5, 90, date.today().strftime(DATE_FORMAT)),
        ("Prepare 3-minute project presentation", "Study", 4, 70, (date.today() + timedelta(days=1)).strftime(DATE_FORMAT)),
        ("Revise weekly lecture notes", "Study", 3, 60, (date.today() + timedelta(days=3)).strftime(DATE_FORMAT)),
        ("Exercise and reset routine", "Health", 2, 30, (date.today() + timedelta(days=2)).strftime(DATE_FORMAT)),
        ("Organise assignment files", "Personal", 3, 45, (date.today() + timedelta(days=6)).strftime(DATE_FORMAT)),
    ]
    added = 0
    existing_titles = {task.title.lower() for task in planner.tasks}
    for title, category, priority, duration, deadline in sample_data:
        if title.lower() not in existing_titles:
            planner.add_task(title, category, priority, duration, deadline)
            added += 1
    print(f"Added {added} sample task(s).")


def main() -> None:
    planner = FocusFlowPlanner()
    while True:
        print("\nFocusFlow Smart Workload Planner")
        print("1. Add task")
        print("2. View tasks sorted by risk")
        print("3. Smart workload dashboard")
        print("4. Generate daily focus plan")
        print("5. Mark task as completed")
        print("6. Delete task")
        print("7. Add sample tasks for demo")
        print("8. Export summary report")
        print("9. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_task_flow(planner)
        elif choice == "2":
            print_task_table(planner.sorted_pending_tasks() + [task for task in planner.tasks if task.status == "Completed"])
        elif choice == "3":
            dashboard_flow(planner)
        elif choice == "4":
            plan_flow(planner)
        elif choice == "5":
            task_id = input_integer("Task ID to complete: ", 1, 99999)
            print("Task marked completed." if planner.mark_done(task_id) else "Task ID not found.")
        elif choice == "6":
            task_id = input_integer("Task ID to delete: ", 1, 99999)
            print("Task deleted." if planner.delete_task(task_id) else "Task ID not found.")
        elif choice == "7":
            seed_sample_tasks(planner)
        elif choice == "8":
            filename = planner.export_summary()
            print(f"Summary exported to {filename}")
        elif choice == "9":
            print("Goodbye. Stay focused!")
            break
        else:
            print("Invalid choice. Please choose 1-9.")


if __name__ == "__main__":
    main()
