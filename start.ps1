# ============================================================
#  BQBQ v2 一键启动
#
#  用法：在本目录右键"在终端中打开"，然后执行：
#      .\start.ps1                 # 默认：后端 + 前端 build 模式（推荐）
#      .\start.ps1 -DevMode        # 后端 + 前端 dev 模式（改代码热更新）
#
#  可选参数：
#      -DevMode        前端跑 Vite dev server（5173），适合改前端代码
#      -Build          强制先重新构建前端再启动
#      -BackendOnly    只启动后端
#      -FrontendOnly   只启动前端
#      -Force          端口被占用时，自动结束占用进程再启动
#
#  ── 两种模式的区别（重要）──
#
#  build 模式（默认，公网访问必须用它）：
#      前端产物由【后端 8000】直接托管，访问 http://127.0.0.1:8000/g2/
#      · 只有 1 个 JS（约 310 KB）+ 1 个 CSS
#      · 只需一个服务，无需代理
#      · 公网经 nginx 转发时更快
#
#  dev 模式（改代码时用）：
#      前端跑 Vite dev server，访问 http://localhost:5173/g2/
#      · 浏览器逐个请求 .ts/.vue 源码（约 28 个模块、2.6 MB 未压缩）
#      · 公网访问会非常慢，不要用它对外服务
# ============================================================

param(
    [switch]$DevMode,
    [switch]$Build,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

# 项目根目录（以本脚本所在位置为准，可在任意目录调用）
$Root      = $PSScriptRoot
$BackendDir  = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'

$BackendPort  = 8000
$FrontendPort = 5173

function Write-Title($text) {
    Write-Host ''
    Write-Host ('=' * 58) -ForegroundColor DarkCyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ('=' * 58) -ForegroundColor DarkCyan
}

# 查询占用指定端口的进程 PID（可能多个）
function Get-PortOwners([int]$Port) {
    $lines = netstat -ano | Select-String ":$Port\s+.*LISTENING"
    $pids = @()
    foreach ($l in $lines) {
        $parts = ($l.ToString().Trim() -split '\s+')
        $pidStr = $parts[-1]
        if ($pidStr -match '^\d+$') { $pids += [int]$pidStr }
    }
    return ($pids | Sort-Object -Unique)
}

# 处理端口占用：返回 $true 表示可以继续启动
function Resolve-Port([int]$Port, [string]$Name) {
    $owners = Get-PortOwners $Port
    if (-not $owners) { return $true }

    Write-Host "[!] 端口 $Port ($Name) 已被占用：" -ForegroundColor Yellow
    foreach ($procId in $owners) {
        $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($p) {
            $started = try { $p.StartTime.ToString('MM-dd HH:mm') } catch { '?' }
            Write-Host ("      PID {0,-6} {1,-12} 启动于 {2}" -f $procId, $p.ProcessName, $started) -ForegroundColor DarkYellow
        } else {
            Write-Host ("      PID {0,-6} (无法读取信息)" -f $procId) -ForegroundColor DarkYellow
        }
    }

    if ($Force) {
        foreach ($procId in $owners) {
            try {
                Stop-Process -Id $procId -Force -ErrorAction Stop
                Write-Host "      已结束 PID $procId" -ForegroundColor Green
            } catch {
                Write-Host "      结束 PID $procId 失败：$($_.Exception.Message)" -ForegroundColor Red
            }
        }
        # 端口不会立刻释放（TCP TIME_WAIT + 子进程退出需要时间）。
        # 尤其 uvicorn --reload 会拉子进程，父进程结束后子进程可能仍占着端口，
        # 所以这里轮询等待，并在中途再清理一次残留的 python/node 监听者。
        $waited = 0
        $maxWait = 20
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds 1
            $waited++
            $still = Get-PortOwners $Port
            if (-not $still) { break }

            if ($waited -eq 5 -or $waited -eq 10) {
                foreach ($procId in $still) {
                    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
                    if ($p -and $p.ProcessName -in @('python', 'node')) {
                        try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch {}
                    }
                }
            }
        }

        if (-not (Get-PortOwners $Port)) {
            Write-Host "      端口 $Port 已释放（等待 ${waited}s）" -ForegroundColor Green
            return $true
        }

        Write-Host "[x] 端口 $Port 等待 ${maxWait}s 后仍被占用，无法启动 $Name" -ForegroundColor Red
        foreach ($procId in (Get-PortOwners $Port)) {
            $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($p) { Write-Host "      仍占用: PID $procId $($p.ProcessName)" -ForegroundColor Red }
        }
        return $false
    }

    Write-Host ''
    Write-Host "    该端口已被占用，$Name 启动会失败。" -ForegroundColor Yellow
    Write-Host "    如果那是旧的进程，请先结束它，或改用：" -ForegroundColor Yellow
    Write-Host "        .\start.ps1 -Force" -ForegroundColor White
    Write-Host ''
    return $false
}

