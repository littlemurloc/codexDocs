
"use strict";

const { clips, parts, partOrder, partNames = {} } = window.CHARACTER_VIEWER_DATA || window.ORC_VIEWER_DATA;
let clip;
let atlas;
let frames;
let fps;
let duration;
let beats;
let loadingVersion = 0;
let bodyImage;
let fxImage;
let showFx = true;
let frameWidth = 330;
let frameHeight = 326;
const markerButtons = [];
let atlasCells = [];

const get = (id) => document.getElementById(id);
const labelFrame = (index) => String(index + 1).padStart(2, "0");

const partLabels = {
  hips_legs: "骨盆与双腿",
  torso: "胸带与躯干",
  head: "头部",
  arm_near: "近侧手臂",
  hand_axe_near: "近手与斧",
  arm_far: "远侧手臂",
  hand_axe_far: "远手与斧",
};
const extraPartLabels = {
  leg_near: "近侧腿",
  leg_far: "远侧腿",
  walk_hips: "行走骨盆与腰布",
};
Object.assign(partLabels, extraPartLabels, partNames);
const eventLabels = {
  impact: "伤害结算",
  hurt: "受击",
  ground: "落地",
  step_near: "近脚着地",
  step_far: "远脚着地",
};

const img = get("atlas-image");
const canvas = get("viewport");
const ctx = canvas.getContext("2d");
const atlasCanvas = get("atlas-preview");
const atlasCtx = atlasCanvas.getContext("2d");
const tabs = [...document.querySelectorAll('[role="tab"]')];
let activeTab = "motion";
let playbackFrame = 0;
let inspectedFrame = 0;
let time = 0;
let lastTick = 0;
let animationRequest = 0;
let playing = false;
let loop = true;
let speed = 1;
let showBones = false;
let loaded = false;

function buildMarkers() {
  get("markers").replaceChildren();
  markerButtons.length = 0;
  for (const [frame, title] of beats) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "marker";
    if (atlas.events?.some((event) => event.event === "impact" && event.frame === frame)) {
      button.classList.add("is-impact");
    }
    const name = document.createElement("span");
    name.textContent = title;
    const timestamp = document.createElement("time");
    timestamp.textContent = (frame / fps).toFixed(2) + " s";
    button.append(name, timestamp);
    button.addEventListener("click", () => seek(frame));
    get("markers").append(button);
    markerButtons.push(button);
  }
}

function addRows(root, rows) {
  root.replaceChildren(...rows.map(([key, value]) => {
    const row = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = value;
    row.append(dt, dd);
    return row;
  }));
}

function drawAtlasFrame(context, frame, width, height) {
  context.clearRect(0, 0, width, height);
  if (loaded) {
    context.imageSmoothingQuality = "high";
    context.drawImage(bodyImage, ...frames[frame], 0, 0, width, height);
    if (fxImage && showFx) context.drawImage(fxImage, ...frames[frame], 0, 0, width, height);
  }
}

