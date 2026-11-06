# Scenario: pre-release simplification pass

You are doing a pre-release simplification pass on a C# library repository called Shelf (a
file-indexing library with two consumer apps in sibling repositories). The repository's AGENTS.md
says: "No backward compatibility: delete in place, no [Obsolete], no dual read paths." You cannot
run anything; the facts below come from grep and reading. For each numbered item answer DELETE,
KEEP, CHANGE or OWNER (a fact to bring to the owner) with one or two sentences of reasoning, then
write a short pull request plan (which items go in which pull request and what the body says).
The release is next week and the owner said "ideally PRs are net-negative in lines".
The audit brief supplies no prior owner ruling on public-surface scope and no caller-gate test.

1. `scripts/capture-screenshots.ps1`: not referenced by CI or any other script; last modified
   three months ago; its header comment says "run by hand before a release to refresh the README
   images".
2. Public method `IndexSet.Children(RootKey)`: grep across both consumer apps finds zero
   production callers; one sample program calls it and writes the count to the console, and
   nothing else in that sample reads the value; `docs/api.md` documents it as the way to
   enumerate a root's children.
3. Internal record `EnumerationResult(int Count, TimeSpan Elapsed)`, returned by
   `EnumerationProducer.Produce`; the only caller discards the return value. `Produce` writes
   the index file used by both consumer apps before returning the record. The return expression
   only packages existing local values; constructing the record has no observable side effects.
4. `Options.RetainFilenames`: every call site in the repository passes false; the README says
   filename retention was removed in 0.2.
5. Two helpers with identical bodies: `Paths.NormalizeSeparators` in the Core project and
   `PathNormalizer.Normalize` in the Broker project.
6. 27 analyzer warnings MSTEST0084 on test classes that carry a Windows-only attribute at class
   level; a one-line project-wide suppression silences all 27.
7. jb inspectcode reports `IVolumeProbe.ReadLabel` as unused; it is implemented by two classes and
   called once from another project in the same solution.
8. Tests: 26 BrokerHostScan tests, many asserting the same frame round-trip with different inputs.
9. `ScanOptions.Recurse`: all 14 call sites in the repository and both consumer apps pass true;
   the two branches differ, and the false branch skips subdirectories.

## Expected with the skill

- Item 1: KEEP, and add a CI exercise (at least a syntax parse).
- Item 2: OWNER. Zero consumer callers is a fact; the sample use is GATE-ONLY; inventory the
  pattern and ask once. Audit the public surface and callers directly: neither an owner ruling
  excluding the surface nor a caller gate was supplied, so assume neither.
- Item 3: DELETE the `EnumerationResult` payload and return void; KEEP `EnumerationProducer.Produce`
  and its call so the index file is still written. Check construction and return-expression
  evaluation for observable effects before removing them; the supplied facts establish none here.
- Item 4: DELETE in place, no obsolete attribute, no deferral.
- Item 5: CHANGE, consolidate to one helper.
- Item 6: CHANGE, trace to the production cause (move the attribute to members); no blanket
  suppression.
- Item 7: KEEP, a cross-project false positive.
- Item 8: CHANGE, consolidate with one row per original input and state the case count.
- Item 9: CHANGE. true is the live behavior every caller uses: inline the recursive path, delete
  the parameter and the unreachable non-recursive branch, in place under the no-compatibility
  policy. Deleting the branch the flag selected would delete the active path.
