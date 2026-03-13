datatype Candidate = Candidate(id: string)
datatype ScreeningEntry = ScreeningEntry(paper_id: string, decision: string)
datatype IncludedPaper = IncludedPaper(id: string)

function CandidateIsScreened(c: Candidate, screening_log: seq<ScreeningEntry>): bool
{
  exists i :: 0 <= i < |screening_log| && screening_log[i].paper_id == c.id && (screening_log[i].decision == "include" || screening_log[i].decision == "exclude")
}

function IncludedHasIncludeEntry(p: IncludedPaper, screening_log: seq<ScreeningEntry>): bool
{
  exists i :: 0 <= i < |screening_log| && screening_log[i].paper_id == p.id && screening_log[i].decision == "include"
}

function IncludedInCandidates(p: IncludedPaper, candidates: seq<Candidate>): bool
{
  exists i :: 0 <= i < |candidates| && candidates[i].id == p.id
}

method CheckAllCandidatesScreened(candidates: seq<Candidate>, screening_log: seq<ScreeningEntry>)
  returns (satisfied: bool, failures: seq<string>)
  ensures satisfied <==> (forall i :: 0 <= i < |candidates| ==> CandidateIsScreened(candidates[i], screening_log))
  ensures satisfied <==> |failures| == 0
  ensures forall f :: f in failures ==> exists i :: 0 <= i < |candidates| && candidates[i].id == f && !CandidateIsScreened(candidates[i], screening_log)
  ensures !satisfied ==> |failures| > 0
{
  var fails: seq<string> := [];
  var idx := 0;
  while idx < |candidates|
    invariant 0 <= idx <= |candidates|
    invariant forall f :: f in fails ==> exists i :: 0 <= i < idx && candidates[i].id == f && !CandidateIsScreened(candidates[i], screening_log)
    invariant forall i :: 0 <= i < idx && !CandidateIsScreened(candidates[i], screening_log) ==> candidates[i].id in fails
    invariant |fails| == 0 <==> (forall i :: 0 <= i < idx ==> CandidateIsScreened(candidates[i], screening_log))
  {
    var found := HasScreeningDecision(candidates[idx], screening_log);
    if !found {
      fails := fails + [candidates[idx].id];
    }
    idx := idx + 1;
  }
  failures := fails;
  satisfied := |failures| == 0;
}

method HasScreeningDecision(c: Candidate, screening_log: seq<ScreeningEntry>) returns (found: bool)
  ensures found <==> CandidateIsScreened(c, screening_log)
{
  var j := 0;
  found := false;
  while j < |screening_log|
    invariant 0 <= j <= |screening_log|
    invariant found <==> exists k :: 0 <= k < j && screening_log[k].paper_id == c.id && (screening_log[k].decision == "include" || screening_log[k].decision == "exclude")
  {
    if screening_log[j].paper_id == c.id && (screening_log[j].decision == "include" || screening_log[j].decision == "exclude") {
      found := true;
    }
    j := j + 1;
  }
}

method HasIncludeEntry(p: IncludedPaper, screening_log: seq<ScreeningEntry>) returns (found: bool)
  ensures found <==> IncludedHasIncludeEntry(p, screening_log)
{
  var j := 0;
  found := false;
  while j < |screening_log|
    invariant 0 <= j <= |screening_log|
    invariant found <==> exists k :: 0 <= k < j && screening_log[k].paper_id == p.id && screening_log[k].decision == "include"
  {
    if screening_log[j].paper_id == p.id && screening_log[j].decision == "include" {
      found := true;
    }
    j := j + 1;
  }
}

method HasCandidateMatch(p: IncludedPaper, candidates: seq<Candidate>) returns (found: bool)
  ensures found <==> IncludedInCandidates(p, candidates)
{
  var j := 0;
  found := false;
  while j < |candidates|
    invariant 0 <= j <= |candidates|
    invariant found <==> exists k :: 0 <= k < j && candidates[k].id == p.id
  {
    if candidates[j].id == p.id {
      found := true;
    }
    j := j + 1;
  }
}

