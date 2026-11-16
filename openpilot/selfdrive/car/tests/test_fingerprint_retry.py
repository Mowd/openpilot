from types import SimpleNamespace

from openpilot.selfdrive.car.fingerprint_retry import FINGERPRINT_RETRIES, get_car_with_retries


def car(brand):
  return SimpleNamespace(CP=SimpleNamespace(brand=brand, carFw=[]))


def run(results):
  calls, sleeps = [], []

  def get_car():
    calls.append(1)
    return results[min(len(calls), len(results)) - 1]

  CI = get_car_with_retries(get_car, sleep=sleeps.append)
  return CI.CP.brand, len(calls), len(sleeps)


class TestFingerprintRetry:
  def test_recognized_first_time(self):
    assert run([car("mg")]) == ("mg", 1, 0)

  def test_recognized_on_retry(self):
    # an ECU missed the first query (engine cranking): the second one finds the car
    assert run([car("mock"), car("mg")]) == ("mg", 2, 1)

  def test_gives_up(self):
    assert run([car("mock")]) == ("mock", FINGERPRINT_RETRIES + 1, FINGERPRINT_RETRIES)