# 在新 PowerShell 窗口中运行一条命令
function Start-InNewWindow([string]$Title, [string]$WorkDir, [string]$Command) {
    $inner = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
Set-Location -LiteralPath '$WorkDir'
Write-Host '=== $Title ===' -ForegroundColor Cyan
Write-Host ('目录: ' + (Get-Location).Path) -ForegroundColor DarkGray
Write-Host ''
$Command
Write-Host ''
Write-Host '--- 进程已退出，按任意键关闭窗口 ---' -ForegroundColor DarkGray
try { `$null = `$Host.UI.RawUI.ReadKey() } catch { Start-Sleep -Seconds 30 }
"@

    # 用 -EncodedCommand 避免中文/引号在多层传递中被破坏
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($inner))
    Start-Process -FilePath 'powershell.exe' `
                  -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $encoded `
                  -WorkingDirectory $WorkDir | Out-Null
}

Write-Title 'BQBQ v2 启动器'

# ---------- 前置检查 ----------
$missing = @()
foreach ($t in @('python', 'node')) {
    if (-not (Get-Command $t -ErrorAction SilentlyContinue)) { $missing += $t }
}
if ($missing.Count -gt 0) {
    Write-Host "[x] 找不到命令：$($missing -join ', ')" -ForegroundColor Red
    Write-Host "    请确认 Python 与 Node.js 已安装并加入 PATH。" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $BackendDir 'run.py'))) {
    Write-Host "[x] 找不到 backend\run.py，请确认脚本放在项目根目录。" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir 'package.json'))) {
    Write-Host "[x] 找不到 frontend\package.json。" -ForegroundColor Red
    exit 1
}

$startBackend  = -not $FrontendOnly
$startFrontend = -not $BackendOnly
$useDevServer  = $DevMode.IsPresent
$distDir       = Join-Path $FrontendDir 'dist'

