# Dump the UI Automation tree (control type, class, name, automation id, bounding rect in physical
# pixels) of a process's main window. Read-only: never focuses, clicks or types.
# -Filter limits printed lines to a regex. Output is one line per element, indented by depth.
param(
    [Parameter(Mandatory)] [string] $ProcessName,
    [string] $Filter = '.',
    [int] $MaxDepth = 40
)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$dpi = Add-Type -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();' -Name Dpi -Namespace Cap -PassThru
$null = $dpi::SetProcessDPIAware()
$process = Get-Process -Name $ProcessName -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $process) { throw "No window for process $ProcessName" }
$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
$walker = [System.Windows.Automation.TreeWalker]::RawViewWalker
function Format-Number($value) {
    if ([double]::IsInfinity($value) -or [double]::IsNaN($value)) { return 'inf' }
    return [string][int]$value
}
function Dump-Element($element, $depth) {
    if ($depth -gt $MaxDepth) { return }
    $current = $element.Current
    $rect = $current.BoundingRectangle
    $controlType = if ($current.ControlType) { $current.ControlType.ProgrammaticName.Replace('ControlType.', '') } else { '?' }
    $line = ('{0}{1} class={2} name="{3}" id={4} rect=({5},{6} {7}x{8})' -f (' ' * $depth), $controlType, $current.ClassName, $current.Name, $current.AutomationId, (Format-Number $rect.X), (Format-Number $rect.Y), (Format-Number $rect.Width), (Format-Number $rect.Height))
    if ($line -match $Filter) { $line }
    $child = $walker.GetFirstChild($element)
    while ($child -ne $null) {
        Dump-Element $child ($depth + 1)
        $child = $walker.GetNextSibling($child)
    }
}
Dump-Element $root 0
