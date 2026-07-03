const KEYWORD_CLASS = {
  护盾: "shield",
  反击: "shield",
  灼烧: "burn",
  流血: "bleed",
  斩杀: "bleed",
  破甲: "bleed",
};

const stages = [
  {
    id: "stage_01",
    name: "黄巾余烬",
    tag: "新手 / 杂兵潮",
    unlocked: true,
    difficulties: [
      {
        id: "stage_01_d01",
        name: "难度 1",
        waves: [
          { name: "黄巾步卒", preview: "少量步卒，适合理解推进、接敌和击灭获胜。", enemies: [{ id: "yellow_rebel", count: 3 }] },
        ],
      },
      {
        id: "stage_01_d02",
        name: "难度 2",
        waves: [
          { name: "黄巾步卒", preview: "基础步卒队形，观察前排接敌。", enemies: [{ id: "yellow_rebel", count: 4 }] },
          { name: "弓手试探", preview: "少量黄巾弓手加入，测试前排保护与后排处理。", enemies: [{ id: "yellow_rebel", count: 3 }, { id: "rebel_archer", count: 1 }] },
        ],
      },
      {
        id: "stage_01_d03",
        name: "难度 3",
        waves: [
          { name: "密集残兵", preview: "杂兵密度提高，范围与反击收益更明显。", enemies: [{ id: "yellow_rebel", count: 5 }] },
          { name: "力士压阵", preview: "黄巾力士加入，第一次面对厚前排。", enemies: [{ id: "shield_rebel", count: 2 }, { id: "yellow_rebel", count: 2 }] },
        ],
      },
      {
        id: "stage_01_d04",
        name: "难度 4",
        waves: [
          { name: "步卒前压", preview: "步卒数量提高，测试基础清杂。", enemies: [{ id: "yellow_rebel", count: 5 }] },
          { name: "弓手掩护", preview: "后排弓手出现，需要突进、范围或快速清杂。", enemies: [{ id: "rebel_archer", count: 3 }] },
          { name: "力士混编", preview: "力士与步卒混编，处理前后排压力。", enemies: [{ id: "shield_rebel", count: 2 }, { id: "yellow_rebel", count: 3 }] },
        ],
      },
      {
        id: "stage_01_d05",
        name: "难度 5",
        waves: [
          { name: "步弓混编", preview: "步卒和弓手混编，测试默认 2 人位基础闭环。", enemies: [{ id: "yellow_rebel", count: 4 }, { id: "rebel_archer", count: 2 }] },
          { name: "祭酒号令", preview: "黄巾祭酒加入，会放大步卒压力，建议优先处理。", enemies: [{ id: "rebel_priest", count: 1 }, { id: "yellow_rebel", count: 4 }] },
          { name: "黄巾渠帅", preview: "关卡 2 解锁门槛 Boss，弱点窗口和清杂能力都重要。", enemies: [{ id: "yellow_boss", count: 1 }, { id: "yellow_rebel", count: 3 }] },
        ],
      },
      {
        id: "stage_01_d06",
        name: "难度 6",
        waves: [
          { name: "步卒密集", preview: "复刷难度起点，清杂压力更稳定。", enemies: [{ id: "yellow_rebel", count: 7 }] },
          { name: "弓步推进", preview: "弓手与步卒同时推进，测试功能怪优先级。", enemies: [{ id: "rebel_archer", count: 3 }, { id: "yellow_rebel", count: 4 }] },
          { name: "力士祭酒", preview: "厚前排保护祭酒，推荐范围、控制或斩杀。", enemies: [{ id: "shield_rebel", count: 2 }, { id: "rebel_priest", count: 1 }] },
        ],
      },
      {
        id: "stage_01_d07",
        name: "难度 7",
        waves: [
          { name: "步卒", preview: "连续多波开始，测试技能循环稳定性。", enemies: [{ id: "yellow_rebel", count: 5 }] },
          { name: "弓手", preview: "远程压力单独出现，观察后排处理能力。", enemies: [{ id: "rebel_archer", count: 4 }] },
          { name: "力士", preview: "厚前排单独压阵，测试破甲与持续伤害。", enemies: [{ id: "shield_rebel", count: 3 }] },
          { name: "祭酒弓手", preview: "祭酒和弓手组合，推荐灼烧扩散或反击承压。", enemies: [{ id: "rebel_priest", count: 1 }, { id: "rebel_archer", count: 3 }] },
        ],
      },
      {
        id: "stage_01_d08",
        name: "难度 8",
        waves: [
          { name: "步卒密集", preview: "密集杂兵潮，清杂能力开始吃紧。", enemies: [{ id: "yellow_rebel", count: 8 }] },
          { name: "力士步卒", preview: "厚前排拖延步卒潮，推荐灼烧或破甲。", enemies: [{ id: "shield_rebel", count: 3 }, { id: "yellow_rebel", count: 4 }] },
          { name: "弓手群", preview: "后排远程集中，前排承压明显。", enemies: [{ id: "rebel_archer", count: 5 }] },
          { name: "渠帅弱化版", preview: "弱化 Boss 检查精英击破和清杂节奏。", enemies: [{ id: "rebel_captain", count: 1 }, { id: "yellow_rebel", count: 4 }] },
        ],
      },
      {
        id: "stage_01_d09",
        name: "难度 9",
        waves: [
          { name: "弓手步卒", preview: "高远程密度开局，注意前排拖延。", enemies: [{ id: "rebel_archer", count: 4 }, { id: "yellow_rebel", count: 4 }] },
          { name: "力士", preview: "力士集中压阵，测试单体破甲能力。", enemies: [{ id: "shield_rebel", count: 4 }] },
          { name: "祭酒弓手", preview: "增益与远程混合，推荐突进、控制或治疗。", enemies: [{ id: "rebel_priest", count: 2 }, { id: "rebel_archer", count: 3 }] },
          { name: "力士渠帅", preview: "厚前排拖延渠帅弱化版，需要清前排再打本体。", enemies: [{ id: "shield_rebel", count: 2 }, { id: "rebel_captain", count: 1 }] },
        ],
      },
      {
        id: "stage_01_d10",
        name: "难度 10",
        waves: [
          { name: "步卒密集", preview: "关卡 1 完全挑战开场，密集清场压力。", enemies: [{ id: "yellow_rebel", count: 9 }] },
          { name: "弓手群", preview: "后排火力集中，测试前排保护与快速清后。", enemies: [{ id: "rebel_archer", count: 6 }] },
          { name: "力士祭酒", preview: "厚前排保护增益源，推荐控制、破甲或斩杀。", enemies: [{ id: "shield_rebel", count: 3 }, { id: "rebel_priest", count: 2 }] },
          { name: "步卒增援", preview: "增援潮检查持续清杂与技能循环。", enemies: [{ id: "yellow_rebel", count: 10 }] },
          { name: "黄巾渠帅强化版", preview: "强化 Boss 波，清场、控制和 Boss 单体都重要。", enemies: [{ id: "yellow_boss", count: 1 }, { id: "shield_rebel", count: 2 }, { id: "yellow_rebel", count: 4 }] },
        ],
      },
    ],
  },
];

