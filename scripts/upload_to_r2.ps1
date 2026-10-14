# R2 上传辅助脚本（bqbq 表情包）
#
# 用法：
#   .\upload_to_r2.ps1 -Action check          # 检查 rclone 与环境
#   .\upload_to_r2.ps1 -Action dryrun         # 演习，不传数据
#   .\upload_to_r2.ps1 -Action thumbs         # 先传缩略图（13GB）
#   .\upload_to_r2.ps1 -Action images         # 再传原图（135GB）
#   .\upload_to_r2.ps1 -Action verify         # 校验远端数量与体积
#
# 依赖：rclone >= 1.59，且已配置好名为 r2 的 remote（见 R2_UPLOAD.md 第 5 节）

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('check', 'dryrun', 'thumbs', 'images', 'verify', 'resume')]
    [string]$Action,

    [string]$Remote = 'r2:bqbq-memes',
    [string]$ImageRoot = 'D:\bqbq_backend\meme_images',
    [string]$ThumbRoot = 'D:\bqbq_backend\meme_images_thumbnail'
)

$ErrorActionPreference = 'Stop'

function Assert-Rclone {
    $r = Get-Command rclone -ErrorAction SilentlyContinue
    if (-not $r) {
        Write-Host "找不到 rclone。请先安装：" -ForegroundColor Red
        Write-Host "  winget install --id Rclone.Rclone -e"
        exit 1
    }
    $ver = (& rclone version | Select-Object -First 1)
    Write-Host "rclone: $ver" -ForegroundColor Green
    if ($ver -match 'v(\d+)\.(\d+)') {
        $maj = [int]$Matches[1]; $min = [int]$Matches[2]
        if ($maj -lt 1 -or ($maj -eq 1 -and $min -lt 59)) {
            Write-Host "版本过低，R2 需要 >= 1.59（否则会 401）" -ForegroundColor Red
            exit 1
        }
    }
}

# 通用参数：小文件多，提高并发；失败重试
$common = @(
    '--transfers', '32',
    '--checkers', '32',
    '--retries', '5',
    '--low-level-retries', '20',
    '--stats', '30s',
    '--log-level', 'INFO'
)

switch ($Action) {

    'check' {
        Assert-Rclone
        Write-Host "`n=== 本地数据 ===" -ForegroundColor Cyan
        foreach ($p in @($ImageRoot, $ThumbRoot)) {
            if (-not (Test-Path -LiteralPath $p)) { Write-Host "缺失: $p" -ForegroundColor Red; continue }
            $m = Get-ChildItem -LiteralPath $p -Recurse -File -ErrorAction SilentlyContinue |
                 Measure-Object -Property Length -Sum
            $gib = [math]::Round($m.Sum / 1GB, 2)
            Write-Host ("{0,-28} {1,8} 个文件  {2,10} GiB" -f (Split-Path $p -Leaf), $m.Count, $gib)
        }
        Write-Host "`n=== 远端连通性 ===" -ForegroundColor Cyan
        & rclone lsd $Remote
        if ($LASTEXITCODE -ne 0) { Write-Host "无法访问 $Remote，检查配置" -ForegroundColor Red; exit 1 }
        Write-Host "`n远端当前内容：" -ForegroundColor Cyan
        & rclone size $Remote
    }

    'dryrun' {
        Assert-Rclone
        Write-Host "`n=== 演习：缩略图 ===" -ForegroundColor Cyan
        & rclone copy $ThumbRoot "$Remote/meme_images_thumbnail" --dry-run @common -P
        Write-Host "`n=== 演习：原图（只显示前 200 行）===" -ForegroundColor Cyan
        & rclone copy $ImageRoot "$Remote/meme_images" --dry-run @common | Select-Object -First 200
        Write-Host "`n以上为演习结果，未传输任何数据。" -ForegroundColor Yellow
        Write-Host "确认无误后用 -Action thumbs / -Action images 正式上传。"
    }

    'thumbs' {
        Assert-Rclone
        Write-Host "`n=== 上传缩略图（约 13 GiB）===" -ForegroundColor Cyan
        & rclone copy $ThumbRoot "$Remote/meme_images_thumbnail" @common `
            --log-file 'D:\bqbq_backend\r2_thumb_upload.log' -P
        if ($LASTEXITCODE -eq 0) { Write-Host "缩略图上传完成" -ForegroundColor Green }
        else { Write-Host "退出码 $LASTEXITCODE，可重跑本命令续传" -ForegroundColor Yellow }
    }

    'images' {
        Assert-Rclone
        Write-Host "`n=== 上传原图（约 135 GiB，耗时较长）===" -ForegroundColor Cyan
        Write-Host "中断后重新执行本命令即可续传。" -ForegroundColor Yellow
        & rclone copy $ImageRoot "$Remote/meme_images" @common `
            --log-file 'D:\bqbq_backend\r2_image_upload.log' -P
        if ($LASTEXITCODE -eq 0) { Write-Host "原图上传完成" -ForegroundColor Green }
        else { Write-Host "退出码 $LASTEXITCODE，可重跑本命令续传" -ForegroundColor Yellow }
    }

    'resume' {
        Assert-Rclone
        Write-Host "`n=== 续传：两条命令重跑即可，已传的会自动跳过 ===" -ForegroundColor Cyan
        & rclone copy $ThumbRoot "$Remote/meme_images_thumbnail" @common -P
        & rclone copy $ImageRoot "$Remote/meme_images" @common -P
    }

    'verify' {
        Assert-Rclone
        Write-Host "`n=== 远端统计 ===" -ForegroundColor Cyan
        Write-Host "-- meme_images --"
        & rclone size "$Remote/meme_images"
        Write-Host "-- meme_images_thumbnail --"
        & rclone size "$Remote/meme_images_thumbnail"

        Write-Host "`n期望值：" -ForegroundColor Yellow
        Write-Host "  meme_images           434810 个对象 / 134.98 GiB"
        Write-Host "  meme_images_thumbnail 434811 个对象 /  13.21 GiB"

        Write-Host "`n=== 抽查 7f/5d 分片 ===" -ForegroundColor Cyan
        & rclone lsjson "$Remote/meme_images/7f/5d" --files-only | Select-Object -First 20

        Write-Host "`n提示：如需更严格比对，可执行（较慢）：" -ForegroundColor Yellow
        Write-Host "  rclone check `"$ImageRoot`" `"$Remote/meme_images`" --size-only --one-way -P"
    }
}
