// Scholar state machine — formal specification.
// Companion to lib/state.py. Python is the runtime; Dafny is the proof.

datatype PhaseStatus = Pending | InProgress | Completed | Failed | NeedsProtocolRevision

datatype State = State(
  currentPhase: nat,
  phaseStatus: PhaseStatus,
  feedbackIterations: nat,
  retryCount: nat,
  phaseCompleted: seq<bool>
)

const MAX_FEEDBACK_ITERATIONS: nat := 2

predicate ValidState(s: State) {
  0 <= s.currentPhase <= 5 &&
  |s.phaseCompleted| == 6 &&
  s.retryCount <= 1 &&
  s.feedbackIterations <= MAX_FEEDBACK_ITERATIONS
}

predicate MonotonicCompleted(before: seq<bool>, after: seq<bool>) {
  |before| == |after| == 6 &&
  forall i :: 0 <= i < 6 ==> (before[i] ==> after[i])
}

method StartPhase(s: State, phase: nat) returns (s': State)
  requires ValidState(s)
  requires phase == s.currentPhase
  requires s.phaseStatus == Pending
  ensures ValidState(s')
  ensures s'.phaseStatus == InProgress
  ensures s'.currentPhase == s.currentPhase
  ensures s'.phaseCompleted == s.phaseCompleted
{
  s' := State(s.currentPhase, InProgress, s.feedbackIterations, s.retryCount, s.phaseCompleted);
}

method CompletePhase(s: State, phase: nat) returns (s': State)
  requires ValidState(s)
  requires phase == s.currentPhase
  requires s.phaseStatus == InProgress
  requires 0 <= phase <= 5
  ensures ValidState(s')
  ensures s'.phaseStatus == Completed
  ensures s'.phaseCompleted[phase] == true
  ensures MonotonicCompleted(s.phaseCompleted, s'.phaseCompleted)
{
  var completed := s.phaseCompleted[..phase] + [true] + s.phaseCompleted[phase+1..];
  s' := State(s.currentPhase, Completed, s.feedbackIterations, s.retryCount, completed);
}

method TransitionToNext(s: State) returns (s': State)
  requires ValidState(s)
  requires s.phaseStatus == Completed
  requires s.currentPhase < 5
  ensures ValidState(s')
  ensures s'.currentPhase == s.currentPhase + 1
  ensures s'.phaseStatus == Pending
  ensures s'.retryCount == 0
  ensures MonotonicCompleted(s.phaseCompleted, s'.phaseCompleted)
{
  s' := State(s.currentPhase + 1, Pending, s.feedbackIterations, 0, s.phaseCompleted);
}

method FailPhase(s: State, phase: nat) returns (s': State)
  requires ValidState(s)
  requires phase == s.currentPhase
  requires s.phaseStatus == InProgress
  ensures ValidState(s')
  ensures s'.phaseStatus == Failed
{
  s' := State(s.currentPhase, Failed, s.feedbackIterations, s.retryCount, s.phaseCompleted);
}

method RetryPhase(s: State) returns (s': State)
  requires ValidState(s)
  requires s.phaseStatus == Failed
  requires s.retryCount < 1
  ensures ValidState(s')
  ensures s'.phaseStatus == InProgress
  ensures s'.retryCount == s.retryCount + 1
  ensures s'.retryCount <= 1
{
  s' := State(s.currentPhase, InProgress, s.feedbackIterations, s.retryCount + 1, s.phaseCompleted);
}

method FeedbackLoop(s: State) returns (s': State)
  requires ValidState(s)
  requires s.currentPhase == 4
  requires s.phaseStatus == Completed
  requires s.feedbackIterations < MAX_FEEDBACK_ITERATIONS
  ensures ValidState(s')
  ensures s'.currentPhase == 3
  ensures s'.phaseStatus == Pending
  ensures s'.feedbackIterations == s.feedbackIterations + 1
  ensures s'.feedbackIterations <= MAX_FEEDBACK_ITERATIONS
{
  s' := State(3, Pending, s.feedbackIterations + 1, 0, s.phaseCompleted);
}

method DiagnosticTransition(s: State) returns (s': State)
  requires ValidState(s)
  requires s.currentPhase == 2
  requires s.phaseStatus == Completed
  ensures ValidState(s')
  ensures s'.phaseStatus == NeedsProtocolRevision
{
  s' := State(s.currentPhase, NeedsProtocolRevision, s.feedbackIterations, s.retryCount, s.phaseCompleted);
}

predicate IsReviewComplete(s: State)
  requires ValidState(s)
{
  s.currentPhase == 5 && s.phaseStatus == Completed
}
