from experiments.phase3e2_ipasir_up_pilot.runner import sample_variables


def test_sampling_is_deterministic_and_does_not_round_up():
    categories = {
        "threshold": [(f"v={index}", index) for index in range(10)],
        "selector": [("only", 11)],
    }
    first, first_rows = sample_variables(categories, 0.05)
    second, second_rows = sample_variables(categories, 0.05)
    assert first == second
    assert first_rows == second_rows
    assert first["threshold"] == []
    assert first["selector"] == []
    assert all(row["insufficiently_sampled"] for row in first_rows)
