# 战斗胜负插屏提示

最终资源在 `transparent/`，均为透明 PNG。`source/` 是抠图前的绿色底源图，不参与游戏使用。

## 胜利

从底到顶：

1. `victory_gold_ring.png`：屏幕中心，先由 80% 缩放至 105%，再回落至 100%。
2. `title_battle_victory.png`：位于圆印中心，在圆印落下后 0.06 秒出现。
3. `victory_gold_flecks.png`：覆盖在最上层，短暂向外扩散并淡出。

建议总时长 0.85-1.05 秒：圆印顿入，标题落字，飞屑外散，所有层同步淡出。

## 失败

从底到顶：

1. `defeat_vermilion_stroke.png`：屏幕中心纵向拉开，从顶部快速落入。
2. `defeat_fissures_ash.png`：与竖痕撞击点对齐，在竖痕落下后 0.08 秒出现。
3. `title_battle_defeat.png`：位于裂痕中央，随后缓慢向下淡出。

建议总时长 0.8-1.0 秒：竖痕劈落，裂墨出现，标题落下，裂墨与竖痕向下渗散。
