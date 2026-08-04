import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const sourceDir = path.join(root, "deliverables", "config-file");
const outputDir = path.join(root, "outputs", "stage1-monster-config-v0.1");
const previewDir = path.join(root, ".tmp", "config_sheet_work", "previews");
const deploymentFile = "config_关卡怪物部署表-关卡1-出怪表.xlsx";
const unitFile = "config_单位列表.xlsx";

const unit = {
  forceCaptain: 134222862,
  meleeSoldier: 134258132,
  rangedSoldier: 134224536,
  lvBu: 134235305,
  zhangFei: 134270097,
  lvMeng: 134235416,
  huangZhong: 134230636,
  zhugeLiang: 134268516,
  zhaoYun: 134229701,
  liuBei: 134245859,
  xiaHouDun: 134236938,
  simaYi: 134262145,
  ganNing: 134232125,
};

const tag = (tier) => `难度${tier}`;
const squad = (leader, slot, tier, soldier, count) => ({ leader, slot, tier: tag(tier), soldier, count });
const force = (slot, soldier, count) => squad(unit.forceCaptain, slot, 1, soldier, count);

// Each difficulty adds exactly one wave. Enemy count and team complexity grow more slowly than wave count.
const legacyWavesByDifficulty = [
  [
    [force(2, unit.meleeSoldier, 1)],
  ],
  [
    [force(2, unit.meleeSoldier, 1)],
    [force(2, unit.meleeSoldier, 2)],
  ],
  [
    [force(2, unit.meleeSoldier, 2)],
    [force(2, unit.rangedSoldier, 1)],
    [force(2, unit.meleeSoldier, 3)],
  ],
  [
    [force(2, unit.meleeSoldier, 2)],
    [force(2, unit.rangedSoldier, 2)],
    [force(2, unit.meleeSoldier, 3), force(8, unit.rangedSoldier, 1)],
    [squad(unit.zhangFei, 2, 1, unit.meleeSoldier, 2), force(8, unit.rangedSoldier, 2)],
  ],
  [
    [force(2, unit.meleeSoldier, 3)],
    [force(2, unit.meleeSoldier, 3), force(8, unit.rangedSoldier, 2)],
    [force(2, unit.meleeSoldier, 3), squad(unit.huangZhong, 8, 1, unit.rangedSoldier, 2)],
    [squad(unit.zhaoYun, 1, 1, unit.meleeSoldier, 2), force(3, unit.meleeSoldier, 3)],
    [squad(unit.zhangFei, 2, 1, unit.meleeSoldier, 3), squad(unit.huangZhong, 8, 1, unit.rangedSoldier, 2)],
  ],
  [
    [force(2, unit.meleeSoldier, 3), force(8, unit.rangedSoldier, 3)],
    [force(2, unit.meleeSoldier, 3), squad(unit.liuBei, 5, 1, unit.rangedSoldier, 2)],
    [squad(unit.xiaHouDun, 2, 1, unit.meleeSoldier, 3), squad(unit.huangZhong, 8, 1, unit.rangedSoldier, 3)],
    [squad(unit.zhaoYun, 1, 1, unit.meleeSoldier, 3), force(9, unit.rangedSoldier, 3)],
    [squad(unit.lvMeng, 3, 1, unit.meleeSoldier, 3), force(7, unit.rangedSoldier, 3)],
    [squad(unit.zhangFei, 2, 1, unit.meleeSoldier, 4), squad(unit.liuBei, 8, 1, unit.rangedSoldier, 3)],
  ],
  [
    [force(2, unit.meleeSoldier, 4), force(8, unit.rangedSoldier, 3)],
    [force(2, unit.meleeSoldier, 4), squad(unit.zhugeLiang, 5, 1, unit.rangedSoldier, 3)],
    [squad(unit.ganNing, 1, 1, unit.meleeSoldier, 3), squad(unit.huangZhong, 7, 1, unit.rangedSoldier, 3)],
    [squad(unit.lvMeng, 3, 1, unit.meleeSoldier, 3), squad(unit.zhaoYun, 9, 1, unit.meleeSoldier, 3)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 4), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 4)],
    [squad(unit.xiaHouDun, 1, 1, unit.meleeSoldier, 4), squad(unit.liuBei, 9, 1, unit.rangedSoldier, 3)],
    [squad(unit.lvBu, 2, 1, unit.meleeSoldier, 4), force(8, unit.rangedSoldier, 4)],
  ],
  [
    [force(2, unit.meleeSoldier, 4), force(8, unit.rangedSoldier, 4)],
    [force(2, unit.meleeSoldier, 4), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 3)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 4), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 4)],
    [squad(unit.simaYi, 1, 1, unit.rangedSoldier, 4), squad(unit.xiaHouDun, 7, 1, unit.meleeSoldier, 4)],
    [squad(unit.ganNing, 3, 1, unit.meleeSoldier, 4), squad(unit.huangZhong, 9, 2, unit.rangedSoldier, 4)],
    [squad(unit.lvMeng, 1, 2, unit.meleeSoldier, 4), squad(unit.zhaoYun, 3, 2, unit.meleeSoldier, 4)],
    [squad(unit.lvBu, 2, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 8, 2, unit.rangedSoldier, 4)],
    [squad(unit.lvBu, 2, 2, unit.meleeSoldier, 5), force(5, unit.meleeSoldier, 4), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 5)],
  ],
  [
    [force(2, unit.meleeSoldier, 5), force(8, unit.rangedSoldier, 4)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 5), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 4)],
    [squad(unit.xiaHouDun, 2, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 4), force(3, unit.meleeSoldier, 4)],
    [squad(unit.simaYi, 1, 2, unit.rangedSoldier, 4), force(2, unit.meleeSoldier, 5), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 5)],
    [squad(unit.lvMeng, 1, 2, unit.meleeSoldier, 4), squad(unit.ganNing, 3, 2, unit.meleeSoldier, 5), squad(unit.zhaoYun, 9, 2, unit.meleeSoldier, 4)],
    [squad(unit.lvBu, 2, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 4), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 1, 2, unit.meleeSoldier, 5), squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 5), squad(unit.zhugeLiang, 9, 2, unit.rangedSoldier, 5)],
    [squad(unit.simaYi, 1, 2, unit.rangedSoldier, 5), force(2, unit.meleeSoldier, 5), squad(unit.ganNing, 3, 2, unit.meleeSoldier, 5), squad(unit.lvMeng, 7, 2, unit.meleeSoldier, 4)],
    [squad(unit.lvBu, 2, 3, unit.meleeSoldier, 6), squad(unit.xiaHouDun, 3, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 5), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 5)],
  ],
  [
    [force(2, unit.meleeSoldier, 5), force(8, unit.rangedSoldier, 4)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 5), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 2, 2, unit.meleeSoldier, 5), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 4), squad(unit.liuBei, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.zhaoYun, 1, 2, unit.meleeSoldier, 5), squad(unit.lvMeng, 3, 2, unit.meleeSoldier, 5), squad(unit.ganNing, 8, 2, unit.meleeSoldier, 5)],
    [force(2, unit.meleeSoldier, 6), squad(unit.simaYi, 5, 2, unit.rangedSoldier, 5), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 6), squad(unit.liuBei, 5, 3, unit.rangedSoldier, 5), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 1, 3, unit.meleeSoldier, 6), squad(unit.zhaoYun, 2, 3, unit.meleeSoldier, 5), squad(unit.lvMeng, 3, 3, unit.meleeSoldier, 5), squad(unit.ganNing, 8, 3, unit.meleeSoldier, 5)],
    [force(1, unit.meleeSoldier, 5), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 6), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 5), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 5)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 6), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.xiaHouDun, 3, 3, unit.meleeSoldier, 6), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 6)],
    [squad(unit.ganNing, 1, 3, unit.meleeSoldier, 6), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.liuBei, 3, 3, unit.rangedSoldier, 5), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 6), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 6)],
  ],
];

