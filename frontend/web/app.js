const $ = (id) => document.getElementById(id)

const state = {
  data: null,
  lastOkAt: null,
  refreshTimer: null,
  taskId: null,
  pendingQuery: null,
  pendingOpen: false,
  pollingPaused: false,
}

const AGENT_AVATAR_URL =
  "https://storage-public.zhaopin.cn/user/avatar/b4a36c5df1d845de9372f4dab5dbb3dd/timg.jpg"

const REFRESH_MS = 5000
const API_BASE = `http://${window.location.hostname}:8000/api`

function isBlank(v) {
  return v == null || String(v).trim() === ""
}

function setText(id, text) {
  const el = $(id)
  if (!el) return
  el.textContent = text
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function safeLinkHref(href) {
  const raw = String(href || "").trim()
  const lowered = raw.toLowerCase()
  if (lowered.startsWith("javascript:") || lowered.startsWith("data:")) return ""
  return raw
}

function formatInlineMarkdown(text) {
  let s = escapeHtml(text)
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
    const href = safeLinkHref(url)
    if (!href) return label
    return `<a href="${escapeHtml(href)}" target="_blank" rel="noreferrer noopener">${label}</a>`
  })
  s = s.replace(/`([^`]+)`/g, (_, code) => `<code>${code}</code>`)
  s = s.replace(/\*\*([^*]+)\*\*/g, (_, bold) => `<strong>${bold}</strong>`)
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, (_, pre, ital) => `${pre}<em>${ital}</em>`)
  return s
}

function renderMarkdown(md) {
  const src = String(md || "")
  const lines = src.replaceAll("\r\n", "\n").replaceAll("\r", "\n").split("\n")
  const out = []
  let inCode = false
  let codeLang = ""
  let codeLines = []
  let listType = null
  const isTableSep = (line) => {
    const t = String(line || "").trim()
    if (!t) return false
    let s = t
    if (s.startsWith("|")) s = s.slice(1)
    if (s.endsWith("|")) s = s.slice(0, -1)
    const parts = s.split("|").map((x) => x.trim())
    if (!parts.length) return false
    return parts.every((cell) => /^:?-{3,}:?$/.test(cell))
  }
  const parseTableRow = (line) => {
    let s = String(line || "").trim()
    if (s.startsWith("|")) s = s.slice(1)
    if (s.endsWith("|")) s = s.slice(0, -1)
    return s.split("|").map((x) => x.trim())
  }
  const closeList = () => {
    if (!listType) return
    out.push(listType === "ol" ? "</ol>" : "</ul>")
    listType = null
  }
  const openList = (t) => {
    if (listType === t) return
    closeList()
    listType = t
    out.push(t === "ol" ? "<ol>" : "<ul>")
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i] ?? ""
    const fence = line.match(/^\s*```(\w+)?\s*$/)
    if (fence) {
      if (!inCode) {
        closeList()
        inCode = true
        codeLang = fence[1] || ""
        codeLines = []
      } else {
        const code = escapeHtml(codeLines.join("\n"))
        out.push(`<pre><code${codeLang ? ` class="lang-${escapeHtml(codeLang)}"` : ""}>${code}</code></pre>`)
        inCode = false
        codeLang = ""
        codeLines = []
      }
      continue
    }
    if (inCode) {
      codeLines.push(line)
      continue
    }

    if (String(line).trim() === "") {
      closeList()
      continue
    }

    if (String(line).includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      closeList()
      const headerCells = parseTableRow(line)
      const rows = []
      i += 2
      for (; i < lines.length; i++) {
        const rowLine = lines[i] ?? ""
        if (String(rowLine).trim() === "") break
        if (!String(rowLine).includes("|")) break
        rows.push(parseTableRow(rowLine))
      }
      i -= 1
      const thead = `<thead><tr>${headerCells.map((c) => `<th>${formatInlineMarkdown(c)}</th>`).join("")}</tr></thead>`
      const tbody = `<tbody>${rows
        .map((r) => `<tr>${r.map((c) => `<td>${formatInlineMarkdown(c)}</td>`).join("")}</tr>`)
        .join("")}</tbody>`
      out.push(`<table>${thead}${tbody}</table>`)
      continue
    }

    const h = line.match(/^(#{1,3})\s+(.*)$/)
    if (h) {
      closeList()
      const level = h[1].length
      out.push(`<h${level}>${formatInlineMarkdown(h[2])}</h${level}>`)
      continue
    }

    const ul = line.match(/^\s*[-*+]\s+(.*)$/)
    if (ul) {
      openList("ul")
      out.push(`<li>${formatInlineMarkdown(ul[1])}</li>`)
      continue
    }
    const ol = line.match(/^\s*\d+\.\s+(.*)$/)
    if (ol) {
      openList("ol")
      out.push(`<li>${formatInlineMarkdown(ol[1])}</li>`)
      continue
    }

    closeList()
    out.push(`<p>${formatInlineMarkdown(line)}</p>`)
  }
  closeList()
  return out.join("\n")
}

