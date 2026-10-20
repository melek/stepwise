// Stepwise orchestration decisions — companion to decide() in
// lib/orchestrate.py.
//
// Issue #29: the orchestrator stopped to ask about transitions the protocol
// already determined. decide() now computes every advance and stop; these
// lemmas pin down that it only stops when there is something to decide or
// recover from, and that its loops are bounded.

datatype Status = Pending | InProgress | Completed | Failed | NeedsRevision
datatype Action = Dispatch | Stop | Done
datatype StopKind = NoStop | Decision | Recovery

datatype St = St(phase: int, status: Status, retry: nat, feedback: nat)

datatype Ev = Ev(
  approved: bool,
  pcOk: bool,         // postconditions passed (meaningful when InProgress)
  included: nat,      // size of the included corpus
  expanding: bool,    // conceptual saturation >= threshold
  maxFeedback: nat
)

datatype Dec = Dec(action: Action, stop: StopKind, next: St, retried: bool)

const MaxRetries: nat := 1

function Start(s: St): Dec
{
  Dec(Dispatch, NoStop, St(s.phase, InProgress, s.retry, s.feedback), false)
}

// The phase is completed: apply the transition table.
function AfterCompletion(s: St, ev: Ev): Dec
  requires 1 <= s.phase <= 5
{
  if s.phase == 5 then Dec(Done, NoStop, s, false)
  else if s.phase == 2 && ev.included == 0 then
    Dec(Stop, Decision, St(2, NeedsRevision, s.retry, s.feedback), false)
  else if s.phase == 4 && ev.expanding && s.feedback < ev.maxFeedback then
    Start(St(3, Pending, 0, s.feedback + 1))
  else
    Start(St(s.phase + 1, Pending, 0, s.feedback))
}

function Decide(s: St, ev: Ev): Dec
  requires 0 <= s.phase <= 5
{
  if s.phase == 0 || !ev.approved then Dec(Stop, Decision, s, false)
  else if s.status == NeedsRevision then Dec(Stop, Decision, s, false)
  else if s.status == Failed then Dec(Stop, Recovery, s, false)
  else if s.status == Pending then Start(s)
  else if s.status == Completed then AfterCompletion(s, ev)
  else if !ev.pcOk then
    (if s.retry < MaxRetries
     then Dec(Dispatch, NoStop, St(s.phase, InProgress, s.retry + 1, s.feedback), true)
     else Dec(Stop, Recovery, St(s.phase, Failed, s.retry, s.feedback), false))
  else AfterCompletion(St(s.phase, Completed, s.retry, s.feedback), ev)
}

// ---- #29: no stops without something to decide or recover ----

// A clean postcondition pass never stops, except the empty-corpus fork.
lemma CleanPassNeverStops(s: St, ev: Ev)
  requires 1 <= s.phase <= 5 && s.status == InProgress
  requires ev.approved && ev.pcOk
  requires !(s.phase == 2 && ev.included == 0)
  ensures Decide(s, ev).action != Stop
{
}

// Every stop is one of two kinds, each with a specific cause.
lemma StopsAreDecisionsOrRecoveries(s: St, ev: Ev)
  requires 0 <= s.phase <= 5
  ensures Decide(s, ev).action == Stop ==>
    (Decide(s, ev).stop == Decision &&
       (s.phase == 0 || !ev.approved || s.status == NeedsRevision ||
        (s.phase == 2 && ev.included == 0 &&
         (s.status == Completed || (s.status == InProgress && ev.pcOk)))))
    || (Decide(s, ev).stop == Recovery &&
       (s.status == Failed || (s.status == InProgress && !ev.pcOk && s.retry >= MaxRetries)))
{
}

// Dispatch and Done never carry a stop kind.
lemma NonStopsAreUnlabelled(s: St, ev: Ev)
  requires 0 <= s.phase <= 5
  ensures Decide(s, ev).action != Stop ==> Decide(s, ev).stop == NoStop
{
}

// ---- Bounds ----

// At most one automatic retry per phase.
lemma RetryBound(s: St, ev: Ev)
  requires 0 <= s.phase <= 5 && s.retry <= MaxRetries
  ensures Decide(s, ev).next.retry <= MaxRetries
  ensures Decide(s, ev).retried ==> s.retry == 0 && Decide(s, ev).next.phase == s.phase
{
}

// Feedback loops never exceed the protocol's maximum.
lemma FeedbackBound(s: St, ev: Ev)
  requires 0 <= s.phase <= 5 && s.feedback <= ev.maxFeedback
  ensures Decide(s, ev).next.feedback <= ev.maxFeedback
{
}

// Forward progress: after a clean pass the run moves on, either to the next
// phase or (Phase 4 only) back to snowballing, and never skips a phase.
lemma CleanPassProgresses(s: St, ev: Ev)
  requires 1 <= s.phase <= 4 && s.status == InProgress && ev.approved && ev.pcOk
  requires !(s.phase == 2 && ev.included == 0)
  ensures Decide(s, ev).action == Dispatch
  ensures Decide(s, ev).next.phase == s.phase + 1 ||
          (s.phase == 4 && Decide(s, ev).next.phase == 3)
{
}
