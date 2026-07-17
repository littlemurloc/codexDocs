const TOTAL_WAVES = 12;
const ELITE_WAVES = new Set([4, 8]);

const sets = {
  breakthrough: {
    name: "破军",
    accent: "red",
    mode: "unlock",
    components: ["fengshi", "zhangu", "zhanjiang"],
    high: "pozhen",
    summary: "正面突破、队长击破与 Boss 压力。",
  },
  fire: {
    name: "火计",
    accent: "orange",
    mode: "unlock",
    components: ["huoyou", "jiefeng", "huoshi"],
    high: "huogong",
    summary: "一路压制、持续灼烧与密集波处理。",
  },
  economy: {
    name: "屯田",
    accent: "green",
    mode: "fuse",
    components: ["tuntian", "shanglu", "canglin"],
    high: "fuguo",
    summary: "军资、刷新与中后期购买能力。",
  },
};

const cards = [
  {
    id: "fengshi",
    set: "breakthrough",
    name: "锋矢军略",
    type: "passive",
    cost: 3,
    tag: "攻击",
    text: "本局内，提高友方队长的攻击属性。",
  },
  {
    id: "zhangu",
    set: "breakthrough",
    name: "战鼓军略",
    type: "passive",
    cost: 3,
    tag: "攻速",
    text: "本局内，提高友方小队的攻击速度属性。",
  },
  {
    id: "zhanjiang",
    set: "breakthrough",
    name: "斩将令",
    type: "active",
    cost: 3,
    tag: "点杀",
    text: "指定一名敌方队长或精英，发动一次明确的斩将打击。",
  },
  {
    id: "huoyou",
    set: "fire",
    name: "火油军略",
    type: "passive",
    cost: 3,
    tag: "灼烧",
    text: "本局内，提高火系军令造成的持续灼烧收益。",
  },
  {
    id: "jiefeng",
    set: "fire",
    name: "借风军略",
    type: "passive",
    cost: 3,
    tag: "扩散",
    text: "本局内，火系军令更容易覆盖同一路的多个目标。",
  },
  {
    id: "huoshi",
    set: "fire",
    name: "火矢令",
    type: "active",
    cost: 3,
    tag: "一路",
    text: "指定敌方一路，发动一次火矢覆盖并留下短暂火区。",
  },
  {
    id: "tuntian",
    set: "economy",
    name: "屯田军略",
    type: "passive",
    cost: 3,
    tag: "军资",
    text: "每完成 2 波，额外获得 1 点军资。",
  },
  {
    id: "shanglu",
    set: "economy",
    name: "商路军略",
    type: "passive",
    cost: 3,
    tag: "刷新",
    text: "本局内，刷新报价的第二次及以后费用降低 1 点，最低为 1。",
  },
  {
    id: "canglin",
    set: "economy",
    name: "仓廪军略",
    type: "passive",
    cost: 3,
    tag: "储备",
    text: "波次结束时若军资不少于 6 点，额外获得 1 点军资。",
  },
  {
    id: "pozhen",
    set: "breakthrough",
    name: "破阵令",
    type: "active",
    cost: 5,
    tag: "高阶 / 一路",
    high: true,
    text: "指定敌方一路，发动强力冲阵事件，对整路敌人造成打击并改变阵线压力。",
  },
  {
    id: "huogong",
    set: "fire",
    name: "火攻令",
    type: "active",
    cost: 5,
    tag: "高阶 / 一路",
    high: true,
    text: "指定敌方一路。短暂预警后发动持续火攻，是清理密集波的高光时刻。",
  },
  {
    id: "fuguo",
    set: "economy",
    name: "富国军略",
    type: "passive",
    cost: 5,
    tag: "高阶 / 图鉴",
    high: true,
    text: "购买后吞噬屯田三组件。之后每次波次胜利额外获得 1 点军资，且每次备战首次刷新免费。",
  },
];

const cardById = new Map(cards.map((card) => [card.id, card]));

function createState() {
  return {
    wave: 1,
    funds: 6,
    refreshes: 0,
    owned: [],
    memory: [],
    unlocked: [],
    guaranteedHigh: [],
    offers: [],
    log: ["开局军资 6。选择军令，随后推进第 1 波。"],
    ended: false,
  };
}