# 前端依赖检查
if ($startFrontend -and -not (Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules'))) {
    Write-Host '[!] frontend\node_modules 不存在，正在安装依赖（首次较慢）...' -ForegroundColor Yellow
    Push-Location $FrontendDir
    try { & npm install } finally { Pop-Location }
}

# ---------- build 模式：确保产物是最新的 ----------
if (-not $useDevServer) {
    $distIndex = Join-Path $distDir 'index.html'
    $needBuild = $Build.IsPresent -or (-not (Test-Path -LiteralPath $distIndex))

    if (-not $needBuild) {
        # 产物存在：检查是否有源码比产物新，有则重新构建
        $distTime = (Get-Item -LiteralPath $distIndex).LastWriteTime
        $newer = Get-ChildItem -LiteralPath (Join-Path $FrontendDir 'src') -Recurse -File -ErrorAction SilentlyContinue |
                 Where-Object { $_.LastWriteTime -gt $distTime } |
                 Select-Object -First 1
        if ($newer) {
            Write-Host "[!] 检测到源码有更新（$($newer.Name)），需要重新构建" -ForegroundColor Yellow
            $needBuild = $true
        }
    }

    if ($needBuild) {
        Write-Host '[+] 构建前端（build 模式）...' -ForegroundColor Cyan
        Push-Location $FrontendDir
        try {
            & npm run build
            if ($LASTEXITCODE -ne 0) {
                Write-Host '[x] 前端构建失败。' -ForegroundColor Red
                Write-Host '    可改用 dev 模式启动：.\start.ps1 -DevMode' -ForegroundColor Yellow
                Pop-Location
                exit 1
            }
        } finally { Pop-Location }
        Write-Host '    构建完成' -ForegroundColor Green
    } else {
        Write-Host '[=] 复用已有的 build 产物（源码无变化）' -ForegroundColor DarkGray
    }
}

# ---------- 端口占用处理 ----------
$okBackend  = $true
$okFrontend = $true
if ($startBackend)  { $okBackend  = Resolve-Port $BackendPort  '后端' }
# build 模式下前端由后端托管，不需要 5173
if ($startFrontend -and $useDevServer) { $okFrontend = Resolve-Port $FrontendPort '前端' }

if (-not $okBackend -or -not $okFrontend) {
    Write-Host ''
    Write-Host '启动已取消。处理后重新运行本脚本。' -ForegroundColor Yellow
    exit 1
}

# ---------- 启动 ----------
if ($startBackend) {
    Write-Host '[+] 启动后端 -> 新窗口 (http://127.0.0.1:8000)'
    # python run.py 里已含 uvicorn reload
    Start-InNewWindow 'BQBQ 后端' $BackendDir 'python run.py'
}

if ($startFrontend -and $useDevServer) {
    Write-Host '[+] 启动前端 dev server -> 新窗口 (http://localhost:5173/g2/)'
    Start-InNewWindow 'BQBQ 前端(dev)' $FrontendDir 'npm run dev'
}

Start-Sleep -Seconds 4

Write-Host ''
if ($useDevServer) {
    Write-Host '【dev 模式】地址：' -ForegroundColor Green
    if ($startBackend)  { Write-Host '  后端 API   http://127.0.0.1:8000/docs' -ForegroundColor Green }
    Write-Host '  前端页面   http://localhost:5173/g2/' -ForegroundColor Green
    Write-Host ''
    Write-Host '  注意：dev 模式浏览器要加载约 28 个模块（2.6 MB），' -ForegroundColor Yellow
    Write-Host '        公网访问会很慢。对外服务请用 build 模式（不加 -DevMode）。' -ForegroundColor Yellow
} else {
    Write-Host '【build 模式】地址：' -ForegroundColor Green
    if ($startBackend) {
        Write-Host '  前端页面   http://127.0.0.1:8000/g2/' -ForegroundColor Green
        Write-Host '  后端 API   http://127.0.0.1:8000/docs' -ForegroundColor Green
        Write-Host '  公网访问   https://bqbq.mmc199.com/g2/  (经 nginx 转发)' -ForegroundColor Green
    } else {
        Write-Host '  未启动后端；build 产物需由后端托管，请去掉 -FrontendOnly' -ForegroundColor Yellow
    }
    Write-Host ''
    Write-Host '  只有 1 个 JS（约 310 KB）+ 1 个 CSS，公网加载快得多。' -ForegroundColor DarkGray
}
Write-Host ''
Write-Host '提示：' -ForegroundColor DarkGray
Write-Host '  - 关闭对应窗口即可停止该服务' -ForegroundColor DarkGray
Write-Host '  - 改前端代码后：dev 模式自动热更新；build 模式需重跑本脚本' -ForegroundColor DarkGray
Write-Host '  - 若启动失败，看新窗口里的报错信息' -ForegroundColor DarkGray
Write-Host ''
