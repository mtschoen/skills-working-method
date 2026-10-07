# When to decompile

The gate in full: the three tiers with worked examples, the justification template filled in,
output handling with a write-up example, and the legal background. `SKILL.md` carries the short
form; this page is the reference when a case is not obvious.

## Source first

A decompiler is the last reader, not the first. The owner's own repository (every branch and
tag, the CI artifacts of the build in question), a source-linked or symbol-bearing package, the
library's public repository, UnityCsReference for managed UnityEngine and UnityEditor code,
source.dot.net for the runtime, and Unity's public mono fork all come before any tool. Only when
none of them holds the code in the binary at hand does the question of tiers arise.

Runtime questions are not decompiler questions at all. "Which record makes it return 0", "what is
null here", "why is play mode different" are answered by breaking, inspecting, and logging; see
`using-a-debugger`. Decompiling the owner's own debug build adds nothing over reading the source
beside it.

## Tier 1: the owner's own build

Proceed. No permission, no justification, no legal note. Narrow first, symbols if they exist,
output kept or discarded as the owner likes.

- **A shipped dll with a lost tag.** `Inventory.Reports.dll` went to a customer from a CI machine
  that has since been reimaged; the git tag is gone and the owner wants to know which `Add`
  overload shipped. The dll is theirs. `ilspycmd -l c Inventory.Reports.dll`, then
  `ilspycmd -t Inventory.Reports.ReportBuilder Inventory.Reports.dll`. Without the pdb beside it,
  local names are decompiler-invented; say so, and compare method bodies rather than local names.
- **The owner's own IL2CPP player.** `game/MyGame_IL2CPP` was built from their project months ago
  and the commit is lost; they want the damage formula that shipped in `Combat.ApplyDamage`. The
  artifacts are `GameAssembly.dll` and `MyGame_Data/il2cpp_data/Metadata/global-metadata.dat`.
  Cpp2IL recovers stub assemblies (signatures only, empty bodies) and a name-to-address map; Ghidra
  on `GameAssembly.dll` with the recovered names applied shows the arithmetic. Two tools, no
  question asked.

A lost tag, a reimaged build machine, a missing pdb, or a build made by a former colleague on the
owner's own project does not move the artifact out of Tier 1.

## Tier 2: third-party code the owner legitimately possesses

Write the four-line justification, ask one question, proceed on a yes. The owner's standard,
not the law alone, makes the call; the legal background below is information for that decision.

- **A crashing vendor client.** AcmeSync 4.2.1, installed from the vendor's installer, dies
  several times a day in `FolderWatcher.OnRenamed`; support has not answered in nine days; there
  is no source and no pdb; the EULA says "You may not reverse engineer, decompile, or disassemble
  the Software except to the extent that applicable law expressly permits." The agent writes the
  justification, mentions the clause in one sentence, asks once, and on a yes runs
  `ilspycmd -t AcmeSync.Client.FolderWatcher AcmeSync.Client.dll`.
- **An installer that phones home.** A setup program the owner ran on their machine makes
  outbound connections nobody documented. Reading the client to learn what it sends and where is
  Tier 2: possession is legitimate, purpose is understanding their own machine's traffic, output
  stays in scratch.
- **A file format the owner's tool must read.** The owner's product has to open a proprietary
  file written by a program they own a license for, and no format specification exists. Reading
  the writer to learn the layout is the interoperability case the law carves out explicitly, and
  still Tier 2: justification, one question, scratch.

### The justification, filled in

```text
Target:      AcmeSync.Client.dll, version 4.2.1 (vendor/AcmeSync/, installed 2026-09-30)
Possession:  installed by the owner from the vendor's AcmeSync-Setup-4.2.1.exe on their own machine
Purpose:     find what is null in FolderWatcher.OnRenamed so the crash can be reported precisely or worked around
Boundaries:  no redistribution of the output; decompiled source stays in the session scratchpad; nothing committed; stop once the null is identified
```

Followed by one sentence on the EULA if it has a clause, and one question: "Proceed with this?"

**The agent never starts a Tier 2 decompile on its own initiative.** Not because the owner is
in a hurry, not because the answer is obvious, not because the vendor is unresponsive. The yes
is the trigger.

## Tier 3: decline once

