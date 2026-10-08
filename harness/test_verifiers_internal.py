"""Internal regression tests for the Store Agent harness verifier/scoring logic.

Claude-authored dev tests — NOT the graded 10-pt hand-tests (those are yours).
Pure functions only: no login, no network.

Run:
    python3 -m harness.test_verifiers_internal
    # or: pytest harness/test_verifiers_internal.py
"""
from harness.verifiers import _single_tenant, trace_recorded, _untied_count
from harness.four_fields import verification_of


def test_single_tenant_true_when_all_rows_one_company():
    assert _single_tenant([{"company_id": "C"}, {"company_id": "C"}]) is True


def test_single_tenant_false_when_two_companies_visible():
    assert _single_tenant([{"company_id": "C"}, {"company_id": "OTHER"}]) is False


def test_verification_na_when_agent_did_not_run():
    assert verification_of(ran=False, state={}, reread_key="disagreements") == "n/a"


def test_verification_verified_when_reread_field_present():
    assert verification_of(ran=True, state={"disagreements": [1]},
                           reread_key="disagreements") == "verified"


def test_verification_no_attempt_when_reread_field_absent():
    assert verification_of(ran=True, state={}, reread_key="disagreements") == "no_attempt"


def test_verification_verified_even_when_answer_is_an_empty_list():
    # a correct "no disagreements" answer is still a produced, verified answer
    assert verification_of(ran=True, state={"disagreements": []},
                           reread_key="disagreements") == "verified"


def test_trace_recorded_true_with_timings_and_order():
    assert trace_recorded({"timings": {"fetch": 0.1}, "dag_order": ["fetch"]}) is True


def test_trace_recorded_false_when_empty():
    assert trace_recorded({}) is False


def test_trace_recorded_false_without_dag_order():
    assert trace_recorded({"timings": {"fetch": 0.1}}) is False


def test_untied_count_flags_coupons_whose_used_count_mismatches_real_orders():
    coupons = [{"code": "A", "used_count": 5},   # phantom: claims 5 but no order uses it
               {"code": "B", "used_count": 0},   # tied: 0 claimed, 0 orders
               {"code": "C", "used_count": 2}]   # tied: 2 claimed, 2 orders
    orders = [{"coupon_code": "C"}, {"coupon_code": "C"}]
    assert _untied_count(coupons, orders) == 1   # only A is untied


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok:", fn.__name__)
    print(f"\n{len(fns)} passed")