function nowClock() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, "0")
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function setStatus(kind, text) {
  const el = $("status")
  el.classList.remove("online", "offline")
  if (kind) el.classList.add(kind)
  $("statusText").textContent = text
}

function toneForRole(role) {
  const r = String(role || "").trim()
  if (!r) return "中性"
  if (/user|用户/i.test(r)) return "需求表达"
  if (/澄清|clar/i.test(r)) return "追问澄清"
  if (/工程师|dev|engineer/i.test(r)) return "执行推进"
  if (/规划|plan|planner/i.test(r)) return "结构化规划"
  return "协作对话"
}

function avatarLetter(role) {
  const r = String(role || "").trim()
  if (!r) return "?"
  return r.slice(0, 1).toUpperCase()
}

function roleKind(role) {
  const r = String(role || "").trim()
  if (/user|用户/i.test(r)) return "user"
  return "agent"
}

function renderChat(chatBody) {
  const root = $("chatList")
  root.innerHTML = ""
  const items = Array.isArray(chatBody) ? chatBody : []
  if (!items.length) {
    root.innerHTML = `<div class="card-sub">暂无对话内容</div>`
    return
  }

  for (const item of items) {
    const role = item?.role ?? ""
    const content = item?.content ?? ""
    const kind = roleKind(role)
    const html = `
      <div class="bubble ${kind}">
        <div class="ico">${escapeHtml(avatarLetter(role))}</div>
        <div class="bubble-box">
          <div class="bubble-hd">
            <div class="who">${escapeHtml(role || "未知角色")}</div>
            <div class="tone">${escapeHtml(toneForRole(role))}</div>
          </div>
          <div class="bubble-text">${escapeHtml(content)}</div>
        </div>
      </div>
    `
    root.insertAdjacentHTML("beforeend", html)
  }
  root.scrollTop = root.scrollHeight
}

function safeArray(v) {
  return Array.isArray(v) ? v : []
}

function normalizeIndex(i, length) {
  if (!Number.isFinite(i)) return null
  if (length <= 0) return null
  const n = Number(i)
  if (n >= 1 && n <= length) return n - 1
  if (n >= 0 && n < length) return n
  return null
}

