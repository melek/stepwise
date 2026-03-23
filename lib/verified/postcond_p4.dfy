// Stepwise Postconditions — Phase 4 (Extraction)
// Verified properties: soundness, completeness, determinism

datatype CheckResult = CheckResult(satisfied: bool, failure_count: int)

// Check 1: All papers extracted
method CheckAllPapersExtracted(
  included_count: int,
  extracted_count: int
) returns (result: CheckResult)
  requires included_count >= 0
  requires extracted_count >= 0
  ensures result.satisfied <==> extracted_count >= included_count
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := extracted_count >= included_count;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 2: Extraction schema valid
method CheckExtractionSchemaValid(
  total_extractions: int,
  valid_extractions: int
) returns (result: CheckResult)
  requires total_extractions >= 0
  requires valid_extractions >= 0
  ensures result.satisfied <==> valid_extractions >= total_extractions
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := valid_extractions >= total_extractions;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 3: Concepts non-empty
method CheckConceptsNonEmpty(
  concepts_count: int
) returns (result: CheckResult)
  requires concepts_count >= 0
  ensures result.satisfied <==> concepts_count > 0
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := concepts_count > 0;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 4: Concept matrix exists
method CheckConceptMatrixExists(
  matrix_exists: bool
) returns (result: CheckResult)
  ensures result.satisfied <==> matrix_exists
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  result := CheckResult(matrix_exists, if matrix_exists then 0 else 1);
}

// Check 5: All concepts defined
method CheckAllConceptsDefined(
  referenced_concepts: int,
  defined_concepts: int
) returns (result: CheckResult)
  requires referenced_concepts >= 0
  requires defined_concepts >= 0
  ensures result.satisfied <==> defined_concepts >= referenced_concepts
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := defined_concepts >= referenced_concepts;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 6: Saturation computed
method CheckSaturationComputed(
  has_saturation_event: bool
) returns (result: CheckResult)
  ensures result.satisfied <==> has_saturation_event
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  result := CheckResult(has_saturation_event, if has_saturation_event then 0 else 1);
}

// Composite check
method CheckPhase4All(
  included_count: int,
  extracted_count: int,
  total_extractions: int,
  valid_extractions: int,
  concepts_count: int,
  matrix_exists: bool,
  referenced_concepts: int,
  defined_concepts: int,
  has_saturation_event: bool
) returns (result: CheckResult)
  requires included_count >= 0
  requires extracted_count >= 0
  requires total_extractions >= 0
  requires valid_extractions >= 0
  requires concepts_count >= 0
  requires referenced_concepts >= 0
  requires defined_concepts >= 0
  // Soundness
  ensures result.satisfied ==>
    extracted_count >= included_count &&
    valid_extractions >= total_extractions &&
    concepts_count > 0 &&
    matrix_exists &&
    defined_concepts >= referenced_concepts &&
    has_saturation_event
  // Completeness
  ensures (extracted_count < included_count ||
           valid_extractions < total_extractions ||
           concepts_count == 0 ||
           !matrix_exists ||
           defined_concepts < referenced_concepts ||
           !has_saturation_event)
          ==> !result.satisfied
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count >= 1
{
  var r1 := CheckAllPapersExtracted(included_count, extracted_count);
  var r2 := CheckExtractionSchemaValid(total_extractions, valid_extractions);
  var r3 := CheckConceptsNonEmpty(concepts_count);
  var r4 := CheckConceptMatrixExists(matrix_exists);
  var r5 := CheckAllConceptsDefined(referenced_concepts, defined_concepts);
  var r6 := CheckSaturationComputed(has_saturation_event);
  var sat := r1.satisfied && r2.satisfied && r3.satisfied && r4.satisfied && r5.satisfied && r6.satisfied;
  var fc := r1.failure_count + r2.failure_count + r3.failure_count + r4.failure_count + r5.failure_count + r6.failure_count;
  result := CheckResult(sat, fc);
}