const heroTemplates = [
  {
    id: "zhangfei",
    name: "张飞",
    faction: "蜀",
    className: "猛将",
    role: "前排承伤，护盾反击启动点",
    hp: 1350,
    atk: 48,
    armor: 22,
    attackInterval: 1.9,
    speed: 22,
    range: 32,
    tags: ["护盾", "反击"],
    equipment: ["xuantiedun", "huwen"],
    skills: [
      ["怒吼开阵", "护盾", 6, "获得护盾并嘲讽最近敌人"],
      ["裂胆一击", "破甲", 5, "攻击最近敌人并附加破甲"],
      ["燕人反击", "反击", 8, "受击后提高下一次反击"],
      ["横扫", "范围", 7, "攻击近处多个敌人"],
      ["据守", "护盾", 10, "短时提高护甲"],
      ["震退", "控制", 9, "击退近处目标"],
    ],
  },
  {
    id: "guanyu",
    name: "关羽",
    faction: "蜀",
    className: "猛将",
    role: "破甲与流血斩杀",
    hp: 1150,
    atk: 65,
    armor: 16,
    attackInterval: 1.7,
    speed: 24,
    range: 34,
    tags: ["流血", "破甲", "斩杀"],
    equipment: ["xuewen", "duanshou"],
    skills: [
      ["青龙斩", "流血", 5, "对最近敌人造成流血"],
      ["武圣压阵", "破甲", 7, "降低目标护甲"],
      ["拖刀追击", "斩杀", 8, "对低血目标追加伤害"],
      ["义绝", "增益", 9, "提高自身攻击"],
      ["破阵", "范围", 8, "攻击前方多个敌人"],
      ["定军", "控制", 10, "短时眩晕目标"],
    ],
  },
  {
    id: "zhouyu",
    name: "周瑜",
    faction: "吴",
    className: "智将",
    role: "灼烧扩散与范围清杂",
    hp: 720,
    atk: 74,
    armor: 6,
    attackInterval: 1.8,
    speed: 20,
    range: 170,
    tags: ["灼烧", "范围"],
    equipment: ["chiyan", "liaoyuan"],
    skills: [
      ["赤焰", "灼烧", 4, "点燃目标"],
      ["连环火", "灼烧", 8, "灼烧附近敌人"],
      ["火借风势", "范围", 9, "对密集敌人造成范围伤害"],
      ["都督令", "增益", 10, "提高队友攻击"],
      ["断粮火", "减益", 7, "降低敌人攻击"],
      ["火幕", "控制", 11, "短时减速敌人"],
    ],
  },
  {
    id: "sunshangxiang",
    name: "孙尚香",
    faction: "吴",
    className: "敏将",
    role: "远程连击与流血补伤",
    hp: 760,
    atk: 72,
    armor: 8,
    attackInterval: 1.3,
    speed: 30,
    range: 185,
    tags: ["连击", "流血"],
    equipment: ["liegu", "baima"],
    skills: [
      ["连珠箭", "连击", 4, "多次命中目标"],
      ["裂帛箭", "流血", 6, "附加流血"],
      ["翻身射", "机动", 7, "调整位置并攻击"],
      ["破甲箭", "破甲", 8, "降低目标护甲"],
      ["疾射", "增益", 9, "提高攻击频率"],
      ["收割", "斩杀", 10, "攻击低血目标"],
    ],
  },
  {
    id: "caocao",
    name: "曹操",
    faction: "魏",
    className: "辅将",
    role: "士气、治疗与护盾队辅助",
    hp: 900,
    atk: 45,
    armor: 11,
    attackInterval: 1.7,
    speed: 21,
    range: 150,
    tags: ["治疗", "士气", "护盾"],
    equipment: ["huixue", "xuantiedun"],
    skills: [
      ["魏武令", "士气", 7, "提高队友攻击"],
      ["军心不坠", "治疗", 8, "治疗低血队友"],
      ["护心策", "护盾", 9, "给前排护盾"],
      ["乱世权谋", "减益", 8, "降低敌人攻击"],
      ["再整旗鼓", "治疗", 12, "群体小治疗"],
      ["号令追击", "增益", 10, "提高队友速度"],
    ],
  },
  {
    id: "lvbu",
    name: "吕布",
    faction: "群",
    className: "敏将",
    role: "高爆发单体压制",
    hp: 1000,
    atk: 82,
    armor: 12,
    attackInterval: 1.4,
    speed: 27,
    range: 36,
    tags: ["爆发", "斩杀"],
    equipment: ["baima", "duanshou"],
    skills: [
      ["无双突击", "爆发", 6, "重击最近敌人"],
      ["方天横扫", "范围", 8, "攻击近处多个敌人"],
      ["追命", "斩杀", 9, "低血追加伤害"],
      ["战意", "增益", 10, "提高自身攻击"],
      ["破军", "破甲", 8, "附加破甲"],
      ["震慑", "控制", 11, "短时眩晕"],
    ],
  },
];

