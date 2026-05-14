const taskForm = document.getElementById("taskForm");
const formMessage = document.getElementById("formMessage");
const taskTable = document.getElementById("taskTable");
const planList = document.getElementById("planList");

function todayISO() {
  return new Date().toISOString().split("T")[0];
}

document.getElementById("deadline").min = todayISO();
document.getElementById("deadline").value = todayISO();

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  return response.json();
}

async function refreshAll() {
  await loadSummary();
  await loadAnalysis();
  await loadTasks();
}

async function loadSummary() {
  const data = await api("/api/summary");
  document.getElementById("totalTasks").textContent = data.total;
  document.getElementById("pendingTasks").textContent = data.pending;
  document.getElementById("overdueTasks").textContent = data.overdue;
  document.getElementById("completionRate").textContent = `${data.completion_rate}%`;
  document.getElementById("dueToday").textContent = data.due_today;
  document.getElementById("dueWeek").textContent = data.due_week;
  document.getElementById("pendingHours").textContent = data.pending_hours;
  document.getElementById("averageRisk").textContent = data.average_risk;
}

async function loadAnalysis() {
  const data = await api("/api/analysis");
  const deadlineBuckets = document.getElementById("deadlineBuckets");
  deadlineBuckets.innerHTML = "";
  for (const [name, count] of Object.entries(data.deadline_analysis)) {
    deadlineBuckets.innerHTML += `<div class="bucket"><span>${name}</span><strong>${count}</strong></div>`;
  }

  const categoryWorkload = document.getElementById("categoryWorkload");
  categoryWorkload.innerHTML = "";
  const categories = Object.entries(data.category_analysis);
  if (!categories.length) {
    categoryWorkload.innerHTML = `<div class="bucket"><span>No categories yet</span><strong>0</strong></div>`;
  } else {
    for (const [name, values] of categories) {
      categoryWorkload.innerHTML += `<div class="bucket"><span>${name}</span><strong>${values.pending} task(s), ${values.minutes} min</strong></div>`;
    }
  }

  const recommendations = document.getElementById("recommendations");
  recommendations.innerHTML = "";
  for (const item of data.recommendations) {
    recommendations.innerHTML += `<li>${item}</li>`;
  }
}

async function loadTasks() {
  const tasks = await api("/api/tasks");
  taskTable.innerHTML = "";
  if (!tasks.length) {
    taskTable.innerHTML = `<tr><td colspan="9">No tasks yet. Add a task or use sample tasks.</td></tr>`;
    return;
  }
  for (const task of tasks) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${task.task_id}</td>
      <td>${task.title}</td>
      <td>${task.category}</td>
      <td>${task.priority}</td>
      <td>${task.duration_minutes} min</td>
      <td>${task.deadline}<br><small>${task.deadline_bucket}</small></td>
      <td><span class="risk ${task.risk_label.toLowerCase()}">${task.risk_label}</span><br><small>${task.risk_score}</small></td>
      <td><span class="status ${task.status.toLowerCase()}">${task.status}</span></td>
      <td>
        ${task.status === "Pending" ? `<button class="done" onclick="markDone(${task.task_id})">Done</button>` : ""}
        <button class="danger" onclick="deleteTask(${task.task_id})">Delete</button>
      </td>
    `;
    taskTable.appendChild(row);
  }
}

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    title: document.getElementById("title").value,
    category: document.getElementById("category").value,
    priority: Number(document.getElementById("priority").value),
    duration_minutes: Number(document.getElementById("duration").value),
    deadline: document.getElementById("deadline").value,
  };
  const result = await api("/api/tasks", { method: "POST", body: JSON.stringify(payload) });
  formMessage.textContent = result.message || result.error;
  if (!result.error) {
    taskForm.reset();
    document.getElementById("deadline").value = todayISO();
  }
  await refreshAll();
});

async function markDone(taskId) {
  await api("/api/tasks/done", { method: "POST", body: JSON.stringify({ task_id: taskId }) });
  await refreshAll();
}

async function deleteTask(taskId) {
  await api("/api/tasks/delete", { method: "POST", body: JSON.stringify({ task_id: taskId }) });
  await refreshAll();
}

async function generatePlan() {
  const minutes = Number(document.getElementById("availableMinutes").value);
  const data = await api("/api/plan", { method: "POST", body: JSON.stringify({ available_minutes: minutes }) });
  planList.innerHTML = "";
  if (data.error) {
    planList.innerHTML = `<p class="message">${data.error}</p>`;
    return;
  }
  if (!data.tasks.length) {
    planList.innerHTML = `<p class="message">No pending tasks available.</p>`;
    return;
  }
  data.tasks.forEach((task, index) => {
    planList.innerHTML += `
      <div class="plan-item">
        <strong>${index + 1}. ${task.title}</strong><br>
        ${task.duration_minutes} minutes • ${task.risk_label} risk • due ${task.deadline}
      </div>`;
  });
  planList.innerHTML += `<p class="message">Planned: ${data.planned_minutes} min | Remaining: ${data.remaining_minutes} min</p>`;
}

async function loadSampleTasks() {
  const result = await api("/api/sample", { method: "POST", body: JSON.stringify({}) });
  formMessage.textContent = result.message;
  await refreshAll();
}

async function exportSummary() {
  const result = await api("/api/export");
  alert(result.message || result.error);
}

refreshAll();
