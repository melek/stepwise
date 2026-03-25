datatype Option<T> = None | Some(value: T)

datatype ProtocolQuery = ProtocolQuery(database: string, query: string)

datatype SearchLogEntry = SearchLogEntry(database: string, query: string)

datatype Candidate = Candidate(
  id: string,
  title: Option<string>,
  abstract_text: Option<string>,
  authors: seq<string>,
  year: Option<int>
)

datatype CheckResult = CheckResult(satisfied: bool, failures: seq<string>)

// ---- Count-based query matching ----
// For each database in protocol queries, the search log must contain
// at least as many entries for that database.

function CountEntriesForDb(db: string, entries: seq<SearchLogEntry>, idx: nat): nat
  requires idx <= |entries|
  decreases |entries| - idx
{
  if idx == |entries| then 0
  else
    var rest := CountEntriesForDb(db, entries, idx + 1);
    if entries[idx].database == db then 1 + rest
    else rest
}

function CountProtocolQueriesForDb(db: string, queries: seq<ProtocolQuery>, idx: nat): nat
  requires idx <= |queries|
  decreases |queries| - idx
{
  if idx == |queries| then 0
  else
    var rest := CountProtocolQueriesForDb(db, queries, idx + 1);
    if queries[idx].database == db then 1 + rest
    else rest
}

function CollectDatabases(queries: seq<ProtocolQuery>, idx: nat): set<string>
  requires idx <= |queries|
  decreases |queries| - idx
{
  if idx == |queries| then {}
  else {queries[idx].database} + CollectDatabases(queries, idx + 1)
}

function CheckQueryCountsHelper(databases: set<string>, protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>): seq<string>
{
  // For each database, check count. Since sets are unordered, we check all at once.
  // A database fails if log count < protocol count.
  var failures := set db | db in databases &&
    CountEntriesForDb(db, search_log, 0) < CountProtocolQueriesForDb(db, protocol_queries, 0);
  // Convert set of failing databases to a sequence of failure messages
  SetToFailures(failures)
}

// Convert a set of failing database names to a sequence of failure strings
function SetToFailures(dbs: set<string>): seq<string>
{
  if dbs == {} then []
  else
    var db :| db in dbs;
    ["Database " + db + ": insufficient queries"] + SetToFailures(dbs - {db})
}

predicate AllDbCountsSatisfied(databases: set<string>, protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>)
{
  forall db :: db in databases ==>
    CountEntriesForDb(db, search_log, 0) >= CountProtocolQueriesForDb(db, protocol_queries, 0)
}

function CheckQueryCountsPerDatabase(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>): CheckResult
{
  var databases := CollectDatabases(protocol_queries, 0);
  var failures := CheckQueryCountsHelper(databases, protocol_queries, search_log);
  CheckResult(|failures| == 0, failures)
}

function CheckCandidatesNonEmpty(candidates: seq<Candidate>): CheckResult
{
  if |candidates| > 0 then CheckResult(true, [])
  else CheckResult(false, ["Candidates list is empty"])
}

function IdExistsInPrefix(candidates: seq<Candidate>, id: string, upTo: nat): bool
  requires upTo <= |candidates|
{
  exists j :: 0 <= j < upTo && candidates[j].id == id
}

function CheckNoDuplicateIdsHelper(candidates: seq<Candidate>, idx: nat): seq<string>
  requires idx <= |candidates|
  decreases |candidates| - idx
{
  if idx == |candidates| then []
  else
    var rest := CheckNoDuplicateIdsHelper(candidates, idx + 1);
    if IdExistsInPrefix(candidates, candidates[idx].id, idx) then
      ["Duplicate id: " + candidates[idx].id] + rest
    else
      rest
}

function CheckNoDuplicateIds(candidates: seq<Candidate>): CheckResult
{
  var failures := CheckNoDuplicateIdsHelper(candidates, 0);
  CheckResult(|failures| == 0, failures)
}

function CheckMinimumMetadataSingle(c: Candidate): seq<string>
{
  var idFail := if c.id == "" then ["Candidate '' missing: id"] else [];
  var titleFail := if c.title.None? then ["Candidate '" + c.id + "' missing: title"] else [];
  var abstractFail := if c.abstract_text.None? then ["Candidate '" + c.id + "' missing: abstract"] else [];
  var authorsFail := if |c.authors| == 0 then ["Candidate '" + c.id + "' missing: authors"] else [];
  var yearFail := if c.year.None? then ["Candidate '" + c.id + "' missing: year"] else [];
  idFail + titleFail + abstractFail + authorsFail + yearFail
}

function CandidateHasAllMetadata(c: Candidate): bool
{
  c.id != "" && c.title.Some? && c.abstract_text.Some? && |c.authors| > 0 && c.year.Some?
}

function CheckMinimumMetadataHelper(candidates: seq<Candidate>, idx: nat): seq<string>
  requires idx <= |candidates|
  decreases |candidates| - idx
{
  if idx == |candidates| then []
  else
    CheckMinimumMetadataSingle(candidates[idx]) + CheckMinimumMetadataHelper(candidates, idx + 1)
}

function CheckMinimumMetadata(candidates: seq<Candidate>): CheckResult
{
  var failures := CheckMinimumMetadataHelper(candidates, 0);
  CheckResult(|failures| == 0, failures)
}