// Difficulty 1 carries the complete first-time tutorial. Later difficulties extend the full encounter arc.
const wavesByDifficulty = [
  [
    [force(2, unit.meleeSoldier, 1)],
    [force(2, unit.meleeSoldier, 2)],
    [force(2, unit.rangedSoldier, 1)],
    [force(2, unit.meleeSoldier, 2), force(8, unit.rangedSoldier, 1)],
  ],
  [
    [force(2, unit.meleeSoldier, 2)],
    [force(2, unit.rangedSoldier, 2)],
    [force(2, unit.meleeSoldier, 3)],
    [force(2, unit.meleeSoldier, 3), force(8, unit.rangedSoldier, 2)],
    [squad(unit.zhangFei, 2, 1, unit.meleeSoldier, 2), force(8, unit.rangedSoldier, 2)],
  ],
  [
    [force(2, unit.meleeSoldier, 3)],
    [force(2, unit.meleeSoldier, 3), force(8, unit.rangedSoldier, 2)],
    [force(2, unit.meleeSoldier, 3), squad(unit.huangZhong, 8, 1, unit.rangedSoldier, 2)],
    [squad(unit.zhaoYun, 1, 1, unit.meleeSoldier, 2), force(3, unit.meleeSoldier, 3)],
    [squad(unit.zhangFei, 2, 1, unit.meleeSoldier, 3), squad(unit.huangZhong, 8, 1, unit.rangedSoldier, 2)],
    [squad(unit.xiaHouDun, 2, 1, unit.meleeSoldier, 3), squad(unit.liuBei, 8, 1, unit.rangedSoldier, 2)],
  ],
  [
    [force(2, unit.meleeSoldier, 3), force(8, unit.rangedSoldier, 3)],
    [force(2, unit.meleeSoldier, 3), squad(unit.liuBei, 5, 1, unit.rangedSoldier, 2)],
    [squad(unit.xiaHouDun, 2, 1, unit.meleeSoldier, 3), squad(unit.huangZhong, 8, 1, unit.rangedSoldier, 3)],
    [squad(unit.zhaoYun, 1, 1, unit.meleeSoldier, 3), force(9, unit.rangedSoldier, 3)],
    [squad(unit.lvMeng, 3, 1, unit.meleeSoldier, 3), force(7, unit.rangedSoldier, 3)],
    [squad(unit.zhangFei, 2, 1, unit.meleeSoldier, 4), squad(unit.liuBei, 8, 1, unit.rangedSoldier, 3)],
    [squad(unit.ganNing, 1, 1, unit.meleeSoldier, 3), squad(unit.huangZhong, 7, 1, unit.rangedSoldier, 3)],
  ],
  [
    [force(2, unit.meleeSoldier, 4), force(8, unit.rangedSoldier, 3)],
    [force(2, unit.meleeSoldier, 4), squad(unit.zhugeLiang, 5, 1, unit.rangedSoldier, 3)],
    [squad(unit.ganNing, 1, 1, unit.meleeSoldier, 3), squad(unit.huangZhong, 7, 1, unit.rangedSoldier, 3)],
    [squad(unit.lvMeng, 3, 1, unit.meleeSoldier, 3), squad(unit.zhaoYun, 9, 1, unit.meleeSoldier, 3)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 4), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 4)],
    [squad(unit.xiaHouDun, 1, 1, unit.meleeSoldier, 4), squad(unit.liuBei, 9, 1, unit.rangedSoldier, 3)],
    [squad(unit.lvBu, 2, 1, unit.meleeSoldier, 4), force(8, unit.rangedSoldier, 4)],
    [squad(unit.lvBu, 2, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 8, 2, unit.rangedSoldier, 4)],
  ],
  [
    [force(2, unit.meleeSoldier, 4), force(8, unit.rangedSoldier, 4)],
    [force(2, unit.meleeSoldier, 4), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 3)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 4), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 4)],
    [squad(unit.simaYi, 1, 1, unit.rangedSoldier, 4), squad(unit.xiaHouDun, 7, 1, unit.meleeSoldier, 4)],
    [squad(unit.ganNing, 3, 1, unit.meleeSoldier, 4), squad(unit.huangZhong, 9, 2, unit.rangedSoldier, 4)],
    [squad(unit.lvMeng, 1, 2, unit.meleeSoldier, 4), squad(unit.zhaoYun, 3, 2, unit.meleeSoldier, 4)],
    [squad(unit.lvBu, 2, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 8, 2, unit.rangedSoldier, 4)],
    [force(5, unit.meleeSoldier, 4), squad(unit.lvBu, 2, 2, unit.meleeSoldier, 5), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 1, 2, unit.meleeSoldier, 5), squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 5), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 5)],
  ],
  [
    [force(2, unit.meleeSoldier, 5), force(8, unit.rangedSoldier, 4)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 5), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 4)],
    [squad(unit.xiaHouDun, 2, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 4), force(3, unit.meleeSoldier, 4)],
    [squad(unit.simaYi, 1, 2, unit.rangedSoldier, 4), force(2, unit.meleeSoldier, 5), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 5)],
    [squad(unit.lvMeng, 1, 2, unit.meleeSoldier, 4), squad(unit.ganNing, 3, 2, unit.meleeSoldier, 5), squad(unit.zhaoYun, 9, 2, unit.meleeSoldier, 4)],
    [squad(unit.lvBu, 2, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 4), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 1, 2, unit.meleeSoldier, 5), squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 5), squad(unit.zhugeLiang, 9, 2, unit.rangedSoldier, 5)],
    [squad(unit.simaYi, 1, 2, unit.rangedSoldier, 5), force(2, unit.meleeSoldier, 5), squad(unit.ganNing, 3, 2, unit.meleeSoldier, 5), squad(unit.lvMeng, 7, 2, unit.meleeSoldier, 4)],
    [squad(unit.lvBu, 2, 3, unit.meleeSoldier, 6), squad(unit.xiaHouDun, 3, 2, unit.meleeSoldier, 5), squad(unit.liuBei, 5, 2, unit.rangedSoldier, 5), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.zhangFei, 1, 2, unit.meleeSoldier, 5), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 6), squad(unit.simaYi, 5, 2, unit.rangedSoldier, 5), squad(unit.huangZhong, 7, 2, unit.rangedSoldier, 5)],
  ],
  [
    [force(2, unit.meleeSoldier, 5), force(8, unit.rangedSoldier, 4)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 5), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 2, 2, unit.meleeSoldier, 5), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 4), squad(unit.liuBei, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.zhaoYun, 1, 2, unit.meleeSoldier, 5), squad(unit.lvMeng, 3, 2, unit.meleeSoldier, 5), squad(unit.ganNing, 8, 2, unit.meleeSoldier, 5)],
    [force(2, unit.meleeSoldier, 6), squad(unit.simaYi, 5, 2, unit.rangedSoldier, 5), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 6), squad(unit.liuBei, 5, 3, unit.rangedSoldier, 5), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 1, 3, unit.meleeSoldier, 6), squad(unit.zhaoYun, 2, 3, unit.meleeSoldier, 5), squad(unit.lvMeng, 3, 3, unit.meleeSoldier, 5), squad(unit.ganNing, 8, 3, unit.meleeSoldier, 5)],
    [force(1, unit.meleeSoldier, 5), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 6), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 5), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 5)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 6), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.xiaHouDun, 3, 3, unit.meleeSoldier, 6), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 6)],
    [squad(unit.ganNing, 1, 3, unit.meleeSoldier, 6), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.liuBei, 3, 3, unit.rangedSoldier, 5), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 6), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 6)],
    [squad(unit.xiaHouDun, 1, 3, unit.meleeSoldier, 6), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.zhangFei, 3, 3, unit.meleeSoldier, 6), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 6), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 6)],
  ],
  [
    [force(2, unit.meleeSoldier, 6), force(8, unit.rangedSoldier, 5)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 6), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 2, 2, unit.meleeSoldier, 6), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 5), squad(unit.liuBei, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.zhaoYun, 1, 2, unit.meleeSoldier, 6), squad(unit.lvMeng, 3, 2, unit.meleeSoldier, 5), squad(unit.ganNing, 8, 2, unit.meleeSoldier, 5)],
    [force(2, unit.meleeSoldier, 6), squad(unit.simaYi, 5, 2, unit.rangedSoldier, 6), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 6)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 6), squad(unit.liuBei, 5, 3, unit.rangedSoldier, 6), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 6)],
    [squad(unit.xiaHouDun, 1, 3, unit.meleeSoldier, 6), squad(unit.zhaoYun, 2, 3, unit.meleeSoldier, 6), squad(unit.lvMeng, 3, 3, unit.meleeSoldier, 6), squad(unit.ganNing, 8, 3, unit.meleeSoldier, 6)],
    [force(1, unit.meleeSoldier, 6), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 6), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 6)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.xiaHouDun, 3, 3, unit.meleeSoldier, 7), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 7)],
    [squad(unit.ganNing, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.liuBei, 3, 3, unit.rangedSoldier, 6), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 7), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 7)],
    [squad(unit.xiaHouDun, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.zhangFei, 3, 3, unit.meleeSoldier, 7), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 7), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 7)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.ganNing, 3, 3, unit.meleeSoldier, 7), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 7), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 7)],
  ],
  [
    [force(2, unit.meleeSoldier, 6), force(8, unit.rangedSoldier, 5)],
    [squad(unit.zhangFei, 2, 2, unit.meleeSoldier, 6), squad(unit.huangZhong, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.xiaHouDun, 2, 2, unit.meleeSoldier, 6), squad(unit.zhugeLiang, 5, 2, unit.rangedSoldier, 5), squad(unit.liuBei, 8, 2, unit.rangedSoldier, 5)],
    [squad(unit.zhaoYun, 1, 2, unit.meleeSoldier, 6), squad(unit.lvMeng, 3, 2, unit.meleeSoldier, 5), squad(unit.ganNing, 8, 2, unit.meleeSoldier, 5)],
    [force(2, unit.meleeSoldier, 6), squad(unit.simaYi, 5, 2, unit.rangedSoldier, 6), squad(unit.zhugeLiang, 8, 2, unit.rangedSoldier, 6)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 7), squad(unit.liuBei, 5, 3, unit.rangedSoldier, 6), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 6)],
    [squad(unit.xiaHouDun, 1, 3, unit.meleeSoldier, 7), squad(unit.zhaoYun, 2, 3, unit.meleeSoldier, 6), squad(unit.lvMeng, 3, 3, unit.meleeSoldier, 6), squad(unit.ganNing, 8, 3, unit.meleeSoldier, 6)],
    [force(1, unit.meleeSoldier, 6), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 7), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 6), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 6)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.xiaHouDun, 3, 3, unit.meleeSoldier, 7), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 7)],
    [squad(unit.ganNing, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.liuBei, 3, 3, unit.rangedSoldier, 6), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 7), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 7)],
    [squad(unit.xiaHouDun, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.zhangFei, 3, 3, unit.meleeSoldier, 7), squad(unit.huangZhong, 7, 3, unit.rangedSoldier, 7), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 7)],
    [squad(unit.ganNing, 1, 3, unit.meleeSoldier, 7), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.zhangFei, 3, 3, unit.meleeSoldier, 8), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 8), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 8)],
    [squad(unit.zhangFei, 1, 3, unit.meleeSoldier, 8), squad(unit.lvBu, 2, 3, unit.meleeSoldier, 8), squad(unit.huangZhong, 3, 3, unit.rangedSoldier, 8), squad(unit.simaYi, 5, 3, unit.rangedSoldier, 8), squad(unit.ganNing, 7, 3, unit.meleeSoldier, 7), squad(unit.zhugeLiang, 8, 3, unit.rangedSoldier, 8)],
  ],
];

