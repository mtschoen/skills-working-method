# List every element in a process's main window that supports the UI Automation Scroll pattern,
# with whether it is vertically scrollable and how much of the extent the viewport shows.
# Read-only: answers "does this list scroll or is it clipped?" without any input.
param([Parameter(Mandatory)] [string] $ProcessName)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$dpi = Add-Type -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();' -Name Dpi2 -Namespace Cap -PassThru
$null = $dpi::SetProcessDPIAware()
$process = Get-Process -Name $ProcessName -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
$condition = New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::IsScrollPatternAvailableProperty), $true
foreach ($element in $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)) {
    $scroll = $element.GetCurrentPattern([System.Windows.Automation.ScrollPattern]::Pattern)
    $rect = $element.Current.BoundingRectangle
    $firstChild = [System.Windows.Automation.TreeWalker]::RawViewWalker.GetFirstChild($element)
    $childName = if ($firstChild) { $firstChild.Current.Name } else { '' }
    '{0} class={1} rect=({2},{3} {4}x{5}) vScrollable={6} vViewSize={7}% vPercent={8} firstChild="{9}"' -f $element.Current.ControlType.ProgrammaticName, $element.Current.ClassName, [int]$rect.X, [int]$rect.Y, [int]$rect.Width, [int]$rect.Height, $scroll.Current.VerticallyScrollable, [int]$scroll.Current.VerticalViewSize, $scroll.Current.VerticalScrollPercent, ($childName -replace "`n.*", '')
}