const enemyTemplates = {
  yellow_rebel: { name: "黄巾步卒", hp: 260, atk: 32, armor: 4, attackInterval: 1.6, range: 28, speed: 18, tags: ["杂兵"] },
  shield_rebel: { name: "黄巾力士", hp: 850, atk: 44, armor: 28, attackInterval: 1.8, range: 28, speed: 14, tags: ["高护甲"] },
  rebel_archer: { name: "黄巾弓手", hp: 380, atk: 56, armor: 5, attackInterval: 1.5, range: 160, speed: 16, tags: ["后排", "远程"] },
  rebel_priest: { name: "黄巾祭酒", hp: 500, atk: 34, armor: 6, attackInterval: 1.9, range: 145, speed: 15, tags: ["增益", "后排"] },
  rebel_captain: { name: "余烬头目", hp: 1800, atk: 68, armor: 18, attackInterval: 1.5, range: 34, speed: 18, tags: ["精英", "破甲"] },
  yellow_boss: { name: "黄巾渠帅", hp: 2800, atk: 62, armor: 16, attackInterval: 1.8, range: 48, speed: 16, tags: ["Boss", "弱点窗口"] },
};

const equipment = {
  xuantiedun: { name: "玄铁盾", tag: "护盾", text: "开战获得 90 护盾。" },
  huwen: { name: "虎纹重甲", tag: "反击", text: "受击反击伤害提高。" },
  xuewen: { name: "血纹匕首", tag: "流血", text: "普通攻击概率附加流血。" },
  liegu: { name: "裂骨箭囊", tag: "流血", text: "连击可附加流血。" },
  chiyan: { name: "赤焰羽扇", tag: "灼烧", text: "灼烧伤害提高。" },
  liaoyuan: { name: "燎原石", tag: "灼烧", text: "击杀灼烧目标时扩散灼烧。" },
  baima: { name: "白马镫", tag: "连击", text: "攻击有概率追加命中。" },
  duanshou: { name: "断首符", tag: "斩杀", text: "低血敌人受到更高伤害。" },
  huixue: { name: "还血护符", tag: "治疗", text: "反击或护盾触发后少量回血。" },
};

