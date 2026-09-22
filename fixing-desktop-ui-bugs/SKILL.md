---
name: fixing-desktop-ui-bugs
description: "Use when a bug lives in a desktop GUI (WinUI 3, .NET MAUI, WPF, Avalonia, Win32) and reproducing, diagnosing, or verifying it means driving the running app on a machine someone is sitting at, when the report says a control is the wrong size, clipped, blank, or misaligned, or that it happens 'sometime during a session' with no known trigger, when the crew parked it as needs-operator or attended-only, and before reaching for computer use, SendInput, SetForegroundWindow, a process kill, or asking the owner to click."
---

# Fixing desktop UI bugs

A layout bug is fixed when a measurement taken from the running app says so, before and after. The whole skill is about getting that measurement without a human at the keyboard and without touching the keyboard they are using.

## The contract with the person at the desk

Every interaction with the app is one of these, and nothing else:

| Need | Use | Never |
| --- | --- | --- |
| See the window | `PrintWindow(hwnd, hdc, 2)` after `SetProcessDPIAware()` (`scripts/capture-window.ps1`) | `CopyFromScreen`, `SetForegroundWindow` |
| Measure a control | UI Automation raw tree, `BoundingRectangle` in physical pixels (`scripts/uia-dump.ps1`) | eyeballing a screenshot |
| Activate a tab, button, item | UI Automation `SelectionItem`, `Invoke`, `Toggle` patterns (`scripts/uia-invoke.ps1`) | `SendInput`, `mouse_event`, `SetCursorPos`, computer use |
| Tell "clipped" from "scrolls" | `ScrollPattern.VerticallyScrollable` and `VerticalViewSize` (`scripts/uia-scrollinfo.ps1`) | guessing from a partially visible row |
| Resize | `SetWindowPos` with `SWP_NOMOVE\|SWP_NOZORDER\|SWP_NOACTIVATE` (0x0016) | dragging |
| Close | `PostMessage(hwnd, WM_CLOSE)` and wait | `Stop-Process`, `taskkill` |
| Reach a state behind a UAC prompt | an env-var seam that produces the state unelevated | automation of the secure desktop (impossible) |

Say in the reply that a window will open and that nothing will be sent to it. The owner may keep working; ask them only to leave that one window alone during a run. A UAC click is the one thing to ask a person for, and only after the seam route is exhausted.

## The recipe

1. **Get a build that does not need a person.** If the app is already running, probe that instance first: it may be sitting in the reported state, which skips the reproduction. Otherwise find or add an env-var seam that puts the UI in the reported state without the privileged path (a seed of N synthetic rows, a fake source). Extend an existing seam rather than adding a parallel one; the seam ships, because it is the reproduction. After launch, poll for a nonzero `MainWindowHandle` instead of sleeping a fixed time.
2. **Reproduce with a transition matrix, not a data matrix.** "Sometime during a session" means a lifecycle transition, so the matrix is: seed at first layout; seed after first layout; one item then trickle; navigate to another page and back (unload and reload); resize; minimize and restore; theme or DPI change; the app's own clear or reset. Measure after every step and stop at the first one that reproduces. Data-only matrices (more rows, bigger window) are what the baseline agent tried and they missed a reload trigger entirely.
3. **Measure from both sides of the toolkit boundary.** UI Automation gives rectangles from outside. Add a temporary in-process dump (under an env var, deleted before the PR) that walks the native visual tree from the control's platform view and writes `ActualHeight`, `DesiredSize`, `Height`, `MinHeight`, `VerticalAlignment`, `Margin`, `Visibility`, a ScrollViewer's viewport and extent, a Grid's row heights. The outside number says which element is wrong; the inside dump says which property made it so.
4. **Get the mechanism from the framework source at the pinned version, by a lane.** Dispatch a read-only agent with the exact tag (read the package pin) and the template part names from the dump. Ask for every code path that sets the offending property and when each fires (load, size change, property change), plus the upstream tracker. A fix chosen without this is a guess, and the second guess costs a rebuild and a run each.
5. **Fix at the hook where the framework fires, then re-run the exact reproducing step.** The pass criterion is a number: inner height within border-and-margin allowance of outer height, at the reproducing step and at every other step of the matrix.
6. **Ship the driver as the regression check.** One tracked script: launch with the seam, walk the matrix, print `step=<name> outer=<px> inner=<px> result=PASS|FAIL`, exit nonzero on any FAIL, screenshots into an ignored output directory that the repo's clean table lists. Record it in the manual test plan row it automates.
7. **Attribute the evidence.** The PR body names who ran the driver, on which machine and session, the display scale, and the before and after numbers per step, in a table. Attended-looking claims with unattended provenance get graded as fabricated.

## Gotchas that cost a rebuild each

- A running app holds its `bin` output; close it (WM_CLOSE) before rebuilding, or the build fails on the copy step.
- PowerShell is DPI-unaware: without `SetProcessDPIAware()` every rectangle is scaled and `PrintWindow` crops the window.
- `Add-Type -MemberDefinition ... -PassThru` returns every type it compiled; select the class by name, and reference nested structs as `Namespace.Class+Struct`.
- `FindFirst` by name returns the first match in raw order, often a hidden container; add a `ControlType` condition. Shell and NavigationView tabs are `SelectionItem`, not `Invoke`.
- A collapsed WinUI control has no template until it is first shown; anything that searches its template parts on `Loaded` finds nothing at the first load and everything at the reload. Wire such lookups to `SizeChanged` too.
- After a page reload the framework's own `Loaded` handlers run before yours, so re-assert your property after theirs, on every `Loaded`.

`references/winui-maui-layout.md` records the MAUI Windows Editor mechanism this skill was built on, as a worked example of steps 3 and 4.

## Red flags

- "I'll ask the owner to click through it" before an env-var seam was looked for.
- "The synthetic seed does not reproduce, so it needs a live session" before a reload or resize step was tried.
- "This matches a known WinUI failure signature, so invalidate measure" with no in-process dump and no source read at the pinned version.
- A fix verified by a screenshot alone, with no inner and outer numbers.
- The driver script left in the scratchpad instead of the repo.
