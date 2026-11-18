from types import SimpleNamespace

from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.lead_moving_off import T_MOVING, LeadMovingOff


def model(v=0.8, prob=0.99, lead=True):
  leads = [SimpleNamespace(prob=prob, v=[v], x=[6.0])] if lead else []
  return SimpleNamespace(leadsV3=leads)


def run(l, m, seconds):
  out = False
  for _ in range(round(seconds / DT_MDL)):
    out = l.update(m, True)
  return out


class TestLeadMovingOff:
  def test_route_3e_creeping_lead(self):
    # HS route 3e: the lead crept off at 1-3 km/h while the planner still wanted to stop
    l = LeadMovingOff()
    assert not run(l, model(v=2.0 / 3.6), T_MOVING / 2)
    assert run(l, model(v=2.0 / 3.6), T_MOVING)

  def test_not_stopped_or_unsure(self):
    assert not run(LeadMovingOff(), model(v=0.1), 2.0)  # a stopped lead reads 0-0.15 m/s
    assert not run(LeadMovingOff(), model(prob=0.3), 2.0)
    assert not run(LeadMovingOff(), model(lead=False), 2.0)

  def test_must_keep_moving(self):
    l = LeadMovingOff()
    run(l, model(v=0.8), T_MOVING - DT_MDL)
    assert not l.update(model(v=0.0), True)
    assert not run(l, model(v=0.8), T_MOVING / 2)

  def test_holds_between_model_frames(self):
    l = LeadMovingOff()
    assert run(l, model(v=0.8), T_MOVING)
    assert l.update(model(v=0.0), False)  # no new model frame: keep the last answer