const prepPool = [
  { id: "prep_shield_counter", name: "破盾回击", tags: ["护盾", "反击"], text: "拥有护盾的我方受击后，每波最多触发一次反击补伤。", apply: (s) => (s.mods.shieldCounter += 1) },
  { id: "prep_burn_spread", name: "火势牵连", tags: ["灼烧"], text: "灼烧目标死亡时，向附近敌人扩散一层灼烧。", apply: (s) => (s.mods.burnSpread += 1) },
  { id: "prep_weak_fire", name: "弱点齐射", tags: ["Boss", "爆发"], text: "Boss 低于 55% 生命时触发一次全队集火。", apply: (s) => (s.mods.weakFire += 1) },
  { id: "prep_warmup", name: "技能预热", tags: ["技能"], text: "下一波我方技能冷却提前 35%。", apply: (s) => (s.mods.warmup += 1) },
  { id: "prep_bleed", name: "裂甲先声", tags: ["流血", "破甲"], text: "开战时敌方前排获得破甲，流血伤害提高。", apply: (s) => (s.mods.bleedBoost += 1) },
  { id: "prep_heal", name: "临阵疗伤", tags: ["治疗"], text: "进入下一波前回复 18% 最大生命。", apply: (s) => (s.mods.preHeal += 1) },
  { id: "prep_recon", name: "重新侦察", tags: ["资源修整"], text: "本次选择后额外记录一次重掷机会。", apply: (s) => (s.rerolls += 1) },
  { id: "prep_laststand", name: "破釜沉舟", tags: ["风险"], text: "低血时伤害提高，但治疗收益下降。", apply: (s) => (s.mods.lastStand += 1) },
];

const defaultState = () => ({
  screen: "setup",
  stageId: "stage_01",
  difficultyId: "stage_01_d01",
  selectedHeroIds: ["zhangfei", "zhouyu"],
  selectedEquipment: {
    zhangfei: ["xuantiedun", "huwen"],
    guanyu: ["xuewen", "duanshou"],
    zhouyu: ["chiyan", "liaoyuan"],
    sunshangxiang: ["liegu", "baima"],
    caocao: ["huixue", "xuantiedun"],
    lvbu: ["baima", "duanshou"],
  },
  skillLoadout: Object.fromEntries(heroTemplates.map((h) => [h.id, [0, 1, 2, 3]])),
  waveIndex: 0,
  time: 0,
  running: false,
  units: [],
  chosenPreps: [],
  prepChoices: [],
  pendingNextWave: false,
  result: null,
  logs: ["选择 2 名武将后开始挑战。"],
  mods: { shieldCounter: 0, burnSpread: 0, weakFire: 0, warmup: 0, bleedBoost: 0, preHeal: 0, lastStand: 0 },
  rerolls: 0,
});

let state = defaultState();
let loopHandle = null;

const app = document.querySelector("#app");

function currentStage() {
  return stages.find((stage) => stage.id === state.stageId);
}

function currentDifficulty() {
  return currentStage().difficulties.find((difficulty) => difficulty.id === state.difficultyId);
}

function currentWave() {
  return currentDifficulty().waves[state.waveIndex];
}

function log(message) {
  state.logs = [`${formatTime(state.time)} ${message}`, ...state.logs].slice(0, 80);
}

function formatTime(time) {
  const minutes = Math.floor(time / 60).toString().padStart(2, "0");
  const seconds = Math.floor(time % 60).toString().padStart(2, "0");
  return `[${minutes}:${seconds}]`;
}

function cloneHero(template, index) {
  const equipIds = state.selectedEquipment[template.id] ?? [];
  const hasShield = equipIds.includes("xuantiedun");
  return {
    uid: `hero_${template.id}`,
    side: "hero",
    name: template.name,
    className: template.className,
    x: 10 - index * 4,
    y: index === 0 ? 43 : 57,
    hp: template.hp,
    maxHp: template.hp,
    atk: template.atk,
    armor: template.armor,
    attackInterval: template.attackInterval,
    speed: template.speed,
    range: template.range,
    tags: [...template.tags],
    equipment: equipIds,
    skills: state.skillLoadout[template.id].map((skillIndex) => {
      const skill = [...template.skills[skillIndex]];
      skill.cdLeft = state.mods.warmup ? skill[2] * 0.35 : 0;
      return skill;
    }),
    shield: hasShield ? 90 : 0,
    bleed: 0,
    burn: 0,
    weakFired: false,
    attackCd: 0,
  };
}

function cloneEnemy(enemyId, index, total) {
  const template = enemyTemplates[enemyId];
  const row = total === 1 ? 50 : 38 + (index % 4) * 8;
  return {
    uid: `enemy_${enemyId}_${index}_${Math.random().toString(16).slice(2)}`,
    side: "enemy",
    name: template.name,
    x: 90 + Math.floor(index / 4) * 4,
    y: row,
    hp: template.hp,
    maxHp: template.hp,
    atk: template.atk,
    armor: template.armor,
    attackInterval: template.attackInterval,
    speed: template.speed,
    range: template.range,
    tags: [...template.tags],
    shield: 0,
    bleed: state.mods.bleedBoost && index === 0 ? 2 : 0,
    burn: 0,
    attackCd: 0,
    weakFired: false,
  };
}