function drawSkeleton() {
  const scaleX = canvas.width / frameWidth;
  const scaleY = canvas.height / frameHeight;
  const joints = atlas.joint_positions?.[playbackFrame];
  const pivots = new Map(Object.entries(joints || {}).map(([name, [x, y]]) =>
    [name, [x * scaleX, y * scaleY]]));
  ctx.save();
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  function links(color, width) {
    ctx.beginPath();
    for (const [name, point] of pivots) {
      const parent = atlas.joint_parents?.[name] ?? parts[name].parent;
      if (parent && pivots.has(parent)) {
        ctx.moveTo(...pivots.get(parent));
        ctx.lineTo(...point);
      }
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  }
  links("#161b14", 5);
  links("#c5db8cf2", 2.3);
  for (const [x, y] of pivots.values()) {
    ctx.beginPath();
    ctx.arc(x, y, 4.7, 0, 2 * Math.PI);
    ctx.fillStyle = "#e2e9b4";
    ctx.strokeStyle = "#22271b";
    ctx.lineWidth = 2.4;
    ctx.fill();
    ctx.stroke();
  }
  const contacts = atlas.locomotion?.contacts_by_frame?.[playbackFrame];
  for (const foot of Object.values(contacts || {})) {
    if (!foot.planted) continue;
    ctx.beginPath();
    ctx.arc(foot.contact[0] * scaleX, foot.contact[1] * scaleY, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#f4d182";
    ctx.fill();
  }
  const x = atlas.anchor_in_frame[0] * scaleX;
  const y = atlas.anchor_in_frame[1] * scaleY;
  ctx.strokeStyle = "#ebc88c";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x, y-7);
  ctx.lineTo(x+7, y);
  ctx.lineTo(x, y+7);
  ctx.lineTo(x-7, y);
  ctx.closePath();
  ctx.stroke();
  ctx.restore();
}

function renderMotion() {
  if (!clip) return;
  drawAtlasFrame(ctx, playbackFrame, canvas.width, canvas.height);
  if (loaded && showBones) {
    drawSkeleton();
    get("origin-label").textContent = atlas.joint_positions?.[playbackFrame] ?
      (atlas.locomotion ? "黄点标记支撑脚 · 菱形为脚底锚点" : "菱形标记脚底锚点")
      : "当前帧使用重绘姿势 · 菱形为脚底锚点";
  }
}

function paintTransport() {
  const scrubber = get("scrubber");
  scrubber.value = playbackFrame;
  scrubber.style.setProperty("--progress", (100 * playbackFrame / (frames.length - 1)) + "%");
  scrubber.setAttribute("aria-valuetext", "第 " + labelFrame(playbackFrame) + " 帧");
  get("frame-label").textContent = labelFrame(playbackFrame) + " / " + frames.length + " 帧";
  get("timecode").textContent = (playbackFrame / fps).toFixed(2) + " / " + duration.toFixed(2) + " 秒";
  get("previous").disabled = playbackFrame === 0;
  get("next").disabled = playbackFrame === frames.length - 1;
  const currentBeat = beats.findLastIndex(([frame]) => frame <= playbackFrame);
  markerButtons.forEach((button, index) => {
    button.classList.toggle("is-current", index === currentBeat);
    if (index === currentBeat) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
  });
}

function updateFrame(index) {
  if (index === playbackFrame) return;
  playbackFrame = index;
  renderMotion();
  paintTransport();
}

function tick(now) {
  if (!playing) return;
  time += Math.max(0, now - lastTick) * speed / 1000;
  lastTick = now;
  if (time >= duration) {
    if (!loop) {
      time = duration;
      updateFrame(frames.length - 1);
      setPlaying(false);
      return;
    }
    time %= duration;
  }
  updateFrame(Math.min(frames.length - 1, Math.floor(time * fps)));
  animationRequest = requestAnimationFrame(tick);
}

function setPlaying(value) {
  if (value && (!loaded || activeTab !== "motion")) return;
  if (value === playing) return;
  cancelAnimationFrame(animationRequest);
  playing = value;
  const label = value ? "暂停" : "播放";
  get("play").setAttribute("aria-label", label);
  get("play-icon").classList.toggle("is-playing", value);
  if (value) {
    if (time >= duration || (!loop && playbackFrame === frames.length - 1)) {
      time = 0;
      updateFrame(0);
    }
    lastTick = performance.now();
    animationRequest = requestAnimationFrame(tick);
  }
}

function seek(index) {
  setPlaying(false);
  const clamped = Math.max(0, Math.min(frames.length - 1, index));
  time = clamped / fps;
  updateFrame(clamped);
}

function toggle(button) {
  const state = button.getAttribute("aria-pressed") !== "true";
  button.setAttribute("aria-pressed", String(state));
  return state;
}

function switchTab(name, focus = false) {
  if (name === activeTab && !focus) return;
  if (name !== "motion") setPlaying(false);
  activeTab = name;
  get("clip-bar").hidden = name !== "motion" && name !== "atlas";
  for (const tab of tabs) {
    const id = tab.getAttribute("aria-controls");
    const selected = id === activeTab;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
    get(id).hidden = !selected;
    if (selected && focus) tab.focus();
  }
  if (name === "motion") renderMotion();
  if (name === "atlas") selectAtlasFrame(playbackFrame);
}

tabs.forEach((button, index) => {
  button.addEventListener("click", () => switchTab(button.getAttribute("aria-controls")));
  button.addEventListener("keydown", (event) => {
    const delta = { ArrowLeft: -1, ArrowRight: 1 }[event.key];
    let destination;
    if (delta) destination = (index + delta + tabs.length) % tabs.length;
    else if (event.key === "Home") destination = 0;
    else if (event.key === "End") destination = tabs.length - 1;
    else return;
    event.preventDefault();
    switchTab(tabs[destination].getAttribute("aria-controls"), true);
  });
});

get("play").addEventListener("click", () => setPlaying(!playing));
get("previous").addEventListener("click", () => seek(playbackFrame - 1));
get("next").addEventListener("click", () => seek(playbackFrame + 1));
get("scrubber").addEventListener("input", (event) => seek(Number(event.target.value)));
get("speed").addEventListener("change", (event) => speed = Number(event.target.value));
get("loop").addEventListener("click", (event) => loop = toggle(event.currentTarget));
get("fx").addEventListener("click", (event) => {
  showFx = toggle(event.currentTarget);
  renderMotion();
  selectAtlasFrame(inspectedFrame);
});
get("bones").addEventListener("click", (event) => {
  showBones = toggle(event.currentTarget);
  get("origin-label").hidden = !showBones;
  renderMotion();
});
get("background").addEventListener("click", (event) => {
  get("stage").classList.toggle("checker", toggle(event.currentTarget));
});
document.addEventListener("keydown", (event) => {
  if (activeTab !== "motion" || event.defaultPrevented || event.ctrlKey || event.altKey || event.metaKey) return;
  const control = event.target.closest?.("button, input, select, a, [contenteditable]");
  if (control && (!control.matches(".transport-button") || event.code === "Space")) return;
  if (event.code === "Space") setPlaying(!playing);
  else if (event.key === "ArrowLeft") seek(playbackFrame - 1);
  else if (event.key === "ArrowRight") seek(playbackFrame + 1);
  else return;
  event.preventDefault();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) setPlaying(false);
});

