// Stepwise Postconditions — Phase 5 (Synthesis)
// Verified properties: soundness, completeness, determinism

datatype CheckResult = CheckResult(satisfied: bool, failure_count: int)

// Check 1: All papers cited
method CheckAllPapersCited(
  included_count: int,
  cited_count: int
) returns (result: CheckResult)
  requires included_count >= 0
  requires cited_count >= 0
  ensures result.satisfied <==> cited_count >= included_count
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := cited_count >= included_count;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 2: All questions addressed
method CheckAllQuestionsAddressed(
  question_count: int,
  addressed_count: int
) returns (result: CheckResult)
  requires question_count >= 0
  requires addressed_count >= 0
  ensures result.satisfied <==> addressed_count >= question_count
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := addressed_count >= question_count;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 3: Question-answers complete
method CheckQuestionAnswersComplete(
  question_count: int,
  qa_count: int
) returns (result: CheckResult)
  requires question_count >= 0
  requires qa_count >= 0
  ensures result.satisfied <==> qa_count >= question_count
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := qa_count >= question_count;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 4: Bibliography consistent
method CheckBibliographyConsistent(
  bib_entry_count: int,
  citation_key_count: int
) returns (result: CheckResult)
  requires bib_entry_count >= 0
  requires citation_key_count >= 0
  ensures result.satisfied <==> bib_entry_count == citation_key_count
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := bib_entry_count == citation_key_count;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 5: Review structure
method CheckReviewStructure(
  required_headers: int,
  found_headers: int
) returns (result: CheckResult)
  requires required_headers >= 0
  requires found_headers >= 0
  ensures result.satisfied <==> found_headers >= required_headers
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := found_headers >= required_headers;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 6: Appendix A row count
method CheckAppendixRowCount(
  appendix_rows: int,
  included_count: int
) returns (result: CheckResult)
  requires appendix_rows >= 0
  requires included_count >= 0
  ensures result.satisfied <==> appendix_rows == included_count
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := appendix_rows == included_count;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Composite check
method CheckPhase5All(
  included_count: int,
  cited_count: int,
  question_count: int,
  addressed_count: int,
  qa_count: int,
  bib_entry_count: int,
  citation_key_count: int,
  required_headers: int,
  found_headers: int,
  appendix_rows: int
) returns (result: CheckResult)
  requires included_count >= 0
  requires cited_count >= 0
  requires question_count >= 0
  requires addressed_count >= 0
  requires qa_count >= 0
  requires bib_entry_count >= 0
  requires citation_key_count >= 0
  requires required_headers >= 0
  requires found_headers >= 0
  requires appendix_rows >= 0
  // Soundness
  ensures result.satisfied ==>
    cited_count >= included_count &&
    addressed_count >= question_count &&
    qa_count >= question_count &&
    bib_entry_count == citation_key_count &&
    found_headers >= required_headers &&
    appendix_rows == included_count
  // Completeness
  ensures (cited_count < included_count ||
           addressed_count < question_count ||
           qa_count < question_count ||
           bib_entry_count != citation_key_count ||
           found_headers < required_headers ||
           appendix_rows != included_count)
          ==> !result.satisfied
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count >= 1
{
  var r1 := CheckAllPapersCited(included_count, cited_count);
  var r2 := CheckAllQuestionsAddressed(question_count, addressed_count);
  var r3 := CheckQuestionAnswersComplete(question_count, qa_count);
  var r4 := CheckBibliographyConsistent(bib_entry_count, citation_key_count);
  var r5 := CheckReviewStructure(required_headers, found_headers);
  var r6 := CheckAppendixRowCount(appendix_rows, included_count);
  var sat := r1.satisfied && r2.satisfied && r3.satisfied && r4.satisfied && r5.satisfied && r6.satisfied;
  var fc := r1.failure_count + r2.failure_count + r3.failure_count + r4.failure_count + r5.failure_count + r6.failure_count;
  result := CheckResult(sat, fc);
}