function renderPlan(planBody) {
  if (!planBody || (typeof planBody === "object" && Object.keys(planBody).length === 0)) {
    $("overallGoal").textContent = "暂无计划"
    const progressLabel = $("progressLabel")
    if (progressLabel) progressLabel.textContent = "—"
    const progressBar = $("progressBar")
    if (progressBar) progressBar.style.width = "0%"
    $("taskList").innerHTML = `<div class="card-sub">暂无任务拆解</div>`
    $("nextStep").textContent = "暂无下一步"
    const chip = $("missionChip")
    if (chip) {
      chip.textContent = "—"
      chip.removeAttribute("data-state")
    }
    return
  }

  const overallGoal = planBody?.overall_goal ?? "—"
  $("overallGoal").innerHTML = isBlank(overallGoal) ? "—" : `<div class="overall-goal-text">整体任务：${escapeHtml(overallGoal)}</div>`

  const tasks = safeArray(planBody?.tasks)
  const finishedCount = tasks.filter((t) => Boolean(t?.finished)).length
  const progressLabel = $("progressLabel")
  const progressBar = $("progressBar")
  if (!tasks.length) {
    if (progressLabel) progressLabel.textContent = "0/0 · —"
    if (progressBar) progressBar.style.width = "0%"
  } else {
    const pct = Math.round((finishedCount / tasks.length) * 100)
    if (progressLabel) progressLabel.textContent = `${finishedCount}/${tasks.length} 已完成 · ${pct}%`
    if (progressBar) progressBar.style.width = `${Math.min(100, Math.max(0, pct))}%`
  }

  const list = $("taskList")
  list.innerHTML = ""
  if (!tasks.length) {
    list.innerHTML = `<div class="card-sub">暂无任务拆解</div>`
  } else {
    let firstPendingFound = false
    tasks.forEach((t, idx) => {
      const name = t?.task_name ?? `任务 ${idx + 1}`
      const done = Boolean(t?.finished)
      let statusText = "进行中"
      let statusClass = ""
      if (done) {
        statusText = "已完成"
        statusClass = "done"
      } else if (firstPendingFound) {
        statusText = "待执行"
        statusClass = "pending"
      } else {
        firstPendingFound = true
        statusText = "进行中"
        statusClass = ""
      }
      const objectives = safeArray(t?.objective)
      const objectiveHtml = !objectives.length
        ? `<div class="card-sub">暂无目标拆解</div>`
        : objectives
            .map((o) => {
              const sub = o?.sub_objective ?? "—"
              const status = o?.status ?? "—"
              const milestones = safeArray(o?.milestones)

              const milestonesHtml = milestones.length
                ? `<ul class="milestones">${milestones.map((m) => `<li>${escapeHtml(m)}</li>`).join("")}</ul>`
                : `<div class="card-sub"></div>`

              const summary = isBlank(o?.execution_summary)
                ? ""
                : `<div class="card-sub" style="margin-top:8px">总结：${escapeHtml(o.execution_summary)}</div>`

              return `
                <div class="objective">
                  <div class="objective-hd">
                    <div class="objective-title">${escapeHtml(sub)}</div>
                    <div class="objective-status">${escapeHtml(status)}</div>
                  </div>
                  ${milestonesHtml}
                  ${summary}
                </div>
              `
            })
            .join("")

      const html = `
        <div class="task">
          <div class="task-top">
            <div class="task-name">${escapeHtml(name)}</div>
            <div class="badge ${statusClass}">${statusText}</div>
          </div>
          ${objectiveHtml}
        </div>
      `
      list.insertAdjacentHTML("beforeend", html)
    })
  }

  const missionDone = Boolean(planBody?.is_mission_accomplished)

  const chip = $("missionChip")
  if (chip) {
    chip.textContent = missionDone ? "已达成" : "运行中"
    chip.setAttribute("data-state", missionDone ? "done" : "run")
  }
}

function renderAgent(agent) {
  const avatarImg = $("agentAvatarImg")
  const avatarFallback = $("agentAvatarFallback")
  if (avatarImg) {
    if (!avatarImg.dataset.bound) {
      avatarImg.src = AGENT_AVATAR_URL
      avatarImg.addEventListener("load", () => avatarImg.closest(".avatar")?.classList.add("has-img"))
      avatarImg.addEventListener("error", () => avatarImg.closest(".avatar")?.classList.remove("has-img"))
      avatarImg.dataset.bound = "1"
    }
  }

  if (!agent || (typeof agent === "object" && Object.keys(agent).length === 0)) {
    setText("agentName", "—")
    if (avatarFallback) avatarFallback.textContent = "A"
    // setText("agentMood", "情绪：待命")
    setText("agentSetting", "—")
    setText("agentSpec", "—")
    $("execTimeline").innerHTML = `<div class="card-sub">暂无执行轨迹</div>`
    return
  }

  const roleName = agent?.role_name ?? "—"
  const roleSetting = agent?.role_setting ?? "—"
  const spec = agent?.task_specification ?? "—"
  const execInfo = safeArray(agent?.exec_info)

  setText("agentName", isBlank(roleName) ? "—" : roleName)
  setText("agentSetting", isBlank(roleSetting) ? "—" : roleSetting)
  setText("agentSpec", isBlank(spec) ? "—" : spec)

  // if (avatarFallback) avatarFallback.textContent = isBlank(roleName) ? "A" : String(roleName).slice(0, 1)
  // setText("agentMood", execInfo.length ? "情绪：专注" : "情绪：待命")

  const timeline = $("execTimeline")
  timeline.innerHTML = ""

  if (!execInfo.length) {
    timeline.innerHTML = `<div class="card-sub">暂无执行轨迹</div>`
    return
  }

  const reversedExecInfo = [...execInfo].reverse()

  reversedExecInfo.forEach((t, idx) => {
    const isActive = idx === 0 ? "active" : ""
    const html = `
      <div class="tl ${isActive}">
        <div class="dot"></div>
        <div class="text">${escapeHtml(t)}</div>
      </div>
    `
    timeline.insertAdjacentHTML("beforeend", html)
  })
}