const partButtons = new Map();
function selectPart(name) {
  const part = parts[name];
  get("part-name").textContent = partLabels[name];
  get("part-download").href = part.path;
  get("part-preview").src = part.path;
  get("part-preview").alt = partLabels[name];
  addRows(get("part-meta"), [
    ["文件", part.path.split("/").at(-1)],
    ["尺寸", part.size.join(" × ") + " px"],
    ["父级", part.parent ? partLabels[part.parent] : "根部件"],
    ["旋转轴", "(" + part.pivot.join(", ") + ")"],
    ["绘制顺序", String(partOrder.indexOf(name) + 1)],
  ]);
  for (const [key, button] of partButtons) {
    button.setAttribute("aria-pressed", String(key === name));
  }
}

for (const name of partOrder) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "part-tile";
  const art = document.createElement("img");
  art.src = parts[name].path;
  art.alt = "";
  const label = document.createElement("span");
  label.textContent = partLabels[name];
  button.append(art, label);
  button.addEventListener("click", () => selectPart(name));
  partButtons.set(name, button);
  get("part-grid").append(button);
}
selectPart("head");

function buildAtlas() {
  const atlasColumns = frames.filter(([, y]) => y === frames[0][1]).length;
  const [atlasWidth, atlasHeight] = atlas.image_size;
  get("atlas-frames").replaceChildren();
  get("atlas-select").replaceChildren();
  atlasCells = frames.map(([x, y, width, height], index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "atlas-cell";
    const label = "第 " + labelFrame(index) + " 帧";
    button.title = label;
    button.setAttribute("aria-label", label);
    button.style.left = 100 * x / atlasWidth + "%";
    button.style.top = 100 * y / atlasHeight + "%";
    button.style.width = 100 * width / atlasWidth + "%";
    button.style.height = 100 * height / atlasHeight + "%";
    button.addEventListener("click", () => selectAtlasFrame(index));
    button.addEventListener("keydown", (event) => {
      const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -atlasColumns, ArrowDown: atlasColumns }[event.key];
      if (!delta) return;
      event.preventDefault();
      const next = Math.max(0, Math.min(frames.length - 1, index + delta));
      selectAtlasFrame(next);
      atlasCells[next].focus();
    });
    get("atlas-frames").append(button);
    const option = document.createElement("option");
    option.textContent = label;
    option.value = index;
    get("atlas-select").append(option);
    return button;
  });
}

