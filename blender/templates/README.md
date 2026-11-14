# 新场景的最小记录模板

在 `scenes/<SceneName>/` 建新目录，把这里的三个 Markdown 文件复制进去填写。先完成根目录 AGENTS 的学习，再开始搭建。文件是任务记录，内容应随着实际工作更新。

- [scene_brief.md](scene_brief.md)：目标、观察、假设、布局与验收范围。
- [work_state.md](work_state.md)：已读资料、经验落实、检查点、状态与下一步。
- [visual_review.md](visual_review.md)：每阶段实际预览和对照判断。

空间数值单独写 `scene_spec.json`，避免在这里复制一份会漂移的坐标表。JSON 应注明单位/轴向、主要对象的中心尺寸、支撑关系、地面高程、相机和未知项；写完用解析器检查格式，再与白模核对。未知值用明确状态表示，不把猜测写成测量事实。
