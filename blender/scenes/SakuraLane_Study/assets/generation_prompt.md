# 材质图集生成记录

使用内置 image_gen 工具。它只生成 `material_atlas.png` 的底色材质；没有生成最终场景图、没有改变用户原图，也不提供实测几何或真实 PBR 参数。

下列为本次实际发送的提示词：

```text
Create ONE square 2x2 material base-color texture atlas for a Blender environment of an old weathered Japanese timber street after rain. Four exactly equal square quadrants, no gutters, no borders, no labels, no text, no scene, no perspective. Orthographic flat surface scans with neutral diffuse illumination, no baked cast shadows, no specular highlights. Top left quadrant: very aged dark brown cedar timber planks, fine vertical grain, split fibers and worn desaturated edges, believable wood, not orange. Top right quadrant: pale ochre grey lime plaster with subtle water stains, hairline cracks, mottled wear, traces of dark underlying substrate, not chunky stone. Bottom left quadrant: dark slate blue grey weathered ceramic roof surface, fine worn mottling and subtle chips, NO large rows of roof tile shapes since tile geometry will be modeled. Bottom right quadrant: grey brown old flagstone surface with mineral texture, fine pores and hairline wear, NO large masonry grid since stone blocks will be modeled. Each quadrant should read as a seamless tileable material within itself, straight-on high-frequency physical texture. Muted realistic cinematic game environment material quality, detailed but restrained. The atlas is intended as albedo only; Blender will add roughness, bump, weathering, geometry and physical lighting.
```

图集被分配到木材、灰泥、屋面和石材的独立几何 UV 上。生成结果不是扫描材质；其无缝性、物理尺度与色彩都需要按具体画面检查。粗糙度、凹凸、浅水面和灯光由 Blender 节点与几何补充。