function selectAtlasFrame(index) {
  inspectedFrame = index;
  atlasCells.forEach((button, i) => {
    button.setAttribute("aria-pressed", String(i === index));
    button.tabIndex = i === index ? 0 : -1;
  });
  get("atlas-title").textContent = "第 " + labelFrame(index) + " 帧";
  get("atlas-select").value = index;
  drawAtlasFrame(atlasCtx, index, atlasCanvas.width, atlasCanvas.height);
  const [x, y, w, h] = frames[index];
  const events = (atlas.events || []).filter((event) => event.frame === index);
  addRows(get("atlas-meta"), [
    ["时间", (index / fps).toFixed(2) + " 秒"],
    ["图集区域", "(" + x + ", " + y + ")"],
    ["帧尺寸", w + " × " + h + " px"],
    ["脚底锚点", "(" + atlas.anchor_in_frame.join(", ") + ")"],
    ...events.flatMap(({event, position_in_frame}) => [
      ["事件", eventLabels[event] || event],
      ...(position_in_frame ? [["命中点", "(" + position_in_frame.join(", ") + ")"]] : []),
    ]),
  ]);
}

get("atlas-select").addEventListener("change", (event) => selectAtlasFrame(Number(event.target.value)));
get("grid-toggle").addEventListener("click", (event) => {
  get("atlas-frames").classList.toggle("no-grid", !toggle(event.currentTarget));
});
get("open-frame").addEventListener("click", () => {
  seek(inspectedFrame);
  switchTab("motion", true);
});

const wrap = document.querySelector(".canvas-wrap");
function fitCanvas(width = wrap.clientWidth, height = wrap.clientHeight) {
  if (width && height) {
    wrap.style.setProperty("--frame-display-width", Math.min(width, height * frameWidth / frameHeight) + "px");
  }
}
new ResizeObserver(([entry]) => {
  fitCanvas(entry.contentRect.width, entry.contentRect.height);
}).observe(wrap);

function loadImage(source) {
  if (!source) return Promise.resolve(null);
  return new Promise((resolve, reject) => {
    const result = new Image();
    result.addEventListener("load", () => resolve(result), { once: true });
    result.addEventListener("error", () => reject(new Error(source)), { once: true });
    result.src = source;
  });
}

function setDownload(id, path) {
  const link = get(id);
  link.hidden = !path;
  if (path) link.href = path;
  else link.removeAttribute("href");
}