function renderMeta(meta) {
  const source = meta?.source ?? "—"
  const generatedAt = meta?.generated_at ?? "—"
  setText("sourceTag", isBlank(source) ? "—" : `来源：${source}`)
  setText("generatedAt", isBlank(generatedAt) || generatedAt === "—" ? "—" : `生成时间：${generatedAt}`)
}

function renderSummary(summary) {
  const el = $("summaryText")
  if (!el) return
  if (isBlank(summary)) {
    el.textContent = "暂无总结"
    return
  }
  el.innerHTML = renderMarkdown(summary)
}

function isEmptyObject(obj) {
  return !obj || (typeof obj === "object" && Object.keys(obj).length === 0)
}

function renderAll(payload) {
  setText("taskId", payload?.task_id ?? "—")
  const chatLen = safeArray(payload?.chat_body).length
  setText("chatSub", ``)
  renderChat(payload?.chat_body)

  const liveSection = $("liveSection")
  const planSection = $("planSection")
  const summarySection = $("summarySection")

  if (isEmptyObject(payload?.current_subagent)) {
    if (liveSection) liveSection.style.display = "none"
  } else {
    if (liveSection) liveSection.style.display = ""
    renderAgent(payload.current_subagent)
  }

  if (isEmptyObject(payload?.plan_body)) {
    if (planSection) planSection.style.display = "none"
  } else {
    if (planSection) planSection.style.display = ""
    renderPlan(payload.plan_body)
  }

  if (isBlank(payload?.summary_body)) {
    if (summarySection) summarySection.style.display = "none"
  } else {
    if (summarySection) summarySection.style.display = ""
    renderSummary(payload.summary_body)
  }

  const meta = payload?.meta
  if (meta) renderMeta(meta)
}

function openDrawer() {
  const d = $("drawer")
  d.classList.add("open")
  d.setAttribute("aria-hidden", "false")
}

function closeDrawer() {
  const d = $("drawer")
  d.classList.remove("open")
  d.setAttribute("aria-hidden", "true")
}

function openInputModal(query) {
  const modal = $("inputModal")
  if (!modal) return
  setText("pendingQuestion", query || "需要你补充输入")
  $("pendingMsg").textContent = ""
  modal.classList.add("open")
  modal.setAttribute("aria-hidden", "false")
  state.pendingOpen = true
}

function closeInputModal() {
  const modal = $("inputModal")
  if (!modal) return
  modal.classList.remove("open")
  modal.setAttribute("aria-hidden", "true")
  state.pendingOpen = false
}

function setTaskId(taskId) {
  state.taskId = taskId || null
  if (state.taskId) {
    window.location.hash = `#${state.taskId}`
  } else {
    history.replaceState(null, "", window.location.pathname + window.location.search)
  }
  setText("taskIdPill", `任务：${state.taskId || "—"}`)
  const submitSection = $("submitSection")
  const statusPage = $("statusPage")
  if (submitSection) submitSection.classList.toggle("hidden", Boolean(state.taskId))
  if (statusPage) statusPage.classList.toggle("hidden", !state.taskId)
  if (!state.taskId) {
    state.pollingPaused = false
    if (state.refreshTimer) clearTimeout(state.refreshTimer)
  }
}

function getInitialTaskId() {
  const hash = window.location.hash ? window.location.hash.replace("#", "") : ""
  return hash || ""
}

function statusTextFor(statePayload, statusPayload) {
  if (statusPayload?.waiting_for_input) return "等待输入"
  if (statePayload?.is_running) return "运行中"
  if (statePayload?.is_completed) return "已完成"
  return "在线"
}

