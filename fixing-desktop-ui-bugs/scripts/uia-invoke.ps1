# Activate a UI element by name through UI Automation patterns (SelectionItem, Invoke, Toggle).
# This is programmatic activation: it does not move the mouse or steal keyboard focus from the
# user's foreground window. Usage: uia-invoke.ps1 -ProcessName FileWizardMaui -Name Scanner
# -Ancestors N walks up N parents from the named element before invoking (e.g. the text label of a
# tab item is a TextBlock; the selectable item is its parent).
param(
    [Parameter(Mandatory)] [string] $ProcessName,
    [Parameter(Mandatory)] [string] $Name,
    [int] $Ancestors = 0,
    [string] $ControlType = ''
)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$process = Get-Process -Name $ProcessName -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $process) { throw "No window for process $ProcessName" }
$root = [System.Windows.Automation.AutomationElement]::FromHandle($process.MainWindowHandle)
$condition = New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::NameProperty), $Name
if ($ControlType) {
    $typeField = [System.Windows.Automation.ControlType].GetField($ControlType)
    if (-not $typeField) { throw "Unknown control type $ControlType" }
    $typeCondition = New-Object System.Windows.Automation.PropertyCondition ([System.Windows.Automation.AutomationElement]::ControlTypeProperty), $typeField.GetValue($null)
    $condition = New-Object System.Windows.Automation.AndCondition @($condition, $typeCondition)
}
$element = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
if (-not $element) { throw "No element named '$Name'" }
$walker = [System.Windows.Automation.TreeWalker]::RawViewWalker
for ($i = 0; $i -lt $Ancestors; $i++) { $element = $walker.GetParent($element) }
$describe = '{0} class={1} name="{2}"' -f $element.Current.ControlType.ProgrammaticName, $element.Current.ClassName, $element.Current.Name
$patterns = $element.GetSupportedPatterns() | ForEach-Object { $_.ProgrammaticName }
"target: $describe patterns: $($patterns -join ',')"
$selection = $null
if ($element.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref] $selection)) { $selection.Select(); 'selected'; return }
$invoke = $null
if ($element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref] $invoke)) { $invoke.Invoke(); 'invoked'; return }
$toggle = $null
if ($element.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern, [ref] $toggle)) { $toggle.Toggle(); 'toggled'; return }
throw "Element supports none of SelectionItem/Invoke/Toggle: $describe"