function startChallenge() {
  state.waveIndex = 0;
  state.time = 0;
  state.result = null;
  state.chosenPreps = [];
  state.mods = { shieldCounter: 0, burnSpread: 0, weakFire: 0, warmup: 0, bleedBoost: 0, preHeal: 0, lastStand: 0 };
  state.rerolls = 0;
  state.logs = [];
  spawnWave();
  state.screen = "battle";
  state.running = true;
  log(`开始挑战 ${currentStage().name} ${currentDifficulty().name}。`);
  startLoop();
  render();
}

function spawnWave() {
  const heroes = state.selectedHeroIds.map((id, index) => cloneHero(heroTemplates.find((hero) => hero.id === id), index));
  if (state.units.some((unit) => unit.side === "hero")) {
    const previousHeroes = state.units.filter((unit) => unit.side === "hero");
    heroes.forEach((hero) => {
      const previous = previousHeroes.find((unit) => unit.uid === hero.uid);
      if (previous) {
        hero.hp = Math.max(1, previous.hp);
        hero.shield += previous.shield;
      }
      if (state.mods.preHeal) {
        hero.hp = Math.min(hero.maxHp, hero.hp + hero.maxHp * 0.18);
      }
    });
  }

  const enemies = [];
  currentWave().enemies.forEach((entry) => {
    for (let i = 0; i < entry.count; i += 1) {
      enemies.push(cloneEnemy(entry.id, enemies.length, entry.count));
    }
  });

  state.units = [...heroes, ...enemies];
  state.pendingNextWave = false;
  log(`第 ${state.waveIndex + 1} 波：${currentWave().name}。`);
}

function startLoop() {
  if (loopHandle) clearInterval(loopHandle);
  loopHandle = setInterval(() => {
    if (!state.running) return;
    tick(0.25);
    render();
  }, 250);
}

function stopLoop() {
  if (loopHandle) clearInterval(loopHandle);
  loopHandle = null;
}

function aliveUnits(side) {
  return state.units.filter((unit) => unit.side === side && unit.hp > 0);
}

function distance(a, b) {
  return Math.abs(a.x - b.x) * 10;
}

function nearestEnemy(unit) {
  const candidates = aliveUnits(unit.side === "hero" ? "enemy" : "hero");
  return candidates.sort((a, b) => distance(unit, a) - distance(unit, b))[0];
}

function tick(dt) {
  state.time += dt;
  state.units.forEach((unit) => {
    if (unit.hp <= 0) return;
    applyDots(unit, dt);
    if (unit.hp <= 0) return;
    const target = nearestEnemy(unit);
    if (!target) return;
    const inRange = distance(unit, target) <= unit.range;
    if (!inRange) {
      unit.x += (unit.side === "hero" ? 1 : -1) * unit.speed * dt * 0.16;
      return;
    }
    unit.attackCd -= dt;
    if (unit.skills) {
      unit.skills.forEach((skill) => (skill.cdLeft = Math.max(0, skill.cdLeft - dt)));
      const readySkill = unit.skills.find((skill) => skill.cdLeft <= 0);
      if (readySkill) {
        castSkill(unit, target, readySkill);
        readySkill.cdLeft = readySkill[2];
        return;
      }
    }
    if (unit.attackCd <= 0) {
      attack(unit, target);
      unit.attackCd = unit.attackInterval ?? 1.5;
    }
  });
  state.units = state.units.filter((unit) => unit.hp > 0);
  checkBattleState();
}

function applyDots(unit, dt) {
  if (unit.bleed > 0) {
    unit.hp -= (5 + state.mods.bleedBoost * 2) * unit.bleed * dt;
  }
  if (unit.burn > 0) {
    const burnBonus = unit.side === "enemy" && hasHeroEquipment("chiyan") ? 4 : 0;
    unit.hp -= (6 + burnBonus) * unit.burn * dt;
  }
}

function hasHeroEquipment(equipmentId) {
  return aliveUnits("hero").some((unit) => unit.equipment.includes(equipmentId));
}

function dealDamage(source, target, rawDamage, tag = "") {
  let damage = Math.max(3, rawDamage - target.armor * 0.32);
  if (state.mods.lastStand && source.side === "hero" && source.hp / source.maxHp < 0.35) damage *= 1.35;
  if (source.equipment?.includes("duanshou") && target.hp / target.maxHp < 0.28) damage *= 1.35;
  if (source.equipment?.includes("baima") && Math.random() < 0.18) damage *= 1.32;
  if (target.shield > 0) {
    const absorbed = Math.min(target.shield, damage);
    target.shield -= absorbed;
    damage -= absorbed;
    if (state.mods.shieldCounter && target.side === "hero" && !target.counteredThisWave) {
      target.counteredThisWave = true;
      const counterTarget = nearestEnemy(target);
      if (counterTarget) {
        counterTarget.hp -= target.atk * 0.42;
        log(`${target.name} 触发破盾回击。`);
      }
    }
  }
  target.hp -= damage;
  if (target.hp <= 0) onUnitKilled(source, target, tag);
}

