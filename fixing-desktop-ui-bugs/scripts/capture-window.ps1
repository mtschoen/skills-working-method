# Screenshot a top-level window of a process WITHOUT focusing it (PrintWindow, PW_RENDERFULLCONTENT).
# Usage: capture-window.ps1 -ProcessName FileWizardMaui -OutFile C:\tmp\shot.png
param(
    [Parameter(Mandatory)] [string] $ProcessName,
    [Parameter(Mandatory)] [string] $OutFile,
    [int] $WaitSeconds = 0
)
Add-Type -AssemblyName System.Drawing
$signature = @'
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
public struct RECT { public int Left, Top, Right, Bottom; }
'@
$type = (Add-Type -MemberDefinition $signature -Name Win -Namespace Cap -PassThru) | Where-Object { $_.Name -eq 'Win' }
# Without this the (DPI-unaware) PowerShell process sees a scaled-down window rect and the bitmap crops the window.
$null = $type::SetProcessDPIAware()
if ($WaitSeconds -gt 0) { Start-Sleep -Seconds $WaitSeconds }
$process = Get-Process -Name $ProcessName -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $process) { throw "No window for process $ProcessName" }
$handle = $process.MainWindowHandle
$rect = New-Object Cap.Win+RECT
$null = $type::GetWindowRect($handle, [ref] $rect)
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
$ok = $type::PrintWindow($handle, $hdc, 2)
$graphics.ReleaseHdc($hdc)
$graphics.Dispose()
$bitmap.Save($OutFile, [System.Drawing.Imaging.ImageFormat]::Png)
$bitmap.Dispose()
"saved $OutFile ${width}x${height} printwindow=$ok pid=$($process.Id) title='$($process.MainWindowTitle)'"
