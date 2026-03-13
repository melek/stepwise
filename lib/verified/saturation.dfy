datatype SnowballEntry = SnowballEntry(
  depth_level: int,
  screening_decision: string,
  already_known: bool
)

datatype ConceptEntry = ConceptEntry(
  concept_id: string,
  first_seen_in: string,
  first_seen_at: string
)

datatype Rational = Rational(num: int, denom: int)

function CountAtDepth(log: seq<SnowballEntry>, depth: int): int
  ensures CountAtDepth(log, depth) >= 0
{
  if |log| == 0 then 0
  else
    (if log[0].depth_level == depth then 1 else 0) + CountAtDepth(log[1..], depth)
}

function CountNewIncludesAtDepth(log: seq<SnowballEntry>, depth: int): int
  ensures CountNewIncludesAtDepth(log, depth) >= 0
{
  if |log| == 0 then 0
  else
    (if log[0].depth_level == depth && log[0].screening_decision == "include" && !log[0].already_known then 1 else 0)
    + CountNewIncludesAtDepth(log[1..], depth)
}

lemma NewIncludesLeqTotal(log: seq<SnowballEntry>, depth: int)
  ensures CountNewIncludesAtDepth(log, depth) <= CountAtDepth(log, depth)
{
  if |log| == 0 {
  } else {
    NewIncludesLeqTotal(log[1..], depth);
  }
}

function DiscoverySaturation(snowball_log: seq<SnowballEntry>, depth: int): Rational
  ensures DiscoverySaturation(snowball_log, depth).denom > 0
  ensures DiscoverySaturation(snowball_log, depth).num >= 0
  ensures DiscoverySaturation(snowball_log, depth).num <= DiscoverySaturation(snowball_log, depth).denom
{
  var total := CountAtDepth(snowball_log, depth);
  var newIncludes := CountNewIncludesAtDepth(snowball_log, depth);
  NewIncludesLeqTotal(snowball_log, depth);
  if total == 0 then Rational(0, 1)
  else Rational(newIncludes, total)
}

function CountConceptsInPapers(concepts: seq<ConceptEntry>, paper_ids: set<string>): int
  ensures CountConceptsInPapers(concepts, paper_ids) >= 0
{
  if |concepts| == 0 then 0
  else
    (if concepts[0].first_seen_in in paper_ids then 1 else 0)
    + CountConceptsInPapers(concepts[1..], paper_ids)
}

lemma ConceptsInPapersLeqTotal(concepts: seq<ConceptEntry>, paper_ids: set<string>)
  ensures CountConceptsInPapers(concepts, paper_ids) <= |concepts|
{
  if |concepts| == 0 {
  } else {
    ConceptsInPapersLeqTotal(concepts[1..], paper_ids);
  }
}

function ConceptualSaturation(concepts: seq<ConceptEntry>, last_k_paper_ids: set<string>): Rational
  ensures ConceptualSaturation(concepts, last_k_paper_ids).denom > 0
  ensures ConceptualSaturation(concepts, last_k_paper_ids).num >= 0
  ensures ConceptualSaturation(concepts, last_k_paper_ids).num <= ConceptualSaturation(concepts, last_k_paper_ids).denom
{
  var total := |concepts|;
  var newConcepts := CountConceptsInPapers(concepts, last_k_paper_ids);
  ConceptsInPapersLeqTotal(concepts, last_k_paper_ids);
  if total == 0 then Rational(0, 1)
  else Rational(newConcepts, total)
}

predicate RationalLt(a: Rational, b: Rational)
  requires a.denom > 0
  requires b.denom > 0
{
  a.num * b.denom < b.num * a.denom
}

function ShouldTerminateDiscovery(saturation: Rational, threshold: Rational): bool
  requires saturation.denom > 0
  requires threshold.denom > 0
{
  RationalLt(saturation, threshold)
}

predicate RationalGeq(a: Rational, b: Rational)
  requires a.denom > 0
  requires b.denom > 0
{
  a.num * b.denom >= b.num * a.denom
}

function ShouldFeedbackLoop(delta: Rational, theta_c: Rational, iterations: int, max_iterations: int): bool
  requires delta.denom > 0
  requires theta_c.denom > 0
  requires iterations >= 0
  requires max_iterations >= 0
{
  RationalGeq(delta, theta_c) && iterations < max_iterations
}

// Property: Range of DiscoverySaturation
lemma DiscoverySaturationRange(log: seq<SnowballEntry>, depth: int)
  ensures var r := DiscoverySaturation(log, depth);
          r.num >= 0 && r.denom > 0 && r.num <= r.denom
{
}

// Property: Range of ConceptualSaturation
lemma ConceptualSaturationRange(concepts: seq<ConceptEntry>, paper_ids: set<string>)
  ensures var r := ConceptualSaturation(concepts, paper_ids);
          r.num >= 0 && r.denom > 0 && r.num <= r.denom
{
}

// Property: Zero denominator safety for DiscoverySaturation
lemma DiscoverySaturationZeroSafe(log: seq<SnowballEntry>, depth: int)
  requires CountAtDepth(log, depth) == 0
  ensures DiscoverySaturation(log, depth) == Rational(0, 1)
{
}

// Property: Zero denominator safety for ConceptualSaturation
lemma ConceptualSaturationZeroSafe(concepts: seq<ConceptEntry>, paper_ids: set<string>)
  requires |concepts| == 0
  ensures ConceptualSaturation(concepts, paper_ids) == Rational(0, 1)
{
}

// Property: Threshold correctness
lemma ThresholdCorrectness(saturation: Rational, threshold: Rational)
  requires saturation.denom > 0
  requires threshold.denom > 0
  ensures ShouldTerminateDiscovery(saturation, threshold) <==> RationalLt(saturation, threshold)
{
}

// Property: Feedback bound
lemma FeedbackBound(delta: Rational, theta_c: Rational, iterations: int, max_iterations: int)
  requires delta.denom > 0
  requires theta_c.denom > 0
  requires iterations >= 0
  requires max_iterations >= 0
  requires iterations >= max_iterations
  ensures !ShouldFeedbackLoop(delta, theta_c, iterations, max_iterations)
{
}

// Property: Monotonicity of discovery — no new includes means saturation is 0
lemma NoNewIncludesMeansZero(log: seq<SnowballEntry>, depth: int)
  ensures CountNewIncludesAtDepth(log, depth) == 0 ==>
          DiscoverySaturation(log, depth).num == 0
{
  NewIncludesLeqTotal(log, depth);
}

// Helper: monotonicity implies termination for any non-negative threshold
lemma ZeroSaturationTerminates(log: seq<SnowballEntry>, depth: int, threshold: Rational)
  requires threshold.denom > 0
  requires threshold.num > 0
  requires CountNewIncludesAtDepth(log, depth) == 0
  ensures ShouldTerminateDiscovery(DiscoverySaturation(log, depth), threshold)
{
  NoNewIncludesMeansZero(log, depth);
  var sat := DiscoverySaturation(log, depth);
  assert sat.num == 0;
  assert sat.denom > 0;
  assert threshold.num > 0;
  assert threshold.denom > 0;
  assert sat.num * threshold.denom == 0;
  assert threshold.num * sat.denom > 0;
}