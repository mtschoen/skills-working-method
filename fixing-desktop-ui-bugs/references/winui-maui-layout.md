# Worked example: a MAUI Editor whose viewport collapsed after a tab switch

The bug that produced this skill (file-wizard issue 489), kept as a worked example of
measuring from both sides and reading the framework at the pinned version.

## Symptom

A read-only `Editor` in a `Grid` star row showed about two and a half rows of text with an
empty band under it. The panel and the native `TextBox` were the right height (373 px); the
`TextBox` template's `ContentElement` `ScrollViewer` was 73 px. A previous fix that changed the
outer row heights was intact and irrelevant. The report said it happened "sometime during a
live session".

## What did not reproduce

Seeding 200 rows at page load: fills. Seeding 200 rows eight seconds after load: fills.
Seeding 1 row after load: fills. Trickling 60 rows one at a time: fills. Resizing: fills.
Every data-shaped and size-shaped step passed.

## What reproduced

Trickle 60 rows, then navigate to another Shell tab and back. Inner height 73 px, outer 426 px.
A resize afterwards did not recover it.

## In-process dump, before and after the reload

```
before  ScrollViewer 'ContentElement' actual=1588x241 desired=1586x238 va=Stretch viewportH=230
after   ScrollViewer 'ContentElement' actual=1588x42  desired=43x44   va=Top     viewportH=31
after   TextBox                       actual=1590x243 desired=0x0     minH=44
```

Two facts the UI Automation rectangles could not show: the alignment flipped from Stretch to
Top, and the `TextBox` was never re-measured (desired 0x0, the viewer's desired 44 equals the
`TextBox` minimum from its first one-line measure).

## Mechanism, from dotnet/maui at tag 10.0.11

- `src/Core/src/Platform/Windows/MauiTextBox.cs`: the attached `VerticalTextAlignment`
  property's change handler finds the template part named `ContentElement` and sets its
  `VerticalAlignment` directly.
- `AlignmentExtensions.ToPlatformVerticalAlignment` maps `Start` to `Top`, `Center` to `Center`,
  `End` to `Bottom`. No input yields `Stretch`.
- `EditorHandler.Windows.cs` calls `MauiTextBox.InvalidateAttachedProperties` from the
  `TextBox.Loaded` handler, so the pin is re-applied on every load. (A later MAUI adds
  `SizeChanged` as a second trigger: dotnet/maui pull request 26194.)
- `Editor.MeasureOverride` with `AutoSize=Disabled` returns the cached `DesiredSize` when the
  constraints match, so the platform view is not re-measured after the text grows.

At the first `Loaded` the panel was collapsed, the template did not exist, and the pin found
nothing; the viewer stayed `Stretch` and filled. The reload's `Loaded` found the template, pinned
`Top`, and a Top-aligned viewer takes its measured height, which was the one-line minimum.

## Fix

The page already located that `ScrollViewer` for scroll-position tracking. The wiring now also
subscribes `TextBox.SizeChanged` (the first moment the template exists for a control that starts
collapsed) and re-asserts `VerticalAlignment.Stretch` on every `Loaded` and `SizeChanged`. The
framework's handler subscribed to `Loaded` first, so the re-assertion runs after the pin.

## Regression check

A tracked PowerShell driver launches the built app with the seed variables, selects the page,
trickles rows, round-trips the tabs, resizes, clicks Clear, and prints outer and inner heights
per step. Before the fix the tab round-trip step read 426 and 73; after, 426 and 422.