async function selectClip(id, autoPlay, previous = false, phase = 0) {
  const entry = clips.find((item) => item.id === id);
  const next = previous && entry?.previous ? entry.previous : entry;
  const showingPrevious = next === entry?.previous;
  if (!next || next === clip) return;
  const version = ++loadingVersion;
  setPlaying(false);
  loaded = false;
  bodyImage = null;
  fxImage = null;
  clip = next;
  atlas = clip.atlas;
  beats = clip.marks;
  frames = atlas.frames_xywh;
  fps = atlas.fps;
  duration = frames.length / fps;
  loop = atlas.loop;
  playbackFrame = Math.min(frames.length - 1, Math.floor(phase * frames.length));
  inspectedFrame = playbackFrame;
  time = playbackFrame / fps;
  frameWidth = frames[0][2];
  frameHeight = frames[0][3];
  canvas.width = frameWidth * 2;
  canvas.height = frameHeight * 2;
  atlasCanvas.width = frameWidth;
  atlasCanvas.height = frameHeight;
  get("clip-select").value = clip.id;
  const revision = get("motion-revision");
  if (revision) {
    revision.hidden = !entry.previous;
    revision.setAttribute("aria-pressed", String(showingPrevious));
    revision.textContent = showingPrevious ? "看新版" : "看旧版";
  }
  get("clip-category").textContent = clip.category + (entry.previous ? (showingPrevious ? " · 旧版" : " · 新版") : "");
  get("clip-title").textContent = clip.name;
  get("clip-id").textContent = clip.id;
  get("stage-clip").textContent = clip.name;
  canvas.setAttribute("aria-label", clip.name + "动画");
  get("scrubber").max = frames.length - 1;
  get("loop").setAttribute("aria-pressed", String(loop));
  get("fx").hidden = !atlas.fx_texture;
  get("stat-duration").firstChild.textContent = duration.toFixed(2) + " ";
  get("stat-fps").firstChild.textContent = fps + " ";
  get("stat-frames").textContent = frames.length;
  get("play").disabled = true;
  get("media-error").hidden = true;
  get("clip-poster").src = clip.thumbnail;
  get("clip-poster").hidden = false;
  img.src = atlas.texture;
  img.width = atlas.image_size[0];
  img.height = atlas.image_size[1];
  img.alt = clip.name + "的透明帧图集";
  setDownload("clip-webp", clip.webp);
  setDownload("clip-motion", clip.motionPath);
  setDownload("atlas-png", atlas.texture);
  setDownload("atlas-json", clip.atlasPath);
  setDownload("atlas-fx", atlas.fx_texture);
  buildMarkers();
  buildAtlas();
  fitCanvas();
  paintTransport();
  renderMotion();
  selectAtlasFrame(inspectedFrame);
  try {
    const [image, effect] = await Promise.all([loadImage(atlas.texture), loadImage(atlas.fx_texture)]);
    if (version !== loadingVersion) return;
    bodyImage = image;
    fxImage = effect;
    loaded = true;
    get("clip-poster").hidden = true;
    get("play").disabled = false;
    renderMotion();
    selectAtlasFrame(inspectedFrame);
    if (autoPlay && !document.hidden && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPlaying(true);
    }
  } catch {
    if (version === loadingVersion) get("media-error").hidden = false;
  }
}

const clipSelect = get("clip-select");
const categories = new Map();
for (const item of clips) {
  if (!categories.has(item.category)) {
    const group = document.createElement("optgroup");
    group.label = item.category;
    categories.set(item.category, group);
    clipSelect.append(group);
  }
  const option = document.createElement("option");
  option.value = item.id;
  option.textContent = item.name;
  categories.get(item.category).append(option);
}
clipSelect.addEventListener("change", (event) => selectClip(event.target.value, true));
get("motion-revision")?.addEventListener("click", (event) => {
  if (!clip) return;
  const source = activeTab === "atlas" ? inspectedFrame : playbackFrame;
  const previous = event.currentTarget.getAttribute("aria-pressed") !== "true";
  selectClip(clip.id, playing, previous, source / frames.length);
});

const initialId = location.hash.slice(1);
const defaultId = clips.some((item) => item.id === "walk_storyboard") ? "walk_storyboard" : "combat";
selectClip(clips.some((item) => item.id === initialId) ? initialId : defaultId, true);