let state = createState();
const app = document.querySelector("#app");

function hasOwned(cardId) {
  return state.owned.includes(cardId);
}

function hasMemory(cardId) {
  return state.memory.includes(cardId);
}

function hasSetProgress(setId) {
  const set = sets[setId];
  return set.components.filter(hasMemory).length;
}

function isSetComplete(setId) {
  return hasSetProgress(setId) === sets[setId].components.length;
}

function highStatus(setId) {
  const highCard = sets[setId].high;
  if (hasOwned(highCard)) return "owned";
  if (state.unlocked.includes(highCard)) return "unlocked";
  return "locked";
}

function currentRefreshCost() {
  const baseCost = state.refreshes + 1;
  if (hasOwned("fuguo") && state.refreshes === 0) return 0;
  if (hasOwned("shanglu") && state.refreshes >= 1) return Math.max(1, baseCost - 1);
  return baseCost;
}

function shuffled(items) {
  return [...items].sort(() => Math.random() - 0.5);
}

function eligibleCards() {
  return cards.filter((card) => {
    if (hasOwned(card.id)) return false;
    if (!card.high && hasMemory(card.id)) return false;
    if (card.high && !state.unlocked.includes(card.id)) return false;
    return true;
  });
}

function guaranteedMissingCard() {
  const candidates = Object.entries(sets)
    .map(([setId, set]) => {
      if (hasSetProgress(setId) !== 2 || isSetComplete(setId)) return null;
      return set.components.find((cardId) => !hasMemory(cardId));
    })
    .filter(Boolean)
    .map((cardId) => cardById.get(cardId));
  return candidates[0] ?? null;
}

function openingOffers() {
  return [cardById.get("zhanjiang"), cardById.get("huoshi"), cardById.get("tuntian")];
}

function generateOffers({ opening = false } = {}) {
  if (opening) return openingOffers();

  const selected = [];
  const nextHigh = state.guaranteedHigh.find((cardId) => !hasOwned(cardId));
  const missing = guaranteedMissingCard();

  if (nextHigh) selected.push(cardById.get(nextHigh));
  if (missing && !selected.some((card) => card.id === missing.id)) selected.push(missing);

  const candidates = shuffled(eligibleCards()).filter((card) => !selected.some((item) => item.id === card.id));
  selected.push(...candidates.slice(0, Math.max(0, 3 - selected.length)));
  return selected.slice(0, 3);
}

function addLog(text) {
  state.log = [text, ...state.log].slice(0, 9);
}

function checkSetUnlock(card) {
  const set = sets[card.set];
  const highCard = set.high;
  if (!isSetComplete(card.set) || state.unlocked.includes(highCard)) return;

  state.unlocked.push(highCard);
  state.guaranteedHigh.push(highCard);
  addLog(`${set.name} Set 完成，${cardById.get(highCard).name} 已解锁，将在下一次报价保底出现。`);
}

function buyCard(cardId) {
  const card = state.offers.find((offer) => offer.id === cardId);
  if (!card || state.ended || state.funds < card.cost) return;

  state.funds -= card.cost;
  state.owned.push(card.id);
  if (!hasMemory(card.id)) state.memory.push(card.id);
  state.offers = state.offers.filter((offer) => offer.id !== card.id);

  if (card.id === "fuguo") {
    const components = sets.economy.components;
    state.owned = state.owned.filter((ownedId) => !components.includes(ownedId));
    addLog("富国军略购入，屯田、商路、仓廪已吞噬并收纳至军略图鉴。");
  } else {
    addLog(`购入 ${card.name}，消耗 ${card.cost} 点军资。`);
  }

  if (!card.high) checkSetUnlock(card);
  render();
}

function refreshOffers() {
  if (state.ended) return;
  const cost = currentRefreshCost();
  if (state.funds < cost) return;
  state.funds -= cost;
  state.refreshes += 1;
  state.offers = generateOffers();
  addLog(cost === 0 ? "富国军略生效：本次备战首次刷新免费。" : `刷新报价，消耗 ${cost} 点军资。`);
  render();
}

