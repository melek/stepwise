// Stepwise Phase 3 seed coverage — companion to check_all_seeds_examined()
// in lib/postconditions.py (issues #26, #27).
//
// postcond_p3.dfy proves the check's arithmetic over counts. This file
// models what is being counted: which papers must have been snowballed,
// and what counts as evidence that they were. A paper is the set of its
// canonical ID keys (ids.dfy); log entries carry canonical keys.

datatype Option<T> = None | Some(value: T)

datatype Direction = Forward | Backward

// discovered == None is an empty-result marker (issue #26).
datatype LogEntry = LogEntry(
  src: string,
  dir: Direction,
  depth: int,
  discovered: Option<string>,
  alreadyKnown: bool
)

// Deepest depth_level the log reached (0 for an empty log).
function Deepest(log: seq<LogEntry>): int
{
  if |log| == 0 then 0
  else
    var rest := Deepest(log[1..]);
    if log[0].depth > rest then log[0].depth else rest
}

// ---- Specification ----

// Terminal: newly discovered at the deepest level reached. Snowballing
// stopped there (depth cap or saturation), so it was never a seed.
predicate Terminal(paper: set<string>, log: seq<LogEntry>)
{
  exists e :: e in log && e.depth == Deepest(log) && e.discovered.Some?
    && e.discovered.value in paper && !e.alreadyKnown
}

// Evidence for a direction: any entry with the paper as its source,
// empty-result markers included.
predicate Examined(paper: set<string>, log: seq<LogEntry>, d: Direction)
{
  exists e :: e in log && e.dir == d && e.src in paper
}

predicate Covered(paper: set<string>, log: seq<LogEntry>)
{
  Terminal(paper, log) || (Examined(paper, log, Forward) && Examined(paper, log, Backward))
}

// ---- Implementation shape (as in the Python: key sets built once) ----

function TerminalKeys(log: seq<LogEntry>): set<string>
{
  set e | e in log && e.depth == Deepest(log) && e.discovered.Some? && !e.alreadyKnown :: e.discovered.value
}

function SourceKeys(log: seq<LogEntry>, d: Direction): set<string>
{
  set e | e in log && e.dir == d :: e.src
}

predicate Uncovered(paper: set<string>, log: seq<LogEntry>)
{
  paper * TerminalKeys(log) == {}
    && (paper * SourceKeys(log, Forward) == {} || paper * SourceKeys(log, Backward) == {})
}

function CountUncovered(seeds: seq<set<string>>, log: seq<LogEntry>): nat
{
  if |seeds| == 0 then 0
  else (if Uncovered(seeds[0], log) then 1 else 0) + CountUncovered(seeds[1..], log)
}

function CheckAllSeedsExamined(seeds: seq<set<string>>, log: seq<LogEntry>): bool
{
  CountUncovered(seeds, log) == 0
}

// ---- Implementation meets specification ----

lemma TerminalKeysSpec(paper: set<string>, log: seq<LogEntry>)
  ensures paper * TerminalKeys(log) != {} <==> Terminal(paper, log)
{
  if paper * TerminalKeys(log) != {} {
    var k :| k in paper * TerminalKeys(log);
    var e :| e in log && e.depth == Deepest(log) && e.discovered.Some? && !e.alreadyKnown && e.discovered.value == k;
  }
  if Terminal(paper, log) {
    var e :| e in log && e.depth == Deepest(log) && e.discovered.Some? && e.discovered.value in paper && !e.alreadyKnown;
    assert e.discovered.value in paper * TerminalKeys(log);
  }
}

lemma SourceKeysSpec(paper: set<string>, log: seq<LogEntry>, d: Direction)
  ensures paper * SourceKeys(log, d) != {} <==> Examined(paper, log, d)
{
  if paper * SourceKeys(log, d) != {} {
    var k :| k in paper * SourceKeys(log, d);
    var e :| e in log && e.dir == d && e.src == k;
  }
  if Examined(paper, log, d) {
    var e :| e in log && e.dir == d && e.src in paper;
    assert e.src in paper * SourceKeys(log, d);
  }
}

lemma UncoveredSpec(paper: set<string>, log: seq<LogEntry>)
  ensures Uncovered(paper, log) <==> !Covered(paper, log)
{
  TerminalKeysSpec(paper, log);
  SourceKeysSpec(paper, log, Forward);
  SourceKeysSpec(paper, log, Backward);
}

lemma CountZeroIffAllCovered(seeds: seq<set<string>>, log: seq<LogEntry>)
  ensures CountUncovered(seeds, log) == 0 <==> forall i :: 0 <= i < |seeds| ==> Covered(seeds[i], log)
{
  if |seeds| > 0 {
    UncoveredSpec(seeds[0], log);
    CountZeroIffAllCovered(seeds[1..], log);
    if forall i :: 0 <= i < |seeds| ==> Covered(seeds[i], log) {
      forall i | 0 <= i < |seeds| - 1 ensures Covered(seeds[1..][i], log) {
        assert seeds[1..][i] == seeds[i + 1];
      }
    }
    if CountUncovered(seeds, log) == 0 {
      forall i | 0 <= i < |seeds| ensures Covered(seeds[i], log) {
        if i > 0 { assert seeds[i] == seeds[1..][i - 1]; }
      }
    }
  }
}

// Soundness and completeness: the check passes exactly when every seed is
// terminal or has evidence in both directions.
lemma CheckSpec(seeds: seq<set<string>>, log: seq<LogEntry>)
  ensures CheckAllSeedsExamined(seeds, log) <==> forall i :: 0 <= i < |seeds| ==> Covered(seeds[i], log)
{
  CountZeroIffAllCovered(seeds, log);
}

// ---- Properties the fixes rely on ----

// #26: an empty-result marker is evidence for its direction.
lemma MarkerIsEvidence(paper: set<string>, log: seq<LogEntry>, i: int)
  requires 0 <= i < |log| && log[i].discovered.None? && log[i].src in paper
  ensures Examined(paper, log, log[i].dir)
{
  assert log[i] in log;
}

// #27: the exemption is only at the frontier. A paper discovered only above
// the deepest level reached was a seed for the next level, so a passing
// check means it was examined in both directions.
lemma ShallowDiscoveryMustBeSnowballed(seeds: seq<set<string>>, log: seq<LogEntry>, i: int)
  requires 0 <= i < |seeds|
  requires forall e :: e in log && e.discovered.Some? && e.discovered.value in seeds[i] ==> e.depth < Deepest(log)
  requires CheckAllSeedsExamined(seeds, log)
  ensures Examined(seeds[i], log, Forward) && Examined(seeds[i], log, Backward)
{
  CheckSpec(seeds, log);
  assert Covered(seeds[i], log);
}