function onUnitKilled(source, target) {
  if (target.burn > 0 && state.mods.burnSpread) {
    aliveUnits(target.side)
      .filter((unit) => unit.uid !== target.uid)
      .slice(0, 2)
      .forEach((unit) => (unit.burn += 1));
    log(`${target.name} 的灼烧扩散。`);
  }
  if (source.side === "hero") log(`${source.name} 击败 ${target.name}。`);
}

function attack(unit, target) {
  dealDamage(unit, target, unit.atk, "attack");
  if (unit.equipment?.includes("xuewen") && Math.random() < 0.24) target.bleed += 1;
  if (unit.equipment?.includes("liegu") && Math.random() < 0.16) target.bleed += 1;
}

function castSkill(unit, target, skill) {
  const [name, keyword] = skill;
  if (keyword === "治疗") {
    const friend = aliveUnits(unit.side).sort((a, b) => a.hp / a.maxHp - b.hp / b.maxHp)[0];
    const ratio = state.mods.lastStand ? 0.7 : 1;
    friend.hp = Math.min(friend.maxHp, friend.hp + unit.atk * 1.2 * ratio);
    log(`${unit.name} 释放 ${name}，治疗 ${friend.name}。`);
    return;
  }
  if (keyword === "护盾") {
    unit.shield += 70;
    log(`${unit.name} 释放 ${name}，获得护盾。`);
    return;
  }
  if (keyword === "增益" || keyword === "士气") {
    unit.atk += 4;
    log(`${unit.name} 释放 ${name}，提升战斗状态。`);
    return;
  }
  const multiplier = keyword === "爆发" || keyword === "斩杀" ? 1.55 : keyword === "范围" ? 0.78 : 1.18;
  if (keyword === "范围") {
    aliveUnits(target.side)
      .filter((enemy) => distance(unit, enemy) <= unit.range + 50)
      .slice(0, 3)
      .forEach((enemy) => dealDamage(unit, enemy, unit.atk * multiplier, keyword));
  } else {
    dealDamage(unit, target, unit.atk * multiplier, keyword);
  }
  if (keyword === "流血") target.bleed += 2;
  if (keyword === "灼烧") target.burn += 2;
  if (keyword === "破甲") target.armor = Math.max(0, target.armor - 5);
  if (state.mods.weakFire && unit.side === "hero") tryWeakFire(target);
  log(`${unit.name} 释放 ${name}。`);
}

function tryWeakFire(target) {
  if (!target.tags.includes("Boss") || target.weakFired || target.hp / target.maxHp > 0.55) return;
  target.weakFired = true;
  const burst = aliveUnits("hero").reduce((sum, hero) => sum + hero.atk * 0.35, 0);
  target.hp -= burst;
  log(`${target.name} 暴露弱点，全队齐射。`);
}

function checkBattleState() {
  const heroes = aliveUnits("hero");
  const enemies = aliveUnits("enemy");
  if (heroes.length === 0) {
    state.running = false;
    state.result = "fail";
    state.screen = "result";
    log("我方全灭，挑战失败。");
    stopLoop();
    return;
  }
  if (enemies.length === 0) {
    if (state.waveIndex < currentDifficulty().waves.length - 1) {
      state.running = false;
      state.pendingNextWave = true;
      state.prepChoices = drawPrepChoices();
      log("当前波次胜利，进入备战。");
    } else {
      state.running = false;
      state.result = "win";
      state.screen = "result";
      log("完成全部波次，难度通关。");
      stopLoop();
    }
  }
}

function drawPrepChoices() {
  const shuffled = [...prepPool].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, 3);
}

function choosePrep(prepId) {
  const prep = state.prepChoices.find((item) => item.id === prepId);
  if (!prep) return;
  prep.apply(state);
  state.chosenPreps.push(prep);
  state.waveIndex += 1;
  spawnWave();
  state.running = true;
  state.prepChoices = [];
  startLoop();
  render();
}

function toggleHero(heroId) {
  if (state.running) return;
  if (state.selectedHeroIds.includes(heroId)) {
    if (state.selectedHeroIds.length <= 1) return;
    state.selectedHeroIds = state.selectedHeroIds.filter((id) => id !== heroId);
  } else if (state.selectedHeroIds.length < 2) {
    state.selectedHeroIds.push(heroId);
  }
  render();
}

function setDifficulty(difficultyId) {
  state.difficultyId = difficultyId;
  render();
}

