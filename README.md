# python-project-
FocusFlow is a smart and easy-to-use productivity planner designed to help students stay organised, focused, and motivated in their daily lives
FocusFlow Smart Workload Planner
=================================

Project category: Productive Task and Workload Management

Main file to run for marking:
- Terminal version: main.py
- Optional web demo: app.py

Functionalities of the application:

1. Risk score calculation
   Each pending task receives a score based on priority, deadline pressure and duration.

2. Deadline analysis
   Tasks are grouped into Overdue, Due Today, Due in 1-2 Days, Due This Week, Later and Completed.

3. Workload analysis
   The program calculates pending workload hours, average risk and the category taking the most time.

4. Smart recommendations
   The program recommends what the user should do next and warns about overdue tasks, heavy workload and high average risk.

5. Daily focus plan
   The program uses a greedy scheduling algorithm to choose high-risk tasks that fit the user's available time.

Files included
--------------
main.py                         Main terminal-based Python program. 
app.py                          Local web UI server for demonstration.
index.html                      Web interface structure.
style.css                       Web page styling.
script.js                       Web interactivity and API calls.
README.txt                      Description about project
requirements.txt                Confirms that no external libraries are required.

------------------------
For the terminal version : 
Run python 3 main.py
For the UI Web version :   
Run python3 app.py
Open this address in your browser:
   http://localhost:8000 

-------------------
Suggested demo steps
--------------------
1. Run python3 app.py on Mac or python app.py on Windows.
2. Click Add Sample Tasks.
3. Check the dashboard values: overdue, due today, due this week, pending hours and average risk.
4. See the Deadline Buckets and Recommendations section.
5. Generate a daily focus plan with 180 minutes.
6. Add one new task with high priority and today's deadline.
7. Mark one task as completed and show that the dashboard changes.
8. Export the summary report.

Programming concepts demonstrated
---------------------------------
- Object-oriented programming: Task and FocusFlowPlanner classes.
- File handling: JSON saving/loading and text summary export.
- Exception handling: invalid file, invalid dates and incorrect inputs.
- Data structures: lists, dictionaries and dataclasses.
- Sorting and filtering: tasks sorted by risk and deadline.
- Algorithms: risk scoring and greedy daily focus planning.
- Web/networking built from Python's built-in http.server for optional demo.