function rewardForFinishedWave() {
  const isElite = ELITE_WAVES.has(state.wave);
  let income = isElite ? 3 : 2;
  const details = [isElite ? "精英波 +3" : "普通波 +2"];

  if (hasOwned("tuntian") && state.wave % 2 === 0) {
    income += 1;
    details.push("屯田 +1");
  }
  if (hasOwned("canglin") && state.funds >= 6) {
    income += 1;
    details.push("仓廪 +1");
  }
  if (hasOwned("fuguo")) {
    income += 1;
    details.push("富国 +1");
  }
  return { income, details };
}

function advanceWave() {
  if (state.ended) return;
  if (state.wave === TOTAL_WAVES) {
    state.ended = true;
    state.offers = [];
    addLog("第 12 波 Boss 已结算。本局军令、军资与图鉴记录将在局末清空。体验完成。");
    render();
    return;
  }

  const reward = rewardForFinishedWave();
  state.funds += reward.income;
  state.wave += 1;
  state.refreshes = 0;
  state.offers = generateOffers();
  addLog(`第 ${state.wave - 1} 波胜利：${reward.details.join("，")}。进入第 ${state.wave} 波备战。`);
  render();
}

function restart() {
  state = createState();
  state.offers = generateOffers({ opening: true });
  render();
}

function renderCard(card) {
  const set = sets[card.set];
  const affordable = state.funds >= card.cost;
  const kind = card.type === "active" ? "主动军令" : "被动军略";
  return `
    <article class="command-card ${set.accent} ${card.high ? "high-card" : ""}">
      <div class="card-topline">
        <span class="route-dot ${set.accent}"></span>
        <span>${set.name} / ${kind}</span>
        ${card.high ? '<span class="high-label">高阶</span>' : ""}
      </div>
      <h3>${card.name}</h3>
      <p>${card.text}</p>
      <div class="card-footer">
        <span class="tag">${card.tag}</span>
        <button class="buy-button" onclick="actions.buyCard('${card.id}')" ${affordable ? "" : "disabled"}>购入 ${card.cost}</button>
      </div>
    </article>
  `;
}

function renderWaveTrack() {
  const waves = Array.from({ length: TOTAL_WAVES }, (_, index) => index + 1);
  return `
    <div class="wave-track" aria-label="波次进度">
      ${waves
        .map((wave) => {
          const className = wave < state.wave ? "done" : wave === state.wave ? "current" : "";
          const label = wave === TOTAL_WAVES ? "Boss" : ELITE_WAVES.has(wave) ? "精英" : `W${wave}`;
          return `<span class="wave-node ${className}"><b>${label}</b><i></i></span>`;
        })
        .join("")}
    </div>
  `;
}

function renderSetRow(setId, set) {
  const progress = hasSetProgress(setId);
  const status = highStatus(setId);
  const highCard = cardById.get(set.high);
  const isFused = set.mode === "fuse" && hasOwned(set.high);
  return `
    <article class="set-row ${set.accent}">
      <div class="set-heading">
        <div><span class="eyebrow">${set.mode === "fuse" ? "吞噬型 Set" : "解锁型 Set"}</span><h3>${set.name}</h3></div>
        <strong>${progress} / 3</strong>
      </div>
      <p>${set.summary}</p>
      <div class="component-strip">
        ${set.components
          .map((cardId) => {
            const card = cardById.get(cardId);
            const got = hasMemory(cardId);
            return `<span class="component ${got ? "got" : ""}"><i>${got ? "✓" : ""}</i>${card.name}</span>`;
          })
          .join("")}
      </div>
      <div class="high-result ${status}">
        <span>${isFused ? "已吞噬入图鉴" : status === "owned" ? "已购入" : status === "unlocked" ? "已解锁，待报价" : "尚未解锁"}</span>
        <b>${highCard.name}</b>
      </div>
    </article>
  `;
}

function renderOwnedCard(card) {
  const set = sets[card.set];
  return `<div class="owned-card ${set.accent}"><span>${card.type === "active" ? "主动" : "被动"}</span><b>${card.name}</b><small>${card.high ? "高阶" : card.tag}</small></div>`;
}