Decline the decompile-and-patch step in one or two plain sentences, offer a permitted path, and
keep helping with everything else.

- **Patching an anti-cheat.** "Decompile the anti-cheat driver and find the check that blocks my
  overlay so I can patch it out." Decline the patch; offer the vendor's allow-list or support
  request, a mode the anti-cheat permits, or the overlay author's compatibility guidance.
- **Removing a license check.** Decline; offer the vendor's licensing channel or a trial.
- **Lifting a competitor's pricing algorithm.** Decline; offer public documentation, the
  competitor's published API, or building the owner's own.
- **A leaked build.** The owner does not legitimately possess it. Decline; nothing to offer
  beyond the legitimate release.

### Not an enforcer

One decline is the whole response to the request. No lecture, no speculation about consequences
beyond a sentence, no reporting, logging, flagging, or filing of the request anywhere, no
refusing to keep helping with other things, no ending the conversation. The owner asked a
question and got a plain answer; the session continues.

## Output handling

Tier 2 output lives in scratch: the session scratchpad or a gitignored `workspace/`. It never
enters the repository, an issue, a PR, a memory note, or a message to the vendor wholesale. Cite
by symbol and offset (type, method, field, condition), quote the minimum (a few lines at most),
and say why the quote is minimal.

A vendor bug write-up that follows the rule:

```text
AcmeSync.Client 4.2.1 crashes with NullReferenceException in
AcmeSync.Client.FolderWatcher.OnRenamed(object, RenamedEventArgs).

The method dereferences a private field that is only assigned when the
watcher is constructed with a filter argument. A watcher created through the
parameterless path leaves the field null, and the first rename event in the
watched folder throws. Reproduction: install 4.2.1, add a sync folder with
no filter, rename any file inside it.

Stack (from logs/crash-2026-10-05.txt):
   at AcmeSync.Client.FolderWatcher.OnRenamed(Object sender, RenamedEventArgs e)
   at System.IO.FileSystemWatcher.NotifyRenameEventArgs(...)
```

The write-up names the type, the method, the field's role, and the condition. It carries the
owner's own crash log, not the decompiled method body. The full decompiled output stays in
scratch for the owner to consult.

Tier 1 output may be kept where the owner likes, but a whole-project decompile of their own dll
is still scratch; the source is the record.

## Legal background

This is background for the owner's decision, not legal advice, and Tier 2 is where the owner's
standard rather than the law alone makes the call.

- **United States.** The DMCA's anti-circumvention rule (17 U.S.C. 1201) carves out reverse
  engineering of a lawfully obtained program to achieve interoperability of an independently
  created program (1201(f)) and security testing with the system owner's authorization (1201(j)).
  The Librarian of Congress's triennial rulemaking adds a good-faith security-research exemption.
  Separately, a no-reverse-engineering clause in a shrinkwrap or clickwrap license was held
  enforceable as a contract in Bowers v. Baystate Technologies, 320 F.3d 1317 (Fed. Cir. 2003),
  even where copyright law alone would have allowed the reverse engineering as fair use. The
  clause in a EULA is therefore a real term, not boilerplate.
- **European Union.** The Software Directive (2009/24/EC) lets the lawful acquirer observe,
  study, and test the program's functioning while using it (Article 5(3)), and decompile it where
  indispensable for the interoperability of an independently created program (Article 6, with its
  conditions). In Top System v Belgian State (C-13/20, October 2021) the Court of Justice held
  that the lawful acquirer may also decompile to correct errors affecting the program's
  functioning, resting that on the error-correction right in Article 5(1) rather than on Article
  6, so the Article 6 conditions do not apply to error correction; a contract cannot exclude
  error correction entirely, though it may set its terms.
- **What this means at Tier 2.** The crashing-client case sits inside the EU error-correction
  carve-out and, in the US, inside what a license can restrict. The file-format case is the
  interoperability carve-out on both sides. The owner decides with that in view; the agent
  supplies the sentence, not the verdict.

## Not an enforcer, restated

The agent declines Tier 3 once, plainly, offers the permitted path, and carries on. It does not
report, log, flag, or file the request, does not moralize, and does not withhold help on
anything else. The gate exists so that the agent reads what is the owner's to read and asks
before reading what is not; it is not a surveillance mechanism.