function CheckPhase1All(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, candidates: seq<Candidate>): CheckResult
{
  var r1 := CheckQueryCountsPerDatabase(protocol_queries, search_log);
  var r2 := CheckCandidatesNonEmpty(candidates);
  var r3 := CheckNoDuplicateIds(candidates);
  var r4 := CheckMinimumMetadata(candidates);
  var allSatisfied := r1.satisfied && r2.satisfied && r3.satisfied && r4.satisfied;
  var allFailures := r1.failures + r2.failures + r3.failures + r4.failures;
  CheckResult(allSatisfied, allFailures)
}

// ---- Helper lemmas ----

lemma SetToFailuresEmpty(dbs: set<string>)
  ensures dbs == {} ==> SetToFailures(dbs) == []
{
}

lemma SetToFailuresNonEmpty(dbs: set<string>)
  ensures dbs != {} ==> |SetToFailures(dbs)| > 0
{
  if dbs != {} {
    var db :| db in dbs;
  }
}

lemma CheckQueryCountsHelperSatisfied(databases: set<string>, protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>)
  ensures AllDbCountsSatisfied(databases, protocol_queries, search_log) ==>
          |CheckQueryCountsHelper(databases, protocol_queries, search_log)| == 0
{
  if AllDbCountsSatisfied(databases, protocol_queries, search_log) {
    var failing := set db | db in databases &&
      CountEntriesForDb(db, search_log, 0) < CountProtocolQueriesForDb(db, protocol_queries, 0);
    assert failing == {};
    SetToFailuresEmpty(failing);
  }
}

lemma CheckQueryCountsHelperUnsatisfied(databases: set<string>, protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>)
  ensures !AllDbCountsSatisfied(databases, protocol_queries, search_log) ==>
          |CheckQueryCountsHelper(databases, protocol_queries, search_log)| > 0
{
  if !AllDbCountsSatisfied(databases, protocol_queries, search_log) {
    var failing := set db | db in databases &&
      CountEntriesForDb(db, search_log, 0) < CountProtocolQueriesForDb(db, protocol_queries, 0);
    assert failing != {};
    SetToFailuresNonEmpty(failing);
  }
}

lemma CheckNoDuplicateIdsHelperNonEmpty(candidates: seq<Candidate>, idx: nat)
  requires idx <= |candidates|
  ensures (exists k :: idx <= k < |candidates| && IdExistsInPrefix(candidates, candidates[k].id, k)) ==>
          |CheckNoDuplicateIdsHelper(candidates, idx)| > 0
  decreases |candidates| - idx
{
  if idx < |candidates| {
    CheckNoDuplicateIdsHelperNonEmpty(candidates, idx + 1);
  }
}

lemma MetadataSingleNonEmpty(c: Candidate)
  ensures !CandidateHasAllMetadata(c) ==> |CheckMinimumMetadataSingle(c)| > 0
{
}

lemma CheckMinimumMetadataHelperNonEmpty(candidates: seq<Candidate>, idx: nat)
  requires idx <= |candidates|
  ensures (exists k :: idx <= k < |candidates| && !CandidateHasAllMetadata(candidates[k])) ==>
          |CheckMinimumMetadataHelper(candidates, idx)| > 0
  decreases |candidates| - idx
{
  if idx < |candidates| {
    CheckMinimumMetadataHelperNonEmpty(candidates, idx + 1);
    if !CandidateHasAllMetadata(candidates[idx]) {
      MetadataSingleNonEmpty(candidates[idx]);
    }
  }
}

// ---- Soundness ----

lemma Soundness(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, candidates: seq<Candidate>)
  ensures CheckPhase1All(protocol_queries, search_log, candidates).satisfied ==>
          (CheckQueryCountsPerDatabase(protocol_queries, search_log).satisfied &&
           CheckCandidatesNonEmpty(candidates).satisfied &&
           CheckNoDuplicateIds(candidates).satisfied &&
           CheckMinimumMetadata(candidates).satisfied)
{
}

// ---- Completeness ----

lemma CompletenessQueries(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, candidates: seq<Candidate>)
  ensures !CheckQueryCountsPerDatabase(protocol_queries, search_log).satisfied ==>
          (!CheckPhase1All(protocol_queries, search_log, candidates).satisfied &&
           |CheckPhase1All(protocol_queries, search_log, candidates).failures| > 0)
{
}

lemma CompletenessNonEmpty(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, candidates: seq<Candidate>)
  ensures !CheckCandidatesNonEmpty(candidates).satisfied ==>
          (!CheckPhase1All(protocol_queries, search_log, candidates).satisfied &&
           |CheckPhase1All(protocol_queries, search_log, candidates).failures| > 0)
{
}

lemma CompletenessNoDups(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, candidates: seq<Candidate>)
  ensures !CheckNoDuplicateIds(candidates).satisfied ==>
          (!CheckPhase1All(protocol_queries, search_log, candidates).satisfied &&
           |CheckPhase1All(protocol_queries, search_log, candidates).failures| > 0)
{
}

lemma CompletenessMetadata(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, candidates: seq<Candidate>)
  ensures !CheckMinimumMetadata(candidates).satisfied ==>
          (!CheckPhase1All(protocol_queries, search_log, candidates).satisfied &&
           |CheckPhase1All(protocol_queries, search_log, candidates).failures| > 0)
{
}

// ---- Determinism ----

lemma Determinism(pq1: seq<ProtocolQuery>, sl1: seq<SearchLogEntry>, c1: seq<Candidate>,
                  pq2: seq<ProtocolQuery>, sl2: seq<SearchLogEntry>, c2: seq<Candidate>)
  requires pq1 == pq2 && sl1 == sl2 && c1 == c2
  ensures CheckPhase1All(pq1, sl1, c1) == CheckPhase1All(pq2, sl2, c2)
{
}
