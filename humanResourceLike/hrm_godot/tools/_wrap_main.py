import pathlib
p = pathlib.Path('scripts/main.gd')
s = p.read_text(encoding='utf-8')

P = [
 # ---- 载入/撤销
 ('\t\t\tlbl_status.text = "levels.json 读取失败，保留原数据"',
  '\t\t\tlbl_status.text = I18n.t("levels.json 读取失败，保留原数据")'),
 ('\t\tlbl_status.text = "已重新载入 %d 关 · 进度保留" % levels.size()',
  '\t\tlbl_status.text = I18n.tf("已重新载入 %d 关 · 进度保留", [levels.size()])'),
 ('\t\tlbl_status.text = "没有可撤销的操作"',
  '\t\tlbl_status.text = I18n.t("没有可撤销的操作")'),
 # ---- 拖拽提示
 ('\t\tlbl_insert_hint.text = "拖到列表任意位置放下 —— 会自动让出空隙"',
  '\t\tlbl_insert_hint.text = I18n.t("拖到列表任意位置放下 —— 会自动让出空隙")'),
 ('\tl.text = "第 %d 行" % (_press_from + 1)',
  '\tl.text = I18n.tf("第 %d 行", [_press_from + 1])'),
 ('\t\t\tlbl_insert_hint.text = "拖到列表里放下（Esc 取消）"',
  '\t\t\tlbl_insert_hint.text = I18n.t("拖到列表里放下（Esc 取消）")'),
 ('\t_gap.label = "放这里"', '\t_gap.label = I18n.t("放这里")'),
 ('\t\tlbl_insert_hint.text = "松手 → 插到第 %d 行" % (idx + 1)',
  '\t\tlbl_insert_hint.text = I18n.tf("松手 → 插到第 %d 行", [idx + 1])'),
 # ---- 结算卡
 ('\twin_title.text = "数完啦！" if bool(info.get("first", false)) else "又数完啦"',
  '\twin_title.text = I18n.t("数完啦！") if bool(info.get("first", false)) else I18n.t("又数完啦")'),
 ('\twin_sub.text = "第 %d 关 · %s" % [int(level.get("id", 0)), String(level.get("cn", ""))]',
  '\twin_sub.text = I18n.tf("第 %d 关 · %s", [int(level.get("id", 0)), I18n.level_name(level)])'),
 ('\t\tbadge = "★  首次通关"', '\t\tbadge = I18n.t("★  首次通关")'),
 ('\t\tbadge = "★  新纪录：指令更快"', '\t\tbadge = I18n.t("★  新纪录：指令更快")'),
 ('\t\tbadge = "★  指令数破纪录"', '\t\tbadge = I18n.t("★  指令数破纪录")'),
 ('\t\tbadge = "★  速度破纪录"', '\t\tbadge = I18n.t("★  速度破纪录")'),
 ('\t\tbadge = "看过解法 · 成绩不计入手写榜"', '\t\tbadge = I18n.t("看过解法 · 成绩不计入手写榜")'),
 ('\twin_next_btn.text = "回到第 1 关" if li + 1 >= levels.size() else "下一关  →"',
  '\twin_next_btn.text = I18n.t("回到第 1 关") if li + 1 >= levels.size() else I18n.t("下一关  →")'),
 # ---- 抬头
 ('\tbtn_level.tooltip_text = "牧场地图：点开选关"', '\tbtn_level.tooltip_text = I18n.t("牧场地图：点开选关")'),
 ('\tstars.tooltip_text = "过关得一颗；指令数与周期各达标再各得一颗"',
  '\tstars.tooltip_text = I18n.t("过关得一颗；指令数与周期各达标再各得一颗")'),
 # ---- 指令面板
 ('\tbtn_doc.tooltip_text = "把本关能用的指令牌逐个讲一遍（F1）"',
  '\tbtn_doc.tooltip_text = I18n.t("把本关能用的指令牌逐个讲一遍（F1）")'),
 ('\tb_clear.tooltip_text = "清空整段程序（可 Ctrl+Z 撤销）"',
  '\tb_clear.tooltip_text = I18n.t("清空整段程序（可 Ctrl+Z 撤销）")'),
 ('\tlbl_best.tooltip_text = "你在本关的最好成绩"', '\tlbl_best.tooltip_text = I18n.t("你在本关的最好成绩")'),
 ('\tp.tooltip_text = caption', '\tp.tooltip_text = I18n.t(caption)'),
 # ---- 地图浮层
 ('\t\tbtn_map_go.text = "先点一块地"', '\t\tbtn_map_go.text = I18n.t("先点一块地")'),
 ('\t\tbtn_map_go.text = "第 %d 关就是这儿 · 收起" % no',
  '\t\tbtn_map_go.text = I18n.tf("第 %d 关就是这儿 · 收起", [no])'),
 ('\t\tbtn_map_go.text = "进入第 %d 关 ›" % no',
  '\t\tbtn_map_go.text = I18n.tf("进入第 %d 关 ›", [no])'),
 ('\t\tlbl_levels_title.text = "通关 %d / %d" % [n_clear, levels.size()]',
  '\t\tlbl_levels_title.text = I18n.tf("通关 %d / %d", [n_clear, levels.size()])'),
 # ---- 关卡静态文案
 ('\t\treturn "（无）"', '\t\treturn I18n.t("（无）")'),
 ('\tlbl_level_name.text = "%s  ·  %s" % [\n\t\tString(level.get("name", "")), String(level.get("cn", ""))\n\t]',
  '\t# 英文版关名本来就叫 First Sheep，后面再挂一个中文括号是废话 —— 只给一个。\n'
  '\tvar nm: String = String(level.get("name", ""))\n'
  '\tlbl_level_name.text = nm if I18n.locale == "en" else "%s  ·  %s" % [nm, I18n.level_name(level)]'),
 # ---- 提示
 ('\t\tlbl_status.text = "再想 %d 秒，实在卡住再点我" % left',
  '\t\tlbl_status.text = I18n.tf("再想 %d 秒，实在卡住再点我", [left])'),
 ('\t\tlbl_status.text = "已填入参考解 · 这关记为「参考答案」"',
  '\t\tlbl_status.text = I18n.t("已填入参考解 · 这关记为「参考答案」")'),
 ('\t\t\tbtn_hint.text = "卡住了？看提示"', '\t\t\tbtn_hint.text = I18n.t("卡住了？看提示")'),
 ('\t\t\ttxt = "思路：" + String(level.get("hint", "（这关没有写提示）"))',
  '\t\t\tvar h1: String = String(level.get("hint", ""))\n'
  '\t\t\ttxt = I18n.t("思路：") + (I18n.t(h1) if h1 != "" else I18n.t("（这关没有写提示）"))'),
 ('\t\t\tbtn_hint.text = "还是不懂 · 再具体点"', '\t\t\tbtn_hint.text = I18n.t("还是不懂 · 再具体点")'),
 ('\t\t\ttxt = "思路：%s\\n关键做法：%s" % [\n\t\t\t\tString(level.get("hint", "")), String(level.get("hint2", ""))\n\t\t\t]',
  '\t\t\ttxt = I18n.tf("思路：%s\\n关键做法：%s", [\n'
  '\t\t\t\tI18n.t(String(level.get("hint", ""))), I18n.t(String(level.get("hint2", "")))\n\t\t\t])'),
 ('\t\t\tbtn_hint.text = "直接看参考解"', '\t\t\tbtn_hint.text = I18n.t("直接看参考解")'),
 ('\t\t\ttxt = "已填入参考解。看每行右边那行小字——那就是它在干什么；鼠标停在任意一行上，下面的说明条会讲清这一句。"',
  '\t\t\ttxt = I18n.t("已填入参考解。看每行右边那行小字——那就是它在干什么；鼠标停在任意一行上，下面的说明条会讲清这一句。")'),
 ('\t\t\tbtn_hint.text = "已给出参考解"', '\t\t\tbtn_hint.text = I18n.t("已给出参考解")'),
 ('\t\tbtn_hint.tooltip_text = "先自己想 %d 秒，实在卡住再点" % left',
  '\t\tbtn_hint.tooltip_text = I18n.tf("先自己想 %d 秒，实在卡住再点", [left])'),
 ('\t\tbtn_hint.tooltip_text = "现在可以看了"', '\t\tbtn_hint.tooltip_text = I18n.t("现在可以看了")'),
 # ---- 指令牌 / 说明条
 ('\tcard.tooltip_text = "%s · %s\\n点一下追加到末尾 / 按住拖到任意行之间" % [op, HrmVM.op_help(op)]',
  '\tcard.tooltip_text = I18n.tf("%s · %s\\n点一下追加到末尾 / 按住拖到任意行之间", [op, HrmVM.op_help(op)])'),
 ('\t\tlbl_op_help.text = "没有单独的「比较」牌：JUMPZ / JUMPN 就是比较 —— 看一眼手上的数，成立就跳。"',
  '\t\tlbl_op_help.text = I18n.t("没有单独的「比较」牌：JUMPZ / JUMPN 就是比较 —— 看一眼手上的数，成立就跳。")'),
 ('\t\tlbl_op_help.text = "鼠标停在指令牌或程序行上，这里会解释它做什么。"',
  '\t\tlbl_op_help.text = I18n.t("鼠标停在指令牌或程序行上，这里会解释它做什么。")'),
 # ---- 说明书标题
 ('\thead.add_child(_label("第 %d 关 · %s" % [int(level.get("id", 0)), String(level.get("cn", ""))],',
  '\thead.add_child(_label(I18n.tf("第 %d 关 · %s", [int(level.get("id", 0)), I18n.level_name(level)]),'),
 # ---- 插入提示（第二处）
 ('\t\tlbl_insert_hint.text = "未选中行 · 指令会追加到末尾"',
  '\t\tlbl_insert_hint.text = I18n.t("未选中行 · 指令会追加到末尾")'),
 ('\t\tlbl_insert_hint.text = "已选第 %d 行 · 新指令插到第 %d 行" % [sel + 1, sel + 2]',
  '\t\tlbl_insert_hint.text = I18n.tf("已选第 %d 行 · 新指令插到第 %d 行", [sel + 1, sel + 2])'),
 # ---- 行内控件
 ('\tb.tooltip_text = "标签：点一下循环切换  无 → a → b → c → d\\nJUMP a / JUMP b 就是跳到标签为 a / b 的那一行"',
  '\tb.tooltip_text = I18n.t("标签：点一下循环切换  无 → a → b → c → d\\nJUMP a / JUMP b 就是跳到标签为 a / b 的那一行")'),
 ('\tspacer.tooltip_text = "按住拖动 = 滚动"', '\tspacer.tooltip_text = I18n.t("按住拖动 = 滚动")'),
 # ---- 运行状态
 ('\t\tlbl_cycles.tooltip_text = "%d 个周期处理 %d 件，摊到每件 %.2f 周期" % [',
  '\t\tlbl_cycles.tooltip_text = I18n.tf("%d 个周期处理 %d 件，摊到每件 %.2f 周期", ['),
 ('\t\tlbl_cycles.tooltip_text = "还没有处理过任何一件"',
  '\t\tlbl_cycles.tooltip_text = I18n.t("还没有处理过任何一件")'),
 ('\t\tlbl_best.text = "最佳 %d · %.1f" % [int(rec.get("size", 0)), float(rec.get("speed", 0.0))]',
  '\t\tlbl_best.text = I18n.tf("最佳 %d · %.1f", [int(rec.get("size", 0)), float(rec.get("speed", 0.0))])'),
 ('\t\tlbl_status.text = "● 任务完成"', '\t\tlbl_status.text = I18n.t("● 任务完成")'),
 ('\t\tlbl_status.text = "● 运行中…" if playing else "● 就绪"',
  '\t\tlbl_status.text = I18n.t("● 运行中…") if playing else I18n.t("● 就绪")'),
 ('\t\tbtn_run.text = "■  暂停" if playing else "▶  运行"',
  '\t\tbtn_run.text = I18n.t("■  暂停") if playing else I18n.t("▶  运行")'),
]

bad = []
for old, new in P:
    n = s.count(old)
    if n != 1:
        bad.append((n, old[:50]))
        continue
    s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('替换', len(P) - len(bad), '/', len(P))
for n, o in bad:
    print('命中', n, '次:', o)
