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

function QueryMatchExists(pq: ProtocolQuery, search_log: seq<SearchLogEntry>): bool
{
  exists i :: 0 <= i < |search_log| && search_log[i].database == pq.database && search_log[i].query == pq.query
}

function CheckAllQueriesExecutedHelper(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, idx: nat): (seq<string>)
  requires idx <= |protocol_queries|
  decreases |protocol_queries| - idx
{
  if idx == |protocol_queries| then []
  else
    var pq := protocol_queries[idx];
    var rest := CheckAllQueriesExecutedHelper(protocol_queries, search_log, idx + 1);
    if QueryMatchExists(pq, search_log) then rest
    else ["Unmatched query: (" + pq.database + ", " + pq.query + ")"] + rest
}

function CheckAllQueriesExecuted(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>): CheckResult
{
  var failures := CheckAllQueriesExecutedHelper(protocol_queries, search_log, 0);
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
  var r1 := CheckAllQueriesExecuted(protocol_queries, search_log);
  var r2 := CheckCandidatesNonEmpty(candidates);
  var r3 := CheckNoDuplicateIds(candidates);
  var r4 := CheckMinimumMetadata(candidates);
  var allSatisfied := r1.satisfied && r2.satisfied && r3.satisfied && r4.satisfied;
  var allFailures := r1.failures + r2.failures + r3.failures + r4.failures;
  CheckResult(allSatisfied, allFailures)
}

// ---- Lemmas for helper functions ----

lemma CheckAllQueriesExecutedHelperEmpty(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, idx: nat)
  requires idx <= |protocol_queries|
  ensures |CheckAllQueriesExecutedHelper(protocol_queries, search_log, idx)| == 0 ==>
          forall k :: idx <= k < |protocol_queries| ==> QueryMatchExists(protocol_queries[k], search_log)
  decreases |protocol_queries| - idx
{
  if idx < |protocol_queries| {
    CheckAllQueriesExecutedHelperEmpty(protocol_queries, search_log, idx + 1);
  }
}

lemma CheckAllQueriesExecutedHelperNonEmpty(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, idx: nat)
  requires idx <= |protocol_queries|
  ensures (exists k :: idx <= k < |protocol_queries| && !QueryMatchExists(protocol_queries[k], search_log)) ==>
          |CheckAllQueriesExecutedHelper(protocol_queries, search_log, idx)| > 0
  decreases |protocol_queries| - idx
{
  if idx < |protocol_queries| {
    CheckAllQueriesExecutedHelperNonEmpty(protocol_queries, search_log, idx + 1);
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
          (CheckAllQueriesExecuted(protocol_queries, search_log).satisfied &&
           CheckCandidatesNonEmpty(candidates).satisfied &&
           CheckNoDuplicateIds(candidates).satisfied &&
           CheckMinimumMetadata(candidates).satisfied)
{
}

// ---- Completeness ----

lemma CompletenessQueries(protocol_queries: seq<ProtocolQuery>, search_log: seq<SearchLogEntry>, candidates: seq<Candidate>)
  ensures !CheckAllQueriesExecuted(protocol_queries, search_log).satisfied ==>
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