function toggleSkill(heroId, skillIndex) {
  const loadout = state.skillLoadout[heroId];
  if (loadout.includes(skillIndex)) {
    if (loadout.length <= 1) return;
    state.skillLoadout[heroId] = loadout.filter((index) => index !== skillIndex);
  } else if (loadout.length < 4) {
    state.skillLoadout[heroId] = [...loadout, skillIndex].sort((a, b) => a - b);
  }
  render();
}

function reset() {
  state = defaultState();
  stopLoop();
  render();
}

function renderTags(tags) {
  return `<div class="tags">${tags.map((tag) => `<span class="tag ${KEYWORD_CLASS[tag] ?? ""}">${tag}</span>`).join("")}</div>`;
}

function renderSetupPanel() {
  return `
    <section class="panel">
      <div class="panel-header"><h2>关卡与难度</h2></div>
      <div class="panel-body stack">
        <div class="stage-list">
          ${stages
            .map(
              (stage) => `
                <div class="row-card selected">
                  <div class="row-head"><span class="row-title">${stage.name}</span><span class="muted">${stage.tag}</span></div>
                  ${renderTags(["单线", "PVE", "战备"])}
                </div>
              `,
            )
            .join("")}
        </div>
        <div class="stage-list">
          ${currentStage().difficulties
            .map(
              (difficulty) => `
              <button class="row-card ${difficulty.id === state.difficultyId ? "selected" : ""}" onclick="actions.setDifficulty('${difficulty.id}')">
                <div class="row-head"><span class="row-title">${difficulty.name}</span><span class="muted">${difficulty.waves.length} 波</span></div>
                <div class="muted">${difficulty.waves.map((wave) => wave.name).join(" / ")}</div>
              </button>
            `,
            )
            .join("")}
        </div>
        <button class="primary" onclick="actions.startChallenge()" ${state.selectedHeroIds.length !== 2 ? "disabled" : ""}>开始挑战</button>
      </div>
    </section>
  `;
}

function renderHeroPanel() {
  return `
    <section class="panel">
      <div class="panel-header"><h2>阵容配置</h2></div>
      <div class="panel-body stack">
        <div class="muted">当前参考版固定 2 人位，用来验证默认体验。</div>
        <div class="hero-list">
          ${heroTemplates
            .map((hero) => {
              const selected = state.selectedHeroIds.includes(hero.id);
              return `
                <div class="row-card ${selected ? "selected" : ""}">
                  <div class="row-head">
                    <button class="ghost" onclick="actions.toggleHero('${hero.id}')">${selected ? "下阵" : "上阵"}</button>
                    <span class="row-title">${hero.name}</span>
                    <span class="muted">${hero.faction} / ${hero.className}</span>
                  </div>
                  <div class="muted">${hero.role}</div>
                  ${renderTags(hero.tags)}
                  ${selected ? renderSkillLoadout(hero) : ""}
                </div>
              `;
            })
            .join("")}
        </div>
      </div>
    </section>
  `;
}

function renderSkillLoadout(hero) {
  return `
    <div class="skill-grid">
      ${hero.skills
        .map((skill, index) => {
          const active = state.skillLoadout[hero.id].includes(index);
          return `<button class="skill ${active ? "active" : ""}" onclick="actions.toggleSkill('${hero.id}', ${index})">${skill[0]}<br><span class="muted">${skill[1]}</span></button>`;
        })
        .join("")}
    </div>
    <div class="equipment-list" style="margin-top:8px">
      ${(state.selectedEquipment[hero.id] ?? [])
        .map((id) => `<div class="muted">${equipment[id].name}：${equipment[id].text}</div>`)
        .join("")}
    </div>
  `;
}

function renderBattlefield() {
  const difficulty = currentDifficulty();
  return `
    <main class="panel battlefield">
      <div class="battle-status">
        <div class="stat-box"><span class="stat-label">挑战</span><span class="stat-value">${currentStage().name} ${difficulty.name}</span></div>
        <div class="stat-box"><span class="stat-label">波次</span><span class="stat-value">${Math.min(state.waveIndex + 1, difficulty.waves.length)} / ${difficulty.waves.length}</span></div>
        <div class="stat-box"><span class="stat-label">时间</span><span class="stat-value">${formatTime(state.time).replace("[", "").replace("]", "")}</span></div>
        <div class="stat-box"><span class="stat-label">已选战备</span><span class="stat-value">${state.chosenPreps.length}</span></div>
      </div>
      <div class="lane">
        ${state.units.map(renderUnit).join("")}
      </div>
      <div class="battle-controls">
        <div class="screen-actions">
          ${state.screen === "setup" ? `<button class="primary" onclick="actions.startChallenge()">开始挑战</button>` : ""}
          ${state.running ? `<button onclick="actions.pause()">暂停</button>` : state.screen === "battle" && !state.pendingNextWave ? `<button onclick="actions.resume()">继续</button>` : ""}
          <button class="ghost" onclick="actions.reset()">重置</button>
        </div>
        <div class="muted">${state.pendingNextWave ? "波次胜利，等待战备选择" : state.running ? "自动战斗中" : "配置或结算中"}</div>
      </div>
    </main>
  `;
}

