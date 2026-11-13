# 出 Android 包

```bat
export_apk.bat                  :: 编号 +1，导出 sheep-counter-v<N>-<YYYYMMDD>.apk
export_apk.bat --no-bump        :: 编号不变，同版重出
export_apk.bat --note=palette   :: 追加短标签，便于区分
```

1. 脚本（`hrm_godot/tools/export_apk.py`）先把 `version/code` +1、`version/name` 写成 `1.<code>`；
2. 导出到 `hrm_godot/build/_export_tmp.apk`；
3. **只有导出与签名都成功**，才删掉根目录与 `hrm_godot/build/` 里所有 `sheep-counter*.apk`、`*.idsig`；
4. 改名为 `sheep-counter-v<code>-<日期>.apk` 放到仓库根目录。

核对：

```bat
aapt2 dump badging sheep-counter-v2-20261109.apk | findstr versionCode
```
应看到 `versionCode='2' versionName='1.2'`，与文件名里的编号一致。

注意：APK 内的 `.gdc` 是压缩二进制，搜不到中文文案，**不能用它判断包的新旧**；
要查内容只能看 `assets/data/i18n.json` 里有没有当天新增的句子。
