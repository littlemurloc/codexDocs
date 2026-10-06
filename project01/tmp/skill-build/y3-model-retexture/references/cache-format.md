# 本次观察到的缓存格式与脚本

这是本机样本的解码方法，不是官方通用格式规范。缓存、版本或格式不匹配时停止该解码路径，改用导出资源或用户提供的原图。

## 名称与材质

`resource.repository` 样本以 `CCCCZZZ4` 开头：`ZZZ4` 后为 little-endian 32 位解压尺寸及 LZ4 block。材质文件的包装是 `ZZZ4`，解压后以 `.MESSIAH` 开头。仓库中的候选记录表现为 16 字节 GUID、16 位字符串长度、ASCII 名称；GUID 用原字节顺序转带连字符的字符串，缓存文件通常位于 `<GUID前两位>/<GUID>[.类型后缀]`。

名称扫描是启发式候选查找，必须再用材质 `tBaseMap` 核对颜色图。`tNormalMap`、`tSpecMap`、`tMixMap` 分别是本样本中其他贴图引用；不能只看文件名后缀推断用途。

旧临时脚本曾把已达到声明长度后的尾部继续当 LZ4 offset 读取，产生多出 4 字节的结果。新版脚本在 literal 已达到声明长度时结束，不再解读尾部。仓库、材质和贴图均严格检查解码长度，不能沿用旧临时脚本的静默截断；名称扫描仍不等于完整解析仓库结构。

## 纹理容器

本样本 `.6` 文件是引擎纹理容器，并非可直接改名为 PNG 的图片。观察到的结构：

- 前五字节 `02 02 02 01 01`；第六字节 `12` 的本样本是 BC1，`14` 的本样本是 BC3。其他值脚本拒绝。
- 从偏移 40 开始，逐 mip 头 `<IHHHHI`：总记录长度、宽、高、depth、row、解压数据长度；本脚本仅支持 depth 0 的二维图。
- mip 头后 `NNNN` 表示后面的原始 BC block；`ZZZ4` 表示 LZ4 包装。
- 按块数量校验数据长度：`ceil(width/4) × ceil(height/4) × blockBytes`；BC1 为 8 字节，BC3 为 16 字节。
- 取面积最大的 mip，封装标准 DDS，交给 Pillow 解码为 PNG。原始 Alpha 通过解码图检测，不靠“BC1”标签推断。

## 命令用法

以下路径均由当前项目和实际安装位置替换；PowerShell 中 `$texturePython` 使用当前发现的 Python 路径，`$textureScript` 指向本 skill 的脚本。需要 Pillow，仅用于解码、尺寸规范化和元数据检查；艺术重绘使用内置 imagegen。

```powershell
$textureScript = '<skill目录>/scripts/y3_texture.py'
& $texturePython $textureScript repository --source '<缓存>/resource.repository' --query 504061
& $texturePython $textureScript material --source '<缓存>/2b/2baa7546-56cc-ac44-2c7d-bffcefd58b5b'
& $texturePython $textureScript extract --source '<缓存>/01/0124172b-8d30-d76d-66b1-fa59578a7ad4.6' --output '<本项目输出目录>/original-body'
& $texturePython $textureScript prepare --source '<生成母版>.png' --reference '<本项目输出目录>/original-body.png' --output '<本项目输出目录>/body-new-v01.png'
```

`extract --output` 是无扩展名的前缀，生成 `.dds`、`.png`、`.json`。`prepare --output` 是 PNG 路径，旁边生成 `.metadata.json`。输出已存在会拒绝，另选版本路径即可；输入缓存只读。

脚本不保证 UV 接缝或材质序号正确，也不处理有用 Alpha 的新版规范化。生成图宽高比不对会拒绝，不能通过强行拉伸或中心裁切修复。