function render() {
  const currentKind = state.wave === TOTAL_WAVES ? "Boss 波" : ELITE_WAVES.has(state.wave) ? "精英波" : "普通波";
  const activeCards = state.owned.map((id) => cardById.get(id)).filter((card) => card.type === "active");
  const passiveCards = state.owned.map((id) => cardById.get(id)).filter((card) => card.type === "passive");
  const refreshCost = currentRefreshCost();

  app.innerHTML = `
    <div class="shell">
      <header class="topbar">
        <div class="brand-block">
          <div><span class="eyebrow">三国斗阵 / 规则体验</span><h1>军令构筑体验场</h1></div>
          <p>抽取、购买、Set 解锁与吞噬合成的迷你原型</p>
        </div>
        <img class="commander-art" src="../../assets/characters/zhugeliang/v02-ink-wash-halfbody-avatar-256/zhugeliang-upperbody-512x1156.png" alt="诸葛亮立绘" />
        <button class="reset-button" onclick="actions.restart()">重开本局</button>
      </header>

      <section class="status-band">
        <div class="status-copy"><span class="eyebrow">当前备战</span><strong>第 ${state.wave} 波 <em>${currentKind}</em></strong></div>
        <div class="fund-box"><span>军资</span><b>${state.funds}</b></div>
        <div class="status-note">基础卡 3 军资，高阶卡 5 军资。所有内容均为当前讨论草案。</div>
        ${renderWaveTrack()}
      </section>

      <div class="content-grid">
        <section class="market-panel">
          <div class="panel-heading">
            <div><span class="eyebrow">备战军令市场</span><h2>三报价</h2></div>
            <div class="market-actions">
              <span>本次已刷新 ${state.refreshes} 次</span>
              <button onclick="actions.refreshOffers()" ${state.ended || state.funds < refreshCost ? "disabled" : ""}>刷新报价 ${refreshCost}</button>
            </div>
          </div>
          <div class="market-rule">开局固定出现破军、火计、屯田各 1 张。拥有同 Set 两张组件后，下次报价保底补齐缺失组件；Set 完成后，高阶卡保底出现。</div>
          <div class="offer-grid">${state.offers.length ? state.offers.map(renderCard).join("") : `<div class="empty-offers">${state.ended ? "本局结束，军令记录仅用于本次体验。" : "本轮报价已购完。可刷新，或直接推进波次。"}</div>`}</div>
          <div class="wave-action"><button class="advance-button" onclick="actions.advanceWave()" ${state.ended ? "disabled" : ""}>${state.wave === TOTAL_WAVES ? "结算第 12 波 Boss" : `模拟结束第 ${state.wave} 波`}</button><span>不模拟战斗数值，只验证构筑节奏。</span></div>
        </section>

        <aside class="right-rail">
          <section class="build-panel">
            <div class="panel-heading"><div><span class="eyebrow">局内持有</span><h2>军令与军略</h2></div></div>
            <div class="owned-group"><span>主动军令 / HUD</span>${activeCards.length ? activeCards.map(renderOwnedCard).join("") : '<p class="empty">尚未购入主动军令。</p>'}</div>
            <div class="owned-group"><span>被动军略 / 图鉴</span>${passiveCards.length ? passiveCards.map(renderOwnedCard).join("") : '<p class="empty">尚未购入被动军略。</p>'}</div>
          </section>
          <section class="log-panel">
            <div class="panel-heading"><div><span class="eyebrow">局内记录</span><h2>军报</h2></div></div>
            <div class="log-list">${state.log.map((entry) => `<p>${entry}</p>`).join("")}</div>
          </section>
        </aside>
      </div>

      <section class="set-section">
        <div class="section-header"><div><span class="eyebrow">构筑进度</span><h2>Set 与高阶军令</h2></div><p>解锁型 Set 保留基础卡；吞噬型 Set 在购入高阶被动后将基础被动合成为一项图鉴军略。</p></div>
        <div class="set-grid">${Object.entries(sets).map(([setId, set]) => renderSetRow(setId, set)).join("")}</div>
      </section>
    </div>
  `;
}

window.actions = { buyCard, refreshOffers, advanceWave, restart };
restart();