async function submitTask(query) {
  const msg = $("taskFormMsg")
  const submitBtn = $("taskSubmitBtn")
  if (msg) msg.textContent = ""
  if (submitBtn) submitBtn.disabled = true
  try {
    const res = await fetch(`${API_BASE}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const payload = await res.json()
    if (!payload?.task_id) throw new Error("未返回 task_id")
    setTaskId(payload.task_id)
    await load()
  } catch (e) {
    if (msg) msg.textContent = `提交失败：${e?.message || e}`
  } finally {
    if (submitBtn) submitBtn.disabled = false
  }
}

async function submitPendingInput() {
  const input = $("pendingInput")
  const msg = $("pendingMsg")
  const submitBtn = $("inputSubmitBtn")
  if (!input) return
  const value = String(input.value || "").trim()
  if (msg) msg.textContent = ""
  if (!value) {
    if (msg) msg.textContent = "请输入回复内容"
    return
  }
  if (submitBtn) submitBtn.disabled = true
  try {
    const res = await fetch(`${API_BASE}/tasks/${state.taskId}/input`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ response: value }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    input.value = ""
    closeInputModal()
    state.pollingPaused = false
    await load(true)
    startAutoRefresh()
  } catch (e) {
    if (msg) msg.textContent = `提交失败：${e?.message || e}`
  } finally {
    if (submitBtn) submitBtn.disabled = false
  }
}

async function load(force = false) {
  if (!state.taskId) {
    setStatus(null, "等待提交任务")
    return
  }
  if (state.pollingPaused && !force) return
  setStatus(null, "连接中")
  setText("hint", "智能体正在思考下一步…")
  setText("liveHint", "智能体正在思考下一步…")

  try {
    const stateRes = await fetch(`${API_BASE}/tasks/${state.taskId}/state`, { cache: "no-store" })
    if (!stateRes.ok) throw new Error(`HTTP ${stateRes.status}`)
    const payload = await stateRes.json()
    const statePayload = payload?.state ?? payload
    state.data = statePayload
    state.lastOkAt = Date.now()

    $("rawJson").textContent = JSON.stringify(payload, null, 2)
    renderAll(statePayload)
    let statusPayload = null
    try {
      const statusRes = await fetch(`${API_BASE}/tasks/${state.taskId}/status`, { cache: "no-store" })
      if (statusRes.ok) statusPayload = await statusRes.json()
    } catch (e) {
      statusPayload = null
    }
    if (statusPayload?.waiting_for_input) {
      const pendingQuery = statusPayload?.pending_query || "需要你补充输入"
      if (!state.pendingOpen || state.pendingQuery !== pendingQuery) {
        state.pendingQuery = pendingQuery
        openInputModal(pendingQuery)
      }
      state.pollingPaused = true
      if (state.refreshTimer) clearTimeout(state.refreshTimer)
    } else if (state.pendingOpen) {
      closeInputModal()
      state.pendingQuery = null
      if (state.pollingPaused) {
        state.pollingPaused = false
        startAutoRefresh()
      }
    }
    setStatus("online", statusTextFor(payload, statusPayload))
    // setText("hint", "轻点“原始数据”，查看完整上下文")
    // setText("liveHint", "实时同步中：执行轨迹会持续更新")
  } catch (e) {
    setStatus("offline", "离线")
    // setText("hint", "请确认后端已启动，并且接口可访问")
    // setText("liveHint", "离线：等待恢复连接后自动继续")
    $("chatList").innerHTML = `<div class="card-sub">加载失败：${escapeHtml(e?.message || e)}</div>`
  }
}

function initClock() {
  $("clock").textContent = nowClock()
  setInterval(() => {
    $("clock").textContent = nowClock()
  }, 1000)
}

function bindUI() {
  $("refreshBtn").addEventListener("click", load)
  const refreshBtn2 = $("refreshBtn2")
  if (refreshBtn2) refreshBtn2.addEventListener("click", load)
  $("jsonBtn").addEventListener("click", openDrawer)
  $("closeDrawer").addEventListener("click", closeDrawer)
  $("drawerBackdrop").addEventListener("click", closeDrawer)
  $("newTaskBtn").addEventListener("click", () => {
    setTaskId(null)
  })
  $("taskForm").addEventListener("submit", (e) => {
    e.preventDefault()
    const input = $("taskQuery")
    const query = String(input?.value || "").trim()
    if (!query) {
      $("taskFormMsg").textContent = "请输入任务描述"
      return
    }
    submitTask(query)
  })
  $("inputSubmitBtn").addEventListener("click", submitPendingInput)
  $("inputCancelBtn").addEventListener("click", closeInputModal)
  $("inputBackdrop").addEventListener("click", closeInputModal)
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeDrawer()
      closeInputModal()
    }
  })
}

function startAutoRefresh() {
  if (state.refreshTimer) clearTimeout(state.refreshTimer)
  const loop = async () => {
    await load()
    if (!state.pollingPaused) {
      state.refreshTimer = setTimeout(loop, REFRESH_MS)
    }
  }
  if (!state.pollingPaused) {
    state.refreshTimer = setTimeout(loop, REFRESH_MS)
  }
}

function boot() {
  initClock()
  bindUI()
  setTaskId(getInitialTaskId())
  load()
  startAutoRefresh()
}

boot()
