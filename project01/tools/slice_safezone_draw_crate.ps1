param([Parameter(Mandatory)][string]$Source)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Join-Path $PSScriptRoot '../assets/art/packages/safezone-draw-reveal-v01'
New-Item -ItemType Directory -Path "$root/png","$root/source" -Force | Out-Null
Copy-Item -LiteralPath $Source -Destination "$root/source/image2-crate.png" -Force
$atlas = [Drawing.Bitmap]::new("$root/source/image2-crate.png")
if ($atlas.Width -ne 1774 -or $atlas.Height -ne 887) { throw 'Unexpected atlas size' }

$boxes = @(@('crate_closed',48,243,833,773), @('crate_open',914,170,1722,774))
$manifest = [ordered]@{}
$preview = [Drawing.Bitmap]::new(860,435)
$g = [Drawing.Graphics]::FromImage($preview)
$g.Clear([Drawing.Color]::FromArgb(30,28,25))
$g.FillRectangle([Drawing.Brushes]::DeepPink, 430,0,430,435)
for ($i=0; $i -lt $boxes.Count; $i++) {
    $key,$l,$t,$r,$b = $boxes[$i]
    $crop = [Drawing.Bitmap]::new($r-$l,$b-$t,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    for ($y=0;$y -lt $crop.Height;$y++) {
        for ($x=0;$x -lt $crop.Width;$x++) {
            $pixel = $atlas.GetPixel($l+$x,$t+$y)
            if ($pixel.A -ge 12) { $crop.SetPixel($x,$y,$pixel) }
        }
    }
    $frame = [Drawing.Bitmap]::new(512,512,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $draw = [Drawing.Graphics]::FromImage($frame)
    $draw.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $h = [int][Math]::Round($crop.Height*472/$crop.Width)
    $draw.DrawImage($crop,[Drawing.Rectangle]::new(20,455-$h,472,$h))
    $draw.Dispose()
    $file = "$root/png/$key.png"
    $frame.Save($file,[Drawing.Imaging.ImageFormat]::Png)
    $g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($frame,[Drawing.Rectangle]::new(430*$i+30,0,370,370))
    $manifest[$key] = @{
        file="png/$key.png"; size=@(512,512); source_bbox=@($l,$t,$r,$b)
        scale_mode='fixed_aspect'; baseline_px=455
        sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $frame.Dispose()
    $crop.Dispose()
}
$g.Dispose()
$preview.Save("$root/preview_alpha_check.png",[Drawing.Imaging.ImageFormat]::Png)
$preview.Dispose()
$atlas.Dispose()
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$root/manifest.json" -Encoding utf8
