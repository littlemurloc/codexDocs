# 备战阶段插屏提示

最终资源位于 `transparent/`，均为带 Alpha 通道的 PNG；`source/` 仅保留抠图前的绿色底源图，不参与游戏使用。

拼接顺序（从底到顶）：

1. `ink_exit_trail.png`：置于中心偏右，作为墨迹的拉长尾迹。
2. `ink_main.png`：置于屏幕中央，作为主墨痕底板。
3. `ink_entry_splatter.png`：从左下向中心爆开，可在入场时短暂出现。
4. `title_beizhan.png`：置于主墨痕中央。
5. `seal_vermilion.png`：置于标题左下附近，尺寸约为单个文字高度的 18%-25%。

同一套墨痕可直接替换为 `title_battle_start.png`，用于“战斗开始”提示。

建议演出：甩墨和主墨痕快速入场，标题随后短促落下；停留约 0.7 秒，再让标题淡出、墨迹与尾迹向右散开。
