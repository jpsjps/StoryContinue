const apiBase = "/api";
window.multiChapterState = {
  isActive: false,
  stopRequested: false,
  totalChapters: 1,
  currentStep: 0,
  selectedTones: ["smooth"],
  confirmEachChapter: true,
};

function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function fetchProjects() {
  const res = await fetch(`${apiBase}/projects`);
  const data = await res.json();
  const listEl = document.getElementById("project-list");
  listEl.innerHTML = "";
  data.forEach((p) => {
    const li = document.createElement("li");
    li.className = "project-list-item";
    li.innerHTML = `
      <div class="project-list-item-main">
        ${escapeHTML(p.title)} <span class="muted">(${p.chapter_count} 章)</span>
      </div>
      <button class="project-delete-btn danger small" type="button" aria-label="删除项目">
        删除
      </button>
    `;
    li.onclick = () => loadProject(p.id);

    const deleteBtn = li.querySelector(".project-delete-btn");
    if (deleteBtn) {
      deleteBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await deleteProjectById(p.id);
      });
    }
    listEl.appendChild(li);
  });
}

async function deleteProjectById(projectId) {
  // 为了拿到标题，先拉一次详情（最轻量，且不依赖列表项是否存在）
  let title = "";
  try {
    const r = await fetch(`${apiBase}/projects/${projectId}`);
    if (r.ok) {
      const p = await r.json();
      title = p.title || "";
    }
  } catch (_) {
    // ignore
  }

  const ok = confirm(`确定删除「${title || "该项目"}」吗？此操作不可恢复。`);
  if (!ok) return;

  try {
    const res = await fetch(`${apiBase}/projects/${projectId}`, { method: "DELETE" });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      alert(`删除失败：${txt || res.statusText}`);
      return;
    }

    // 如果刚删除的是当前项目，清空右侧
    if (window.currentProjectId === projectId) {
      window.currentProjectId = null;
      window.currentProjectChapters = [];
      resetProjectDetail();
    }

    await fetchProjects();
  } catch (e) {
    console.error(e);
    alert("删除失败：网络错误或后端异常，请重试。");
  }
}

async function loadProject(id) {
  const res = await fetch(`${apiBase}/projects/${id}`);
  const project = await res.json();
  window.currentProjectId = project.id;
  window.currentProjectChapters = project.chapters || [];
  window.currentProjectOriginalText = project.original_text || "";
  window.currentProjectTitle = project.title || "";

  const detail = document.getElementById("project-detail");
  const chaptersHtml = project.chapters
    .map(
      (c) =>
        (() => {
          const raw = c.content || "";
          const preview = raw.replace(/\s+/g, " ").trim().slice(0, 90);
          const typeLabel = c.type === "ending" ? "结局" : "正文";
          return `<li class="chapter-item" data-chapter-id="${c.id}" data-chapter-index="${c.index}">
            <div class="chapter-item-row">
              <span>第 ${c.index} 章</span>
              <span class="chip chip-${c.type}">${typeLabel}</span>
              <span class="chip">${c.style_id}</span>
              <span class="chip chip-model">${c.model}</span>
            </div>
            <div class="chapter-preview">${escapeHTML(preview || "（无内容）")}</div>
            <div class="chapter-actions-row">
              <button class="chapter-action-btn ghost small chapter-action-rewrite" data-action="rewrite" type="button">重写</button>
              <button class="chapter-action-btn ghost small chapter-action-delete danger" data-action="delete" type="button">删除</button>
            </div>
          </li>`;
        })()
    )
    .join("");

  const originalSafe = project.original_text
    ? escapeHTML(project.original_text)
    : "（尚未填写原文，可点击下方按钮粘贴或上传 TXT）";

  detail.innerHTML = `
    <div class="project-header">
      <div>
        <h2>${escapeHTML(project.title)}</h2>
        <p class="project-meta">共 ${project.chapters.length} 章 · 最近更新：${
          project.updated_at.split("T")[0]
        }</p>
      </div>
    </div>

    <section class="card-section">
      <div class="section-header">
        <h3>原文</h3>
        <div class="original-actions">
          <button id="edit-original-btn" class="ghost small">
            粘贴 / 编辑原文
          </button>
          <label class="file-upload small">
            上传 TXT
            <input type="file" id="upload-original-file" accept=".txt" hidden />
          </label>
        </div>
      </div>
      <pre class="original-text">${originalSafe}</pre>
      <div id="original-editor" class="original-editor hidden">
        <textarea id="original-textarea" rows="10">${escapeHTML(
          project.original_text || ""
        )}</textarea>
        <div class="original-editor-actions">
          <button id="save-original-btn" class="primary small">保存原文</button>
          <button id="cancel-original-btn" class="ghost small">取消</button>
        </div>
      </div>
    </section>

    <section class="card-section">
      <h3>已续写章节</h3>
      <ul class="chapter-list">
        ${chaptersHtml || "<li class='muted'>暂无章节，先完成第一章续写吧。</li>"}
      </ul>
    </section>

    <section class="card-section">
      <div class="section-header">
        <h3>章节内容</h3>
        <button id="jump-latest-btn" class="ghost small">查看最新</button>
      </div>
      <div id="chapter-content-meta" class="chapter-content-meta"></div>
      <pre id="chapter-content" class="chapter-content-pre"></pre>
    </section>

    <section class="card-section">
      <div class="section-header">
        <h3>下载</h3>
      </div>
      <div class="download-actions">
        <label class="download-label">
          <span>打包方式</span>
          <select id="download-pack-select">
            <option value="single">打包成一个txt</option>
            <option value="per-chapter">每个章节一个txt</option>
          </select>
        </label>
        <button id="download-btn" class="primary small">一键下载</button>
      </div>
      <p class="hint">将把原文与已续写章节保存为 .txt 文件。</p>
    </section>
  `;

  attachProjectDetailHandlers(project);
  renderChapterContentById(
    (project.chapters && project.chapters.length > 0 && project.chapters[project.chapters.length - 1].id) || ""
  );
}