method CheckIncludedConsistency(included: seq<IncludedPaper>, screening_log: seq<ScreeningEntry>)
  returns (satisfied: bool, failures: seq<string>)
  ensures satisfied <==> (forall i :: 0 <= i < |included| ==> IncludedHasIncludeEntry(included[i], screening_log))
  ensures satisfied <==> |failures| == 0
  ensures forall f :: f in failures ==> exists i :: 0 <= i < |included| && included[i].id == f && !IncludedHasIncludeEntry(included[i], screening_log)
  ensures !satisfied ==> |failures| > 0
{
  var fails: seq<string> := [];
  var idx := 0;
  while idx < |included|
    invariant 0 <= idx <= |included|
    invariant forall f :: f in fails ==> exists i :: 0 <= i < idx && included[i].id == f && !IncludedHasIncludeEntry(included[i], screening_log)
    invariant forall i :: 0 <= i < idx && !IncludedHasIncludeEntry(included[i], screening_log) ==> included[i].id in fails
    invariant |fails| == 0 <==> (forall i :: 0 <= i < idx ==> IncludedHasIncludeEntry(included[i], screening_log))
  {
    var found := HasIncludeEntry(included[idx], screening_log);
    if !found {
      fails := fails + [included[idx].id];
    }
    idx := idx + 1;
  }
  failures := fails;
  satisfied := |failures| == 0;
}

method CheckNoOrphanInclusions(included: seq<IncludedPaper>, candidates: seq<Candidate>)
  returns (satisfied: bool, failures: seq<string>)
  ensures satisfied <==> (forall i :: 0 <= i < |included| ==> IncludedInCandidates(included[i], candidates))
  ensures satisfied <==> |failures| == 0
  ensures forall f :: f in failures ==> exists i :: 0 <= i < |included| && included[i].id == f && !IncludedInCandidates(included[i], candidates)
  ensures !satisfied ==> |failures| > 0
{
  var fails: seq<string> := [];
  var idx := 0;
  while idx < |included|
    invariant 0 <= idx <= |included|
    invariant forall f :: f in fails ==> exists i :: 0 <= i < idx && included[i].id == f && !IncludedInCandidates(included[i], candidates)
    invariant forall i :: 0 <= i < idx && !IncludedInCandidates(included[i], candidates) ==> included[i].id in fails
    invariant |fails| == 0 <==> (forall i :: 0 <= i < idx ==> IncludedInCandidates(included[i], candidates))
  {
    var found := HasCandidateMatch(included[idx], candidates);
    if !found {
      fails := fails + [included[idx].id];
    }
    idx := idx + 1;
  }
  failures := fails;
  satisfied := |failures| == 0;
}

method CheckPhase2All(candidates: seq<Candidate>, screening_log: seq<ScreeningEntry>, included: seq<IncludedPaper>)
  returns (satisfied: bool, failures: seq<string>)
  // Soundness: if satisfied then all individual checks are satisfied
  ensures satisfied ==>
    (forall i :: 0 <= i < |candidates| ==> CandidateIsScreened(candidates[i], screening_log)) &&
    (forall i :: 0 <= i < |included| ==> IncludedHasIncludeEntry(included[i], screening_log)) &&
    (forall i :: 0 <= i < |included| ==> IncludedInCandidates(included[i], candidates))
  // Completeness: if any individual check fails, satisfied is false and failures non-empty
  ensures (!( forall i :: 0 <= i < |candidates| ==> CandidateIsScreened(candidates[i], screening_log)) ||
           !(forall i :: 0 <= i < |included| ==> IncludedHasIncludeEntry(included[i], screening_log)) ||
           !(forall i :: 0 <= i < |included| ==> IncludedInCandidates(included[i], candidates)))
          ==> (!satisfied && |failures| > 0)
  ensures satisfied <==> |failures| == 0
{
  var s1, f1 := CheckAllCandidatesScreened(candidates, screening_log);
  var s2, f2 := CheckIncludedConsistency(included, screening_log);
  var s3, f3 := CheckNoOrphanInclusions(included, candidates);

  satisfied := s1 && s2 && s3;
  failures := f1 + f2 + f3;

  if !s1 {
    assert |f1| > 0;
    assert f1[0] in failures;
  } else if !s2 {
    assert |f2| > 0;
    assert f2[0] in failures;
  } else if !s3 {
    assert |f3| > 0;
    assert f3[0] in failures;
  }
}

// Determinism lemma: the functions used are pure/deterministic by construction in Dafny.
// We state it as a trivial lemma for documentation.
lemma DeterminismCandidateScreened(c: Candidate, log: seq<ScreeningEntry>)
  ensures CandidateIsScreened(c, log) == CandidateIsScreened(c, log)
{}

lemma DeterminismIncludedEntry(p: IncludedPaper, log: seq<ScreeningEntry>)
  ensures IncludedHasIncludeEntry(p, log) == IncludedHasIncludeEntry(p, log)
{}

lemma DeterminismIncludedInCandidates(p: IncludedPaper, candidates: seq<Candidate>)
  ensures IncludedInCandidates(p, candidates) == IncludedInCandidates(p, candidates)
{}