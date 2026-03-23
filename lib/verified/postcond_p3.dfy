// Stepwise Postconditions — Phase 3 (Snowballing)
// Verified properties: soundness, completeness, determinism

datatype CheckResult = CheckResult(satisfied: bool, failure_count: int)

// Check 1: Termination condition met
method CheckTerminationCondition(
  max_depth_reached: int,
  saturation_below_threshold: bool,
  max_depth: int
) returns (result: CheckResult)
  requires max_depth >= 0
  requires max_depth_reached >= 0
  ensures result.satisfied <==> (max_depth_reached >= max_depth || saturation_below_threshold)
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := max_depth_reached >= max_depth || saturation_below_threshold;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 2: All seeds examined
method CheckAllSeedsExamined(
  seed_count: int,
  seeds_with_forward: int,
  seeds_with_backward: int
) returns (result: CheckResult)
  requires seed_count >= 0
  requires seeds_with_forward >= 0
  requires seeds_with_backward >= 0
  ensures result.satisfied <==> (seeds_with_forward >= seed_count && seeds_with_backward >= seed_count)
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count >= 1
{
  var sat := seeds_with_forward >= seed_count && seeds_with_backward >= seed_count;
  var fc := 0;
  if seeds_with_forward < seed_count { fc := fc + 1; }
  if seeds_with_backward < seed_count { fc := fc + 1; }
  result := CheckResult(sat, fc);
}

// Check 3: Truncation logged
method CheckTruncationLogged(
  truncated_count: int,
  truncated_with_counts: int
) returns (result: CheckResult)
  requires truncated_count >= 0
  requires truncated_with_counts >= 0
  ensures result.satisfied <==> (truncated_count == truncated_with_counts)
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count == 1
{
  var sat := truncated_count == truncated_with_counts;
  result := CheckResult(sat, if sat then 0 else 1);
}

// Check 4: New inclusions recorded
method CheckNewInclusionsRecorded(
  snowball_includes: int,
  includes_in_included: int,
  includes_in_candidates: int
) returns (result: CheckResult)
  requires snowball_includes >= 0
  requires includes_in_included >= 0
  requires includes_in_candidates >= 0
  ensures result.satisfied <==> (snowball_includes == includes_in_included && snowball_includes == includes_in_candidates)
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count >= 1
{
  var sat := snowball_includes == includes_in_included && snowball_includes == includes_in_candidates;
  var fc := 0;
  if snowball_includes != includes_in_included { fc := fc + 1; }
  if snowball_includes != includes_in_candidates { fc := fc + 1; }
  result := CheckResult(sat, fc);
}

// Composite check: all four
method CheckPhase3All(
  max_depth_reached: int,
  saturation_below_threshold: bool,
  max_depth: int,
  seed_count: int,
  seeds_with_forward: int,
  seeds_with_backward: int,
  truncated_count: int,
  truncated_with_counts: int,
  snowball_includes: int,
  includes_in_included: int,
  includes_in_candidates: int
) returns (result: CheckResult)
  requires max_depth >= 0
  requires max_depth_reached >= 0
  requires seed_count >= 0
  requires seeds_with_forward >= 0
  requires seeds_with_backward >= 0
  requires truncated_count >= 0
  requires truncated_with_counts >= 0
  requires snowball_includes >= 0
  requires includes_in_included >= 0
  requires includes_in_candidates >= 0
  // Soundness: if satisfied, all individual checks pass
  ensures result.satisfied ==>
    (max_depth_reached >= max_depth || saturation_below_threshold) &&
    seeds_with_forward >= seed_count && seeds_with_backward >= seed_count &&
    truncated_count == truncated_with_counts &&
    snowball_includes == includes_in_included && snowball_includes == includes_in_candidates
  // Completeness: if any check fails, composite fails
  ensures (!(max_depth_reached >= max_depth || saturation_below_threshold) ||
           seeds_with_forward < seed_count || seeds_with_backward < seed_count ||
           truncated_count != truncated_with_counts ||
           snowball_includes != includes_in_included || snowball_includes != includes_in_candidates)
          ==> !result.satisfied
  ensures result.satisfied ==> result.failure_count == 0
  ensures !result.satisfied ==> result.failure_count >= 1
{
  var r1 := CheckTerminationCondition(max_depth_reached, saturation_below_threshold, max_depth);
  var r2 := CheckAllSeedsExamined(seed_count, seeds_with_forward, seeds_with_backward);
  var r3 := CheckTruncationLogged(truncated_count, truncated_with_counts);
  var r4 := CheckNewInclusionsRecorded(snowball_includes, includes_in_included, includes_in_candidates);
  var sat := r1.satisfied && r2.satisfied && r3.satisfied && r4.satisfied;
  var fc := r1.failure_count + r2.failure_count + r3.failure_count + r4.failure_count;
  result := CheckResult(sat, fc);
}