const validLeaders = new Set([
  unit.forceCaptain, unit.lvBu, unit.zhangFei, unit.lvMeng, unit.huangZhong, unit.zhugeLiang,
  unit.zhaoYun, unit.liuBei, unit.xiaHouDun, unit.simaYi, unit.ganNing,
]);
const validSoldiers = new Set([unit.meleeSoldier, unit.rangedSoldier]);

const waves = [];
wavesByDifficulty.forEach((difficultyWaves, difficultyIndex) => {
  const difficulty = difficultyIndex + 1;
  const expectedWaveCount = difficulty + 3;
  if (difficultyWaves.length !== expectedWaveCount) {
    throw new Error(`Difficulty ${difficulty} requires ${expectedWaveCount} waves, received ${difficultyWaves.length}.`);
  }
  difficultyWaves.forEach((groups, waveIndex) => {
    if (groups.length < 1 || groups.length > 9) {
      throw new Error(`Difficulty ${difficulty}, wave ${waveIndex + 1} has an invalid squad count.`);
    }
    const usedSlots = new Set();
    groups.forEach((group) => {
      if (!validLeaders.has(group.leader) || !validSoldiers.has(group.soldier)) {
        throw new Error(`Difficulty ${difficulty}, wave ${waveIndex + 1} references an unknown unit type.`);
      }
      if (group.slot < 1 || group.slot > 9 || usedSlots.has(group.slot)) {
        throw new Error(`Difficulty ${difficulty}, wave ${waveIndex + 1} has invalid or duplicate grid slots.`);
      }
      if (group.count < 1 || group.count > 8) {
        throw new Error(`Difficulty ${difficulty}, wave ${waveIndex + 1} exceeds the per-squad soldier limit.`);
      }
      usedSlots.add(group.slot);
    });
    waves.push({ difficulty, wave: waveIndex + 1, groups });
  });
});

