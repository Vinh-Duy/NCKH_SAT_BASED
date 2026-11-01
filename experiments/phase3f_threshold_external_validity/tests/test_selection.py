from experiments.phase3f_threshold_external_validity.runner import read_cohort


def test_selected_cohort_has_two_primary_graphs_per_family():
    cohort = read_cohort()
    assert len(cohort) == 8
    assert {row["family"] for row in cohort} == {
        "Tree", "BA", "ER p=0.15", "ER p=0.30"
    }
    for row in cohort:
        assert row["U"] == max(row["labels"].values())
        assert len(row["labels"]) == row["n"]