async function updateOriginalText(projectId, text) {
  await fetch(`${apiBase}/projects/${projectId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ original_text: text }),
  });
}

function attachProjectDetailHandlers(project) {
  const editBtn = document.getElementById("edit-original-btn");
  const uploadInput = document.getElementById("upload-original-file");
  const editor = document.getElementById("original-editor");
  const textarea = document.getElementById("original-textarea");
  const saveBtn = document.getElementById("save-original-btn");
  const cancelBtn = document.getElementById("cancel-original-btn");

  if (editBtn) {
    editBtn.addEventListener("click", () => {
      editor.classList.remove("hidden");
      textarea.focus();
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      editor.classList.add("hidden");
      textarea.value = project.original_text || "";
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const text = textarea.value || "";
      await updateOriginalText(project.id, text);
      editor.classList.add("hidden");
      await loadProject(project.id);
    });
  }

  if (uploadInput) {
    uploadInput.addEventListener("change", () => {
      const file = uploadInput.files && uploadInput.files[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".txt")) {
        alert("目前仅支持上传 .txt 文本文件。");
        uploadInput.value = "";
        return;
      }
      const reader = new FileReader();
      reader.onload = async (e) => {
        const text = e.target.result || "";
        await updateOriginalText(project.id, text);
        uploadInput.value = "";
        await loadProject(project.id);
      };
      reader.readAsText(file, "utf-8");
    });
  }

  // 如果当前项目还没有原文，默认直接展开编辑区域，方便用户粘贴文字
  if (editor && textarea && !project.original_text) {
    editor.classList.remove("hidden");
    textarea.focus();
  }

  // 章节点击查看内容（历史章节可回看）
  const items = document.querySelectorAll(".chapter-item");
  items.forEach((el) => {
    el.addEventListener("click", () => {
      const chapterId = el.getAttribute("data-chapter-id") || "";
      renderChapterContentById(chapterId);
    });
  });

  // 删除/重写章节
  const rewriteBtns = document.querySelectorAll(".chapter-action-rewrite");
  rewriteBtns.forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const li = btn.closest(".chapter-item");
      const fromIndex = li ? parseInt(li.getAttribute("data-chapter-index") || "0") : 0;
      if (!fromIndex) return;
      const total = (window.currentProjectChapters || []).length;
      const hasLater = fromIndex < total; // 后面还有章节
      let msg = `将从第 ${fromIndex} 章开始删除并重写该章`;
      if (hasLater) msg += `（后续章节也会一起删除）`;
      msg += `。是否继续？`;

      const ok = confirm(msg);
      if (!ok) return;

      const currentNote = document.getElementById("user-note")?.value || "";
      const note = prompt(`为“第 ${fromIndex} 章”重写填写关键说明（可留空）`, currentNote);
      const finalNote = (note || "").trim();
      const userNoteEl = document.getElementById("user-note");
      if (userNoteEl) userNoteEl.value = finalNote;

      await truncateChaptersFromIndex(project.id, fromIndex);
      // 截断后，调用现有续写接口生成“第 fromIndex 章”
      startStream();
    });
  });

  const deleteBtns = document.querySelectorAll(".chapter-action-delete");
  deleteBtns.forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const li = btn.closest(".chapter-item");
      const fromIndex = li ? parseInt(li.getAttribute("data-chapter-index") || "0") : 0;
      if (!fromIndex) return;
      const total = (window.currentProjectChapters || []).length;
      const hasLater = fromIndex < total;
      let msg = `确定删除“第 ${fromIndex} 章”及其后续章节吗？`;
      if (!hasLater) msg = `确定删除“第 ${fromIndex} 章”吗？`;
      const ok = confirm(msg);
      if (!ok) return;

      await truncateChaptersFromIndex(project.id, fromIndex);
      // 直接刷新当前项目
      await loadProject(project.id);
    });
  });

  const jumpLatestBtn = document.getElementById("jump-latest-btn");
  if (jumpLatestBtn) {
    jumpLatestBtn.addEventListener("click", () => {
      const chapters = window.currentProjectChapters || [];
      const latest = chapters[chapters.length - 1];
      renderChapterContentById(latest ? latest.id : "");
    });
  }

  // 下载：一键导出为 txt
  const downloadBtn = document.getElementById("download-btn");
  const downloadPackSelect = document.getElementById("download-pack-select");
  if (downloadBtn && downloadPackSelect) {
    downloadBtn.addEventListener("click", () => {
      const packMode = downloadPackSelect.value || "single";
      downloadProjectAsTxt(packMode);
    });
  }
}

async function truncateChaptersFromIndex(projectId, fromIndex) {
  try {
    const res = await fetch(`${apiBase}/projects/${projectId}/chapters/truncate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_index: fromIndex }),
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      alert(`操作失败：${txt || res.statusText}`);
    }
  } catch (e) {
    console.error(e);
    alert("操作失败：网络错误或后端异常，请重试。");
  }
}

