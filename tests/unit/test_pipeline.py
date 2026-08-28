"""pipeline.prepare — spec/spec-feature-export-pipeline.md.

`prepare()` est le seam unique traversé par `export-file`, `push-hdh` et les
tests : lecture -> mapping -> validation SHACL -> décision, produisant une
séquence d'outcomes typés (Prepared / Unreadable / Rejected) plutôt que
d'écrire directement sur le terminal. La politique d'exclusion (strict/non
strict) est un paramètre de `prepare()`, pas une divergence entre deux
boucles."""

from __future__ import annotations

from dh_healthdcat.model import Severity
from dh_healthdcat.pipeline import Prepared, Rejected, Unreadable, prepare
from tests.fixtures.fake_datahub import (
    ALL_DATAPRODUCT_URNS,
    DATAPRODUCT_URN,
    NONCONFORMING_DATAPRODUCT_URN,
    UNREADABLE_DATAPRODUCT_URN,
    build_context,
)


def test_mixed_batch_yields_one_typed_outcome_per_dataproduct_in_order():
    ctx = build_context()

    outcomes = list(prepare(ctx, ALL_DATAPRODUCT_URNS))

    assert [type(o) for o in outcomes] == [Prepared, Unreadable, Rejected]
    assert [o.urn for o in outcomes] == ALL_DATAPRODUCT_URNS


def test_valid_dataproduct_is_prepared_with_a_conforming_graph():
    ctx = build_context()

    [outcome] = list(prepare(ctx, [DATAPRODUCT_URN]))

    assert isinstance(outcome, Prepared)
    assert outcome.shacl.conforms is True
    assert outcome.dataset.has_errors is False
    assert len(outcome.graph) > 0


def test_unreadable_dataproduct_carries_the_reader_reason():
    ctx = build_context()

    [outcome] = list(prepare(ctx, [UNREADABLE_DATAPRODUCT_URN]))

    assert isinstance(outcome, Unreadable)
    assert UNREADABLE_DATAPRODUCT_URN in outcome.reason


def test_strict_nonconforming_dataproduct_is_rejected_with_its_shacl_report():
    ctx = build_context()

    [outcome] = list(prepare(ctx, [NONCONFORMING_DATAPRODUCT_URN], strict=True))

    assert isinstance(outcome, Rejected)
    assert outcome.shacl.conforms is False
    assert outcome.dataset.has_errors is True


def test_non_strict_nonconforming_dataproduct_is_prepared_but_keeps_its_report():
    """story 4 : --no-strict force l'inclusion sans perdre le rapport
    d'issues ni le résultat SHACL — utile pour un export exploratoire."""

    ctx = build_context()

    [outcome] = list(prepare(ctx, [NONCONFORMING_DATAPRODUCT_URN], strict=False))

    assert isinstance(outcome, Prepared)
    assert outcome.shacl.conforms is False
    assert outcome.dataset.has_errors is True
    assert any(i.severity is Severity.ERROR for i in outcome.dataset.issues)


def test_regression_one_invalid_dataproduct_does_not_exclude_the_others():
    """Non-régression du correctif c244eff : un DataProduct invalide est
    exclu, pas le lot entier — les autres jeux sélectionnés restent Prepared."""

    ctx = build_context()

    outcomes = list(
        prepare(ctx, [NONCONFORMING_DATAPRODUCT_URN, DATAPRODUCT_URN, UNREADABLE_DATAPRODUCT_URN])
    )

    by_urn = {o.urn: o for o in outcomes}
    assert isinstance(by_urn[DATAPRODUCT_URN], Prepared)
    assert isinstance(by_urn[NONCONFORMING_DATAPRODUCT_URN], Rejected)
    assert isinstance(by_urn[UNREADABLE_DATAPRODUCT_URN], Unreadable)


def test_prepared_dataset_has_no_duplicate_error_issues():
    """Garde-fou : dataset_to_graph() enrichit dataset.issues en place, un
    double appel dupliquerait chaque ERROR. prepare() ne doit mapper qu'une
    fois par DataProduct."""

    ctx = build_context()

    [outcome] = list(prepare(ctx, [NONCONFORMING_DATAPRODUCT_URN], strict=False))

    by_property = [i.rdf_property for i in outcome.dataset.issues if i.severity is Severity.ERROR]
    assert len(by_property) == len(set(by_property))
