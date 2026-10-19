# New-sample construction validation

The completed [v1 study](v1_20261017/README.md) contains 69 graphs, 207 graph/parameter instances and 1,035 method observations. This is a separate construction/certificate experiment, not an extension of the timed 117-instance SAT/ILP cohort.

The five methods produce 907 valid labelings. The union of their certificates establishes 96 optima. Insertion ordering is effective on dense ER samples but does not dominate the coloring baseline overall. All failed searches remain in the archive. See the [experimental protocol and interpretation](../../../docs/experiments/certificate_validation.md).

`make certificate-validation-data` independently checks saved evidence and regenerates tables. It does not run either exact solver or repeat the construction experiment.