function resetProjectDetail() {
  const detail = document.getElementById("project-detail");
  if (detail) {
    detail.innerHTML = `
      <div class="empty-state">
        <h2>欢迎使用 StoryContinue</h2>
        <p>在左侧创建或选择一个项目，右侧即可配置风格并开始 AI 续写。</p>
      </div>
    `;
  }
  const output = document.getElementById("output");
  if (output) output.textContent = "";
  const statusEl = document.getElementById("stream-status");
  if (statusEl) statusEl.textContent = "";
  const chapterContentPre = document.getElementById("chapter-content");
  if (chapterContentPre) chapterContentPre.textContent = "";
}

function sanitizeFilename(str) {
  return String(str || "")
    .trim()
    .replace(/[\\/:*?"<>|]/g, "_")
    .slice(0, 60);
}

function downloadTextFile(filename, content) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function getCurrentProjectSnapshot() {
  return {
    title: window.currentProjectTitle || "",
    original_text: window.currentProjectOriginalText || "",
    chapters: window.currentProjectChapters || [],
  };
}

function buildSingleTxt(snapshot) {
  const title = snapshot.title || "未命名项目";
  const parts = [];
  parts.push(`《${title}》`);
  parts.push("");
  parts.push("===== 原文 =====");
  parts.push(snapshot.original_text || "");
  parts.push("");

  if (!snapshot.chapters || snapshot.chapters.length === 0) {
    parts.push("（暂无已续写章节）");
    return parts.join("\n");
  }

  for (const c of snapshot.chapters) {
    const typeLabel = c.type === "ending" ? "结局" : "正文";
    parts.push(`===== 第 ${c.index} 章（${typeLabel}）=====`);
    parts.push((c.content || "").trimEnd());
    parts.push("");
  }

  return parts.join("\n");
}

function buildPerChapterTxt(snapshot) {
  const files = [];
  const title = snapshot.title || "未命名项目";
  const safeTitle = sanitizeFilename(title);

  // 原文单独保存
  files.push({
    filename: `${safeTitle}_原文.txt`,
    content: snapshot.original_text || "",
  });

  if (!snapshot.chapters) return files;
  for (const c of snapshot.chapters) {
    const typeLabel = c.type === "ending" ? "结局" : "正文";
    const styleTag = c.style_id ? `_${c.style_id}` : "";
    files.push({
      filename: `${safeTitle}_第${c.index}章_${typeLabel}${styleTag}.txt`,
      content: (c.content || "").trimEnd(),
    });
  }

  return files;
}

function downloadProjectAsTxt(packMode) {
  const snapshot = getCurrentProjectSnapshot();
  if (!snapshot.title) {
    alert("请先选择/创建一个项目再下载。");
    return;
  }

  if (packMode === "per-chapter") {
    const files = buildPerChapterTxt(snapshot);
    if (files.length <= 1) {
      alert("当前项目没有可下载的章节内容。");
      return;
    }
    if (!confirm(`将下载 ${files.length} 个 .txt 文件（可能触发浏览器下载多个文件）。确定继续？`)) {
      return;
    }
    for (const f of files) {
      downloadTextFile(f.filename, f.content || "");
    }
    return;
  }

  const content = buildSingleTxt(snapshot);
  const safeTitle = sanitizeFilename(snapshot.title || "未命名项目");
  downloadTextFile(`${safeTitle}_全部.txt`, content);
}

function renderChapterContentById(chapterId) {
  const chapterContentPre = document.getElementById("chapter-content");
  const metaEl = document.getElementById("chapter-content-meta");
  if (!chapterContentPre) return;

  const chapters = window.currentProjectChapters || [];
  const chapter = chapters.find((c) => c.id === chapterId) || null;

  // active 状态
  document.querySelectorAll(".chapter-item").forEach((el) => {
    el.classList.remove("active");
  });
  if (chapterId) {
    const activeEl = document.querySelector(
      `.chapter-item[data-chapter-id="${chapterId}"]`
    );
    if (activeEl) activeEl.classList.add("active");
  }

  if (!chapter) {
    metaEl && (metaEl.textContent = "");
    chapterContentPre.textContent = "";
    return;
  }

  metaEl &&
    (metaEl.textContent = `第 ${chapter.index} 章 · ${chapter.type === "ending" ? "结局" : "正文"} · 风格：${chapter.style_id} · 模型：${chapter.model}`);
  chapterContentPre.textContent = chapter.content || "";
}

async function createProjectWithTitle() {
  const input = document.getElementById("new-project-title");
  const title = input.value.trim();
  if (!title) {
    alert("请输入项目名称");
    return;
  }
  const res = await fetch(`${apiBase}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, original_text: "" }),
  });
  const project = await res.json();
  input.value = "";
  toggleNewProjectForm(false);
  await fetchProjects();
  await loadProject(project.id);
}

function toggleNewProjectForm(show) {
  const form = document.getElementById("new-project-form");
  if (!form) return;
  if (show) {
    form.classList.remove("hidden");
    const input = document.getElementById("new-project-title");
    if (input) input.focus();
  } else {
    form.classList.add("hidden");
  }
}

function getSelectedTones() {
  const checkboxes = document.querySelectorAll('input[name="tone"]:checked');
  return Array.from(checkboxes).map((cb) => cb.value);
}

function updateEndingOptionsVisibility() {
  const modeSelect = document.getElementById("mode-select");
  const endingOptions = document.getElementById("ending-options");
  const toneOptions = document.getElementById("tone-options");
  if (!modeSelect || !endingOptions || !toneOptions) return;
  const isEndingMode = modeSelect.value === "ending";
  endingOptions.classList.toggle("hidden", !isEndingMode);
  toneOptions.classList.toggle("hidden", !isEndingMode);
}

function buildSingleChapterParams({
  projectId,
  styleId,
  mode,
  useLongMemory,
  userNote,
  chapterIndex,
  totalChapters,
  tone,
  isFinalChapter,
}) {
  const requestId =
    (typeof crypto !== "undefined" && crypto.randomUUID && crypto.randomUUID()) ||
    `req_${Date.now()}_${Math.random().toString(16).slice(2)}`;

  const params = new URLSearchParams({
    project_id: projectId,
    style_id: styleId,
    mode,
    use_long_memory: String(useLongMemory),
    request_id: requestId,
  });
  if (userNote) params.append("user_note", userNote);
  if (chapterIndex) params.append("chapter_index", String(chapterIndex));
  if (totalChapters) params.append("total_chapters", String(totalChapters));
  if (tone) params.append("tone", tone);
  if (isFinalChapter) params.append("is_final_chapter", "true");

  return { params, requestId };
}

function runSingleStream({ params, requestId, projectId, progressLabel = "" }) {
  return new Promise((resolve) => {
    const output = document.getElementById("output");
    const startBtn = document.getElementById("start-write-btn");
    const panel = document.querySelector(".stream-output");
    const statusEl = document.getElementById("stream-status");
    const stopBtn = document.getElementById("stop-write-btn");

    if (startBtn) {
      startBtn.disabled = true;
      startBtn.textContent = progressLabel ? `续写中（${progressLabel}）…` : "续写中…";
    }
    if (stopBtn) stopBtn.disabled = false;
    if (panel) panel.classList.add("streaming");

    const es = new EventSource(`${apiBase}/stream/write?${params.toString()}`);
    window._activeSse = { es, requestId };

    es.addEventListener("chunk", (event) => {
      output.textContent += event.data;
    });

    const finish = async (opts = { ok: true, isError: false, message: "" }) => {
      es.close();
      if (startBtn) {
        startBtn.disabled = false;
        startBtn.textContent = "开始续写";
      }
      if (stopBtn) stopBtn.disabled = true;
      if (panel) panel.classList.remove("streaming");

      if (statusEl) {
        if (opts.isError) {
          statusEl.textContent = opts.message || "续写失败，请检查网络或配置。";
          statusEl.classList.add("error");
        } else if (opts.message) {
          statusEl.textContent = opts.message;
          statusEl.classList.remove("error");
        } else {
          statusEl.textContent = "";
          statusEl.classList.remove("error");
        }
      }
      if (opts.ok && !opts.isError) {
        await fetchProjects();
        await loadProject(projectId);
      }
      resolve(opts.ok && !opts.isError);
    };

    es.addEventListener("end", () => finish({ ok: true, isError: false, message: "" }));

    es.addEventListener("cancelled", (event) => {
      const raw = event && event.data ? String(event.data) : "";
      finish({
        ok: false,
        isError: true,
        message: raw || "已停止续写。",
      });
    });

    es.addEventListener("app_error", (event) => {
      const raw = event && event.data ? String(event.data) : "";
      let parsed = null;
      try {
        parsed = raw ? JSON.parse(raw) : null;
      } catch (_) {
        parsed = null;
      }
      const msg = (parsed && (parsed.message || parsed.repr || parsed.body)) || raw;
      if (raw) output.textContent = raw;
      finish({
        ok: false,
        isError: true,
        message: msg || "续写失败：可能是网络问题、API Key 无效或配额耗尽。",
      });
    });

    es.addEventListener("error", (event) => {
      let msg = "";
      if (event && event.data) msg = String(event.data);
      finish({
        ok: false,
        isError: true,
        message: msg || "续写过程中发生错误，请稍后重试。",
      });
    });
  });
}

function startStream() {
  const projectId = window.currentProjectId;
  if (!projectId) {
    alert("请先选择或创建一个项目");
    return;
  }
  // 关闭上一次请求（如果还在跑）
  if (window._activeSse && window._activeSse.es) {
    try {
      window._activeSse.es.close();
    } catch (_) {
      // ignore
    }
  }

  const styleId = document.getElementById("style-select").value;
  const mode = document.getElementById("mode-select").value;
  const userNote = document.getElementById("user-note").value.trim();
  const longMemorySwitch = document.getElementById("long-memory-switch");
  const useLongMemory = longMemorySwitch
    ? longMemorySwitch.checked
    : true;

  const output = document.getElementById("output");
  output.textContent = "";
  const statusEl = document.getElementById("stream-status");
  if (statusEl) {
    statusEl.textContent = "";
    statusEl.classList.remove("error");
  }

  // 多章节模式：仅在“续写到结局”开启
  if (mode === "ending") {
    const totalInput = document.getElementById("total-chapters-input");
    const confirmInput = document.getElementById("confirm-each-chapter");
    const totalChapters = parseInt((totalInput && totalInput.value) || "1", 10);
    if (!totalChapters || totalChapters < 1 || totalChapters > 50) {
      alert("本次续写章数需在 1-50 之间。");
      return;
    }

    window.multiChapterState.isActive = true;
    window.multiChapterState.stopRequested = false;
    window.multiChapterState.totalChapters = totalChapters;
    window.multiChapterState.currentStep = 0;
    window.multiChapterState.selectedTones = getSelectedTones();
    if (!window.multiChapterState.selectedTones.length) {
      window.multiChapterState.selectedTones = ["smooth"];
    }
    window.multiChapterState.confirmEachChapter = confirmInput ? confirmInput.checked : true;

    const baseChapterIndex = (window.currentProjectChapters || []).length;

    (async () => {
      for (let step = 1; step <= totalChapters; step++) {
        if (window.multiChapterState.stopRequested) break;

        window.multiChapterState.currentStep = step;
        const isFinal = step === totalChapters;
        const chapterIndex = baseChapterIndex + step;
        const tone = window.multiChapterState.selectedTones.join(",");

        if (statusEl) {
          statusEl.textContent = `正在新增第 ${step}/${totalChapters} 章…`;
        }

        const { params, requestId } = buildSingleChapterParams({
          projectId,
          styleId,
          mode: isFinal ? "ending" : "chapter",
          useLongMemory,
          userNote,
          chapterIndex,
          totalChapters,
          tone,
          isFinalChapter: isFinal,
        });

        const ok = await runSingleStream({
          params,
          requestId,
          projectId,
          progressLabel: `${step}/${totalChapters}`,
        });
        if (!ok || window.multiChapterState.stopRequested) break;

        if (window.multiChapterState.confirmEachChapter && !isFinal) {
          // 简化确认：避免复杂弹窗，直接 confirm 即可
          const goOn = confirm(`第 ${step} 章已完成，继续生成下一章吗？`);
          if (!goOn) break;
        }
      }
      window.multiChapterState.isActive = false;
      window.multiChapterState.stopRequested = false;
    })();
    return;
  }

  // 单章模式
  const { params, requestId } = buildSingleChapterParams({
    projectId,
    styleId,
    mode,
    useLongMemory,
    userNote,
  });
  runSingleStream({ params, requestId, projectId });
}

window.addEventListener("DOMContentLoaded", () => {
  const themeSelect = document.getElementById("theme-select");
  if (themeSelect) {
    const themeSwitcher = document.getElementById("theme-switcher");
    const collapseBtn = document.getElementById("theme-collapse-btn");

    const savedCollapsed = window.localStorage.getItem("sc_theme_collapsed");
    const isCollapsed = savedCollapsed === "1";
    if (themeSwitcher && isCollapsed) {
      themeSwitcher.classList.add("collapsed");
    }

    const saved = window.localStorage.getItem("sc_theme");
    const theme = saved === "light" || saved === "dark" ? saved : "dark";
    document.body.classList.toggle("light", theme === "light");
    themeSelect.value = theme;

    if (collapseBtn && themeSwitcher) {
      const sync = () => {
        const nowCollapsed = themeSwitcher.classList.contains("collapsed");
        collapseBtn.textContent = nowCollapsed ? "▸" : "▾";
      };
      sync();

      collapseBtn.addEventListener("click", () => {
        const nowCollapsed = themeSwitcher.classList.contains("collapsed");
        themeSwitcher.classList.toggle("collapsed");
        window.localStorage.setItem("sc_theme_collapsed", nowCollapsed ? "0" : "1");
        sync();
      });
    }

    themeSelect.addEventListener("change", () => {
      const next = themeSelect.value === "light" ? "light" : "dark";
      document.body.classList.toggle("light", next === "light");
      window.localStorage.setItem("sc_theme", next);
    });
  }

  document
    .getElementById("new-project-btn")
    .addEventListener("click", () => toggleNewProjectForm(true));
  document
    .getElementById("confirm-new-project-btn")
    .addEventListener("click", createProjectWithTitle);
  document
    .getElementById("cancel-new-project-btn")
    .addEventListener("click", () => toggleNewProjectForm(false));
  document
    .getElementById("start-write-btn")
    .addEventListener("click", startStream);

  const modeSelect = document.getElementById("mode-select");
  if (modeSelect) {
    updateEndingOptionsVisibility();
    modeSelect.addEventListener("change", updateEndingOptionsVisibility);
  }

  const stopBtn = document.getElementById("stop-write-btn");
  if (stopBtn) {
    stopBtn.addEventListener("click", async () => {
      if (!window._activeSse || !window._activeSse.requestId) return;
      window.multiChapterState.stopRequested = true;
      const requestId = window._activeSse.requestId;
      try {
        // 通知后端停止
        await fetch(`${apiBase}/stream/cancel?request_id=${encodeURIComponent(requestId)}`, {
          method: "POST",
        });
      } catch (e) {
        console.error(e);
      }
      // 立即关闭前端连接
      try {
        window._activeSse.es && window._activeSse.es.close();
      } catch (_) {
        // ignore
      }
      window._activeSse = null;
      const statusEl = document.getElementById("stream-status");
      if (statusEl) {
        statusEl.textContent = "已请求停止续写，正在收尾...";
        statusEl.classList.remove("error");
      }
    });
    stopBtn.disabled = true;
  }
  fetchProjects();
});

