// Scholar saturation metrics — formal specification.
// Companion to lib/saturation.py.

method DiscoverySaturation(included: nat, examined: nat) returns (num: nat, den: nat)
  ensures den == 0 ==> num == 0
  ensures den > 0 ==> num <= den
  ensures den == examined
  ensures num <= included
{
  den := examined;
  if examined == 0 {
    num := 0;
  } else {
    num := if included <= examined then included else examined;
  }
}

method ShouldTerminateDiscovery(num: nat, den: nat, threshNum: nat, threshDen: nat) returns (terminate: bool)
  requires den > 0
  requires threshDen > 0
  ensures terminate <==> (num * threshDen < threshNum * den)
{
  terminate := num * threshDen < threshNum * den;
}

method ConceptualSaturation(newInLastK: nat, total: nat) returns (num: nat, den: nat)
  ensures den == 0 ==> num == 0
  ensures den > 0 ==> num <= den
{
  den := total;
  if total == 0 {
    num := 0;
  } else {
    num := if newInLastK <= total then newInLastK else total;
  }
}

method ShouldFeedbackLoop(
  deltaNum: nat, deltaDen: nat,
  thetaNum: nat, thetaDen: nat,
  iterations: nat, maxIterations: nat
) returns (feedback: bool)
  requires deltaDen > 0
  requires thetaDen > 0
  ensures feedback <==> (deltaNum * thetaDen >= thetaNum * deltaDen && iterations < maxIterations)
{
  var aboveThreshold := deltaNum * thetaDen >= thetaNum * deltaDen;
  feedback := aboveThreshold && iterations < maxIterations;
}
