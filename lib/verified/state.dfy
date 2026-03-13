datatype PhaseStatus = Pending | InProgress | Completed | Failed | NeedsProtocolRevision

datatype State = State(
  current_phase: int,
  phase_status: PhaseStatus,
  feedback_iterations: int,
  retry_count: int,
  phase_completed: seq<bool>
)

predicate NoSkipping(pc: seq<bool>)
  requires |pc| == 6
{
  (pc[1] ==> pc[0]) &&
  (pc[2] ==> pc[1]) &&
  (pc[3] ==> pc[2]) &&
  (pc[4] ==> pc[3]) &&
  (pc[5] ==> pc[4])
}

predicate ValidState(s: State)
{
  0 <= s.current_phase <= 5 &&
  |s.phase_completed| == 6 &&
  s.feedback_iterations >= 0 &&
  s.retry_count >= 0 &&
  s.retry_count <= 1 &&
  NoSkipping(s.phase_completed)
}

predicate StrongValidState(s: State)
{
  ValidState(s) &&
  (forall i :: 0 <= i < s.current_phase ==> s.phase_completed[i] == true)
}

function InitState(): State
  ensures StrongValidState(InitState())
{
  var s := State(0, Pending, 0, 0, [false, false, false, false, false, false]);
  s
}

method StartPhase(s: State, phase: int) returns (s': State)
  requires StrongValidState(s)
  requires phase == s.current_phase
  requires s.phase_status == Pending
  ensures StrongValidState(s')
  ensures s'.current_phase == s.current_phase
  ensures s'.phase_status == InProgress
  ensures s'.feedback_iterations == s.feedback_iterations
  ensures s'.retry_count == s.retry_count
  ensures s'.phase_completed == s.phase_completed
{
  s' := s.(phase_status := InProgress);
}

method CompletePhase(s: State, phase: int) returns (s': State)
  requires StrongValidState(s)
  requires phase == s.current_phase
  requires s.phase_status == InProgress
  ensures StrongValidState(s')
  ensures s'.current_phase == s.current_phase
  ensures s'.phase_status == Completed
  ensures s'.phase_completed[phase] == true
  ensures s'.feedback_iterations == s.feedback_iterations
  ensures s'.retry_count == s.retry_count
  ensures |s'.phase_completed| == 6
  ensures forall i :: 0 <= i < 6 && i != phase ==> s'.phase_completed[i] == s.phase_completed[i]
{
  var new_pc := s.phase_completed[phase := true];

  assert new_pc[1] ==> new_pc[0] by {
    if phase == 0 { assert new_pc[0] == true; }
    else if phase == 1 { assert new_pc[0] == s.phase_completed[0]; assert 0 < s.current_phase || phase == 0; if phase >= 1 { assert 0 < phase; assert 0 < s.current_phase; assert s.phase_completed[0] == true; } }
    else { assert new_pc[1] == s.phase_completed[1]; assert new_pc[0] == s.phase_completed[0]; }
  }
  assert new_pc[2] ==> new_pc[1] by {
    if phase == 1 { assert new_pc[1] == true; }
    else if phase == 2 { assert new_pc[1] == s.phase_completed[1]; assert 1 < s.current_phase; assert s.phase_completed[1] == true; }
    else { assert new_pc[2] == s.phase_completed[2]; assert new_pc[1] == s.phase_completed[1]; }
  }
  assert new_pc[3] ==> new_pc[2] by {
    if phase == 2 { assert new_pc[2] == true; }
    else if phase == 3 { assert new_pc[2] == s.phase_completed[2]; assert 2 < s.current_phase; assert s.phase_completed[2] == true; }
    else { assert new_pc[3] == s.phase_completed[3]; assert new_pc[2] == s.phase_completed[2]; }
  }
  assert new_pc[4] ==> new_pc[3] by {
    if phase == 3 { assert new_pc[3] == true; }
    else if phase == 4 { assert new_pc[3] == s.phase_completed[3]; assert 3 < s.current_phase; assert s.phase_completed[3] == true; }
    else { assert new_pc[4] == s.phase_completed[4]; assert new_pc[3] == s.phase_completed[3]; }
  }
  assert new_pc[5] ==> new_pc[4] by {
    if phase == 4 { assert new_pc[4] == true; }
    else if phase == 5 { assert new_pc[4] == s.phase_completed[4]; assert 4 < s.current_phase; assert s.phase_completed[4] == true; }
    else { assert new_pc[5] == s.phase_completed[5]; assert new_pc[4] == s.phase_completed[4]; }
  }

  assert NoSkipping(new_pc);
  s' := s.(phase_status := Completed, phase_completed := new_pc);
}

method FailPhase(s: State, phase: int) returns (s': State)
  requires StrongValidState(s)
  requires phase == s.current_phase
  requires s.phase_status == InProgress
  ensures StrongValidState(s')
  ensures s'.current_phase == s.current_phase
  ensures s'.phase_status == Failed
  ensures s'.feedback_iterations == s.feedback_iterations
  ensures s'.retry_count == s.retry_count
  ensures s'.phase_completed == s.phase_completed
{
  s' := s.(phase_status := Failed);
}

method TransitionToNext(s: State) returns (s': State)
  requires StrongValidState(s)
  requires s.phase_status == Completed
  requires s.current_phase < 5
  requires s.phase_completed[s.current_phase] == true
  ensures StrongValidState(s')
  ensures s'.current_phase == s.current_phase + 1
  ensures s'.phase_status == Pending
  ensures s'.retry_count == 0
  ensures s'.feedback_iterations == s.feedback_iterations
  ensures s'.phase_completed == s.phase_completed
{
  s' := State(s.current_phase + 1, Pending, s.feedback_iterations, 0, s.phase_completed);
}

method DiagnosticTransition(s: State) returns (s': State)
  requires StrongValidState(s)
  requires s.current_phase == 2
  requires s.phase_status == Completed
  ensures StrongValidState(s')
  ensures s'.current_phase == s.current_phase
  ensures s'.phase_status == NeedsProtocolRevision
  ensures s'.feedback_iterations == s.feedback_iterations
  ensures s'.retry_count == s.retry_count
  ensures s'.phase_completed == s.phase_completed
{
  s' := s.(phase_status := NeedsProtocolRevision);
}

method FeedbackLoop(s: State, max_iterations: int) returns (s': State)
  requires StrongValidState(s)
  requires s.current_phase == 4
  requires s.phase_status == Completed
  requires s.feedback_iterations < max_iterations
  requires max_iterations > 0
  ensures StrongValidState(s')
  ensures s'.current_phase == 3
  ensures s'.phase_status == Pending
  ensures s'.feedback_iterations == s.feedback_iterations + 1
  ensures s'.feedback_iterations <= max_iterations
  ensures s'.retry_count == 0
  ensures s'.phase_completed == s.phase_completed
{
  s' := State(3, Pending, s.feedback_iterations + 1, 0, s.phase_completed);
}

method RetryPhase(s: State) returns (s': State)
  requires StrongValidState(s)
  requires s.phase_status == Failed
  requires s.retry_count < 1
  ensures StrongValidState(s')
  ensures s'.current_phase == s.current_phase
  ensures s'.phase_status == InProgress
  ensures s'.retry_count == s.retry_count + 1
  ensures s'.retry_count <= 1
  ensures s'.feedback_iterations == s.feedback_iterations
  ensures s'.phase_completed == s.phase_completed
{
  s' := s.(phase_status := InProgress, retry_count := s.retry_count + 1);
}

method IsReviewComplete(s: State) returns (result: bool)
  requires StrongValidState(s)
  ensures result == (s.current_phase == 5 && s.phase_status == Completed)
{
  result := s.current_phase == 5 && s.phase_status == Completed;
}

lemma ForwardProgressLemma(s: State, s': State)
  requires StrongValidState(s)
  requires s.phase_status == Completed
  requires s.current_phase < 5
  requires s.phase_completed[s.current_phase] == true
  requires s' == State(s.current_phase + 1, Pending, s.feedback_iterations, 0, s.phase_completed)
  ensures s'.current_phase == s.current_phase + 1
  ensures StrongValidState(s')
{
}

lemma NoSkippingLemma(s: State, n: int)
  requires StrongValidState(s)
  requires 1 <= n <= 5
  requires s.phase_completed[n] == true
  ensures s.phase_completed[n-1] == true
{
}

lemma FeedbackBoundLemma(s: State, max_iterations: int)
  requires StrongValidState(s)
  requires s.current_phase == 4
  requires s.phase_status == Completed
  requires s.feedback_iterations < max_iterations
  requires max_iterations > 0
  ensures s.feedback_iterations + 1 <= max_iterations
{
}

lemma RetryBoundLemma(s: State)
  requires StrongValidState(s)
  requires s.phase_status == Failed
  requires s.retry_count < 1
  ensures s.retry_count + 1 <= 1
{
}

lemma PhaseRangeLemma(s: State)
  requires StrongValidState(s)
  ensures 0 <= s.current_phase <= 5
{
}

lemma StatusValidityLemma(s: State)
  requires StrongValidState(s)
  ensures s.phase_status == Pending || s.phase_status == InProgress ||
          s.phase_status == Completed || s.phase_status == Failed ||
          s.phase_status == NeedsProtocolRevision
{
}