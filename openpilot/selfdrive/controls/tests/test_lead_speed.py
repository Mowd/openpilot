from types import SimpleNamespace

from openpilot.selfdrive.controls.lib.lead_speed import A_START, RELEASE_DELAY, T_AHEAD, LeadSpeed


def model(a):
  return SimpleNamespace(action=SimpleNamespace(desiredAcceleration=a))


def run(ls, a, v=17.0, has_lead=True, frames=40):
  out = 0.0
  for _ in range(frames):
    out = ls.update(True, v, model(a), has_lead, True)
  return out


class TestLeadSpeed:
  def test_inactive_is_zero(self):
    assert LeadSpeed().update(False, 17.0, model(-2.0), True, True) == 0.0

  def test_no_target_when_cruising(self):
    ls = LeadSpeed()
    assert run(ls, 0.3) == 0.0
    assert not ls.slowing

  def test_mild_braking_is_ignored(self):
    # following normally: the model asks for a little braking now and then
    ls = LeadSpeed()
    assert run(ls, A_START + 0.2) == 0.0

  def test_slowing_for_a_lead(self):
    ls = LeadSpeed()
    target = run(ls, -1.0, v=17.0)
    assert ls.slowing
    assert abs(target - (17.0 - 1.0 * T_AHEAD)) < 0.2

  def test_needs_a_lead(self):
    # braking without a lead (curve, stop line) is left to the curve target
    ls = LeadSpeed()
    assert run(ls, -1.5, has_lead=False) == 0.0

  def test_hysteresis_and_release(self):
    ls = LeadSpeed()
    low = run(ls, -1.0)
    # still braking a bit: keep going, with a target that follows the milder braking
    kept = run(ls, -0.3, frames=10)
    assert ls.slowing
    assert low < kept < 17.0
    # no longer (the wanted acceleration is smoothed, ~1 s): hold the last target a moment, then let go
    held = run(ls, 0.3, frames=20)
    assert not ls.slowing
    assert held > 0.0
    assert run(ls, 0.3, frames=round(RELEASE_DELAY / 0.05)) == 0.0

  def test_flicker_keeps_one_slowdown(self):
    ls = LeadSpeed()
    run(ls, -1.0)
    for _ in range(3):
      assert run(ls, 0.3, frames=20) > 0.0  # released for 1 s
      assert run(ls, -1.0, frames=20) > 0.0  # and wanted again: still the same slowdown, no let go in between
