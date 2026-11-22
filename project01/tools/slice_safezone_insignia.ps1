param([Parameter(Mandatory)][string]$Source)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = 'D:/codex/project01/assets/art/packages/safezone-jade-insignia-v01'
New-Item -ItemType Directory -Path "$root/png","$root/source" -Force | Out-Null
Copy-Item -LiteralPath $Source -Destination "$root/source/image2-atlas.png" -Force
$atlas = [Drawing.Bitmap]::new("$root/source/image2-atlas.png")
if ($atlas.Width -ne 1254 -or $atlas.Height -ne 1254) { throw 'Unexpected source atlas size' }

$rows = @(
    @('star_locked',31,122,288,368), @('star_gold',342,122,598,368),
    @('star_jade',654,122,911,366), @('star_cinnabar',965,122,1224,367),
    @('star_imperial',30,490,290,743), @('quality_n',341,490,597,756),
    @('quality_r',654,492,908,749), @('quality_sr',963,471,1221,771),
    @('quality_ssr',20,852,301,1159), @('quality_ur',340,866,602,1142),
    @('quality_sur',622,848,939,1159), @('quality_tur',952,849,1236,1147)
)
$preview = [Drawing.Bitmap]::new(650,220)
$alphaPreview = [Drawing.Bitmap]::new(650,220)
$g = [Drawing.Graphics]::FromImage($preview)
$g.Clear([Drawing.Color]::FromArgb(246,239,218))
$a = [Drawing.Graphics]::FromImage($alphaPreview)
$a.Clear([Drawing.Color]::FromArgb(30,27,30))
$a.FillRectangle([Drawing.Brushes]::DeepPink, 0,110,650,110)
$manifest = [ordered]@{}
for ($i = 0; $i -lt $rows.Count; $i++) {
    $name, $l, $t, $r, $b = $rows[$i]
    $size = if ($name.StartsWith('star_')) {128} else {160}
    $crop = [Drawing.Bitmap]::new($r-$l,$b-$t,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    for ($y=0;$y -lt $crop.Height;$y++) {
        for ($x=0;$x -lt $crop.Width;$x++) {
            $pixel = $atlas.GetPixel($l+$x,$t+$y)
            if ($pixel.A -ge 12) { $crop.SetPixel($x,$y,$pixel) }
        }
    }
    $scaled = [Drawing.Bitmap]::new($size,$size,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $out = [Drawing.Graphics]::FromImage($scaled)
    $out.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $ratio = ($size - 12) / [Math]::Max($crop.Width,$crop.Height)
    $w = [int][Math]::Round($ratio*$crop.Width)
    $h = [int][Math]::Round($ratio*$crop.Height)
    $rect = [Drawing.Rectangle]::new([int](($size-$w)/2),[int](($size-$h)/2),$w,$h)
    $out.DrawImage($crop, $rect)
    $out.Dispose()
    $file = "$root/png/$name.png"
    $scaled.Save($file,[Drawing.Imaging.ImageFormat]::Png)
    $renderSize = if ($i -lt 5) {22} else {54}
    $cx = if ($i -lt 5) {75+$i*54} else {62+($i-5)*86}
    $cy = if ($i -lt 5) {48} else {145}
    foreach ($surface in @($g,$a)) {
        $surface.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $surface.DrawImage($scaled, [Drawing.Rectangle]::new($cx-$renderSize/2,$cy-$renderSize/2,$renderSize,$renderSize))
    }
    $manifest[$name] = @{
        file = "png/$name.png"; size = @($size,$size); source_bbox = @($l,$t,$r,$b)
        scale_mode = 'fixed_aspect'; sha256 = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $scaled.Dispose()
    $crop.Dispose()
}
$g.Dispose()
$a.Dispose()
$preview.Save("$root/preview_assets.png",[Drawing.Imaging.ImageFormat]::Png)
$alphaPreview.Save("$root/preview_alpha_check.png",[Drawing.Imaging.ImageFormat]::Png)
$preview.Dispose()
$alphaPreview.Dispose()
$atlas.Dispose()
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$root/manifest.json" -Encoding utf8