function renderUnit(unit) {
  const hpPct = Math.max(0, Math.min(100, (unit.hp / unit.maxHp) * 100));
  const effects = [
    unit.shield > 0 ? `盾 ${Math.round(unit.shield)}` : "",
    unit.bleed > 0 ? `血 ${unit.bleed}` : "",
    unit.burn > 0 ? `火 ${unit.burn}` : "",
  ]
    .filter(Boolean)
    .join(" / ");
  return `
    <div class="unit ${unit.side}" style="left:${unit.x}%; top:${unit.y}%">
      <div class="unit-name">${unit.name}</div>
      <div class="hp-bar"><div class="hp-fill" style="width:${hpPct}%"></div></div>
      <div class="unit-meta"><span>${Math.ceil(unit.hp)} HP</span><span>${unit.side === "hero" ? unit.className : unit.tags[0]}</span></div>
      <div class="effect-line">${effects}</div>
    </div>
  `;
}

function renderInfoPanel() {
  return `
    <aside class="panel">
      <div class="panel-header"><h2>${state.screen === "result" ? "结算" : "战斗记录"}</h2></div>
      <div class="panel-body stack">
        ${state.screen === "result" ? renderResult() : ""}
        <div>
          <div class="section-title">下一波预览</div>
          <div class="row-card" style="margin-top:8px">
            <div class="row-title">${currentWave()?.name ?? "已完成"}</div>
            <div class="muted">${currentWave()?.preview ?? "没有下一波。"}</div>
          </div>
        </div>
        <div>
          <div class="section-title">已选战备</div>
          <div class="prep-list" style="margin-top:8px">
            ${state.chosenPreps.length ? state.chosenPreps.map((prep) => `<div class="row-card"><div class="row-title">${prep.name}</div><div class="muted">${prep.text}</div></div>`).join("") : `<div class="muted">暂无</div>`}
          </div>
        </div>
        <div>
          <div class="section-title">日志</div>
          <div class="log" style="margin-top:8px">
            ${state.logs.map((entry) => `<div class="log-entry">${entry}</div>`).join("")}
          </div>
        </div>
      </div>
    </aside>
  `;
}

function renderResult() {
  const win = state.result === "win";
  return `
    <div class="result-banner ${win ? "" : "fail"}">
      <div class="row-title">${win ? "难度通关" : "挑战失败"}</div>
      <div class="muted">${win ? "完成全部波次，可进入通关奖励和解锁流程。" : "我方全灭，失败不触发通关奖励。"}</div>
    </div>
    <div class="screen-actions">
      <button class="primary" onclick="actions.reset()">返回配置</button>
      <button onclick="actions.startChallenge()">再来一局</button>
    </div>
  `;
}

function renderPrepOverlay() {
  if (!state.pendingNextWave) return "";
  const nextWave = currentDifficulty().waves[state.waveIndex + 1];
  return `
    <div class="prep-overlay">
      <div class="prep-dialog">
        <div class="panel-header">
          <h2>备战抉择</h2>
          <div class="muted">下一波：${nextWave.name}。${nextWave.preview}</div>
        </div>
        <div class="panel-body">
          <div class="prep-grid">
            ${state.prepChoices
              .map(
                (prep) => `
                <button class="row-card prep-card" onclick="actions.choosePrep('${prep.id}')">
                  <div>
                    <div class="row-title">${prep.name}</div>
                    ${renderTags(prep.tags)}
                    <p class="muted">${prep.text}</p>
                  </div>
                  <span class="muted">选择后本局继承</span>
                </button>
              `,
              )
              .join("")}
          </div>
        </div>
      </div>
    </div>
  `;
}

function render() {
  app.innerHTML = `
    <div class="app-shell">
      <header class="topbar">
        <div class="brand">
          <h1>三国斗阵</h1>
          <span>Web 参考原型 v0.1</span>
        </div>
        <div class="muted">单线自动推线 / 波次后战备 3 选 1 / 2 人位验证</div>
      </header>
      <div class="layout">
        ${renderSetupPanel()}
        ${renderBattlefield()}
        ${state.screen === "setup" ? renderHeroPanel() : renderInfoPanel()}
      </div>
      ${renderPrepOverlay()}
    </div>
  `;
}

window.actions = {
  startChallenge,
  setDifficulty,
  toggleHero,
  toggleSkill,
  choosePrep,
  reset,
  pause: () => {
    state.running = false;
    render();
  },
  resume: () => {
    state.running = true;
    startLoop();
    render();
  },
};

render();
