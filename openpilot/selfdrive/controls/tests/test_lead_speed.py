from types import SimpleNamespace

from openpilot.selfdrive.controls.lib.lead_speed import A_START, RELEASE_DELAY, T_AHEAD, V_LEAD_WINDOW, LeadSpeed


def model(a, v_lead=None, v_ego=17.0):
  leads = [] if v_lead is None else [SimpleNamespace(v=[v_lead])]
  return SimpleNamespace(action=SimpleNamespace(desiredAcceleration=a), leadsV3=leads, velocity=SimpleNamespace(x=[v_ego]))


def run(ls, a, v=17.0, has_lead=True, frames=40, v_lead=None):
  out = 0.0
  for _ in range(frames):
    out = ls.update(True, v, model(a, v_lead, v), has_lead, True)
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

  def test_not_below_the_lead(self):
    # MG ZS route 41: 49 km/h behind a lead slowing to ~33 km/h, the model wants -1.7 m/s^2: the target stays at the
    # lead's speed instead of 49 - 24 = 25 km/h, so the ACC doesn't fall back behind the lead once it stops slowing
    ls = LeadSpeed()
    assert abs(run(ls, -1.7, v=49 / 3.6, v_lead=33 / 3.6) - 33 / 3.6) < 0.1
    # a stopping lead: the target goes down with it (to the planned 30 km/h - 1.7 m/s^2 * T_AHEAD)
    assert abs(run(ls, -1.7, v=30 / 3.6, v_lead=2 / 3.6) - (30 / 3.6 - 1.7 * T_AHEAD)) < 0.1

  def test_lowest_lead_speed(self):
    # the camera's lead speed jumps: the floor uses its lowest value over the last V_LEAD_WINDOW
    ls = LeadSpeed()
    for i in range(round(V_LEAD_WINDOW / 0.05)):
      ls.update(True, 15.0, model(-3.0, 8.0 if i % 4 == 0 else 12.0, 15.0), True, True)
    assert abs(ls.target - 8.0) < 0.1

  def test_lead_speed_relative_to_the_model(self):
    # the model's ego speed is a little higher than vEgo: its lead speed counts relative to it, like radard
    ls = LeadSpeed()
    for _ in range(40):
      ls.update(True, 13.0, model(-2.0, 10.0, 14.0), True, True)
    assert abs(ls.target - 9.0) < 0.1