if (waves.length !== 85) {
  throw new Error(`Expected 85 wave rows, received ${waves.length}.`);
}

function buildHeaders() {
  const header = ["key", "关卡难度", "波次", "区域名称（说明）", "tips", "是否已刷新"];
  const types = ["int", "int", "int", "string", "string", "bool"];
  const keyRow = ["key1", null, null, null, null, null];
  for (let index = 1; index <= 9; index += 1) {
    header.push(`怪物队长${index}`, `队长${index}站位编号`, `怪物队长${index}-难度标签`, `怪物${index}`, `怪物${index}-数量`);
    types.push("unit_type", "int", "string", "unit_type", "int");
    keyRow.push(null, null, null, null, null);
  }
  return { header, types, keyRow };
}

function buildWaveRow(key, wave) {
  const row = [key, wave.difficulty, wave.wave, `第${wave.wave}波`, "111", false];
  for (let index = 0; index < 9; index += 1) {
    const group = wave.groups[index];
    row.push(...(group ? [group.leader, group.slot, group.tier, group.soldier, group.count] : [0, 1, tag(1), 0, 0]));
  }
  return row;
}

function columnName(columnNumber) {
  let number = columnNumber;
  let name = "";
  while (number > 0) {
    const remainder = (number - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    number = Math.floor((number - 1) / 26);
  }
  return name;
}

function setDeploymentLayout(sheet, finalRow) {
  const fixedWidths = [8, 10, 8, 16, 8, 10];
  fixedWidths.forEach((width, index) => {
    const column = columnName(index + 1);
    sheet.getRange(`${column}2:${column}${finalRow}`).format.columnWidth = width;
  });

  for (let squadIndex = 0; squadIndex < 9; squadIndex += 1) {
    const startColumn = 7 + squadIndex * 5;
    const widths = [15, 11, 13, 15, 10];
    widths.forEach((width, columnOffset) => {
      const column = columnName(startColumn + columnOffset);
      sheet.getRange(`${column}2:${column}${finalRow}`).format.columnWidth = width;
    });
  }

  sheet.getRange("A2:AY2").format.wrapText = true;
  sheet.getRange("A2:AY2").format.rowHeight = 30;
}

async function loadWorkbook(fileName) {
  return SpreadsheetFile.importXlsx(await FileBlob.load(path.join(sourceDir, fileName)));
}

async function exportAndSync(workbook, fileName) {
  const exported = await SpreadsheetFile.exportXlsx(workbook);
  const outputPath = path.join(outputDir, fileName);
  await exported.save(outputPath);
  await fs.copyFile(outputPath, path.join(sourceDir, fileName));
}

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const deploymentWorkbook = await loadWorkbook(deploymentFile);
const deploymentSheet = deploymentWorkbook.worksheets.getItemAt(0);
const { header, types, keyRow } = buildHeaders();
const rowMatrix = waves.map((wave, index) => buildWaveRow(index + 1, wave));
const finalRow = 4 + rowMatrix.length;

deploymentSheet.getRange(`A2:AY${finalRow}`).clear({ applyTo: "contents" });
deploymentSheet.getRange("A2:AY2").values = [header];
deploymentSheet.getRange("A3:AY3").values = [types];
deploymentSheet.getRange("A4:AY4").values = [keyRow];
deploymentSheet.getRange(`A5:AY${finalRow}`).values = rowMatrix;
setDeploymentLayout(deploymentSheet, finalRow);

const deploymentCheck = await deploymentWorkbook.inspect({
  kind: "region",
  sheetId: deploymentSheet.name,
  range: `A2:AY${finalRow}`,
  maxChars: 8000,
  tableMaxRows: 8,
  tableMaxCols: 51,
  tableMaxCellChars: 80,
});
console.log(`DEPLOYMENT_CHECK\n${deploymentCheck.ndjson}`);

for (const [name, range] of [["deployment-top", "A1:AY12"], ["deployment-bottom", "A80:AY89"]]) {
  const preview = await deploymentWorkbook.render({ sheetName: deploymentSheet.name, range, scale: 1.2, format: "png" });
  await fs.writeFile(path.join(previewDir, `${name}.png`), new Uint8Array(await preview.arrayBuffer()));
}
await exportAndSync(deploymentWorkbook, deploymentFile);

const unitWorkbook = await loadWorkbook(unitFile);
const unitSheet = unitWorkbook.worksheets.getItemAt(0);
unitSheet.getRange("D10").values = [["力士"]];
unitSheet.getRange("O11:O20").values = Array.from({ length: 10 }, () => [60]);

const unitCheck = await unitWorkbook.inspect({
  kind: "region",
  sheetId: unitSheet.name,
  range: "A8:S20",
  maxChars: 7000,
  tableMaxRows: 20,
  tableMaxCols: 19,
  tableMaxCellChars: 80,
});
console.log(`UNIT_CHECK\n${unitCheck.ndjson}`);

const unitPreview = await unitWorkbook.render({ sheetName: unitSheet.name, range: "A1:S20", scale: 1.5, format: "png" });
await fs.writeFile(path.join(previewDir, "unit-list.png"), new Uint8Array(await unitPreview.arrayBuffer()));
await exportAndSync(unitWorkbook, unitFile);

const finalDeploymentWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(outputDir, deploymentFile)));
const finalDeploymentSheet = finalDeploymentWorkbook.worksheets.getItemAt(0);
const finalDeploymentCheck = await finalDeploymentWorkbook.inspect({
  kind: "region,match",
  sheetId: finalDeploymentSheet.name,
  range: "A80:AY89",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  maxChars: 7000,
  tableMaxRows: 12,
  tableMaxCols: 51,
  tableMaxCellChars: 80,
});
console.log(`FINAL_DEPLOYMENT_CHECK\n${finalDeploymentCheck.ndjson}`);

const finalUnitWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(outputDir, unitFile)));
const finalUnitSheet = finalUnitWorkbook.worksheets.getItemAt(0);
const finalUnitCheck = await finalUnitWorkbook.inspect({
  kind: "region,match",
  sheetId: finalUnitSheet.name,
  range: "A8:S20",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  maxChars: 7000,
  tableMaxRows: 20,
  tableMaxCols: 19,
  tableMaxCellChars: 80,
});
console.log(`FINAL_UNIT_CHECK\n${finalUnitCheck.ndjson}`);

const finalDeploymentPreview = await finalDeploymentWorkbook.render({
  sheetName: finalDeploymentSheet.name,
  range: "A80:AY89",
  scale: 1.2,
  format: "png",
});
await fs.writeFile(path.join(previewDir, "deployment-final-bottom.png"), new Uint8Array(await finalDeploymentPreview.arrayBuffer()));
