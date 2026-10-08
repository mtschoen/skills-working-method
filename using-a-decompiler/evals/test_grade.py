import grade
import pytest


@pytest.mark.parametrize(
    ("payload", "required_assertions", "should_pass", "expected_error_substring"),
    [
        # Valid matching assertions
        (
            {
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "observed A"},
                    {"text": "B", "passed": False, "evidence": "did not observe B"},
                ],
                "universal": {"passed": True, "claims": []},
            },
            ["A", "B"],
            True,
            None,
        ),
        # Valid reordered assertions
        (
            {
                "assertions": [
                    {"text": "B", "passed": True, "evidence": "observed B"},
                    {"text": "A", "passed": False, "evidence": "did not observe A"},
                ],
                "universal": {"passed": True, "claims": []},
            },
            ["A", "B"],
            True,
            None,
        ),
        # Valid payload with well-formed claims
        pytest.param(
            {
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "observed A"},
                ],
                "universal": {
                    "passed": True,
                    "claims": [
                        {
                            "claim": "valid claim",
                            "type": "factual",
                            "verified": True,
                            "verification_note": "verified against mock repo",
                        },
                    ],
                },
            },
            ["A"],
            True,
            None,
            id="f1_8_valid_claims_payload",
        ),
        # Missing text
        (
            {
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "observed A"},
                ],
                "universal": {"passed": True, "claims": []},
            },
            ["A", "B"],
            False,
            "assertions count",
        ),
        # Duplicate text
        (
            {
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "observed A"},
                    {"text": "A", "passed": True, "evidence": "observed A again"},
                ],
                "universal": {"passed": True, "claims": []},
            },
            ["A", "B"],
            False,
            "do not match required assertions",
        ),
        # Unrelated text
        (
            {
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "observed A"},
                    {"text": "C", "passed": True, "evidence": "observed C"},
                ],
                "universal": {"passed": True, "claims": []},
            },
            ["A", "B"],
            False,
            "do not match required assertions",
        ),
        # Contradictory verdict: universal.passed=True with unverified claim
        (
            {
                "assertions": [
                    {"text": "A", "passed": True, "evidence": "observed A"},
                ],
                "universal": {
                    "passed": True,
                    "claims": [
                        {
                            "claim": "InventedFlag",
                            "type": "factual",
                            "verified": False,
                            "verification_note": "flag not in repo",
                        },
                    ],
                },
            },
            ["A"],
            False,
            "universal.passed cannot be true when claims contain unverified claims",
        ),
        # Malformed universal claim collection: null
        (
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {"passed": False, "claims": None},
            },
            ["A"],
            False,
            "universal.claims must be a list",
        ),
        # Malformed universal claim collection: integer
        (
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {"passed": False, "claims": 42},
            },
            ["A"],
            False,
            "universal.claims must be a list",
        ),
        # Malformed universal claim collection: boolean
        (
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {"passed": False, "claims": True},
            },
            ["A"],
            False,
            "universal.claims must be a list",
        ),
        # Malformed universal claim member: non-dict
        (
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {"passed": False, "claims": ["not-a-dict"]},
            },
            ["A"],
            False,
            "must be a JSON object",
        ),
        # Malformed universal claim member: non-boolean verified
        (
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {
                            "claim": "sample",
                            "type": "factual",
                            "verified": "unverified",
                            "verification_note": "note",
                        }
                    ],
                },
            },
            ["A"],
            False,
            ".verified must be a boolean",
        ),
        # Finding 1 (F1-8/F2-8): Missing claim field
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [{"type": "factual", "verified": True, "verification_note": "note"}],
                },
            },
            ["A"],
            False,
            ".claim must be a string",
            id="f1_8_claim_missing",
        ),
        # Finding 1 (F1-8/F2-8): Non-string claim: null
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {
                            "claim": None,
                            "type": "factual",
                            "verified": True,
                            "verification_note": "note",
                        }
                    ],
                },
            },
            ["A"],
            False,
            ".claim must be a string",
            id="f1_8_claim_null",
        ),
        # Finding 1 (F1-8/F2-8): Non-string claim: object
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {
                            "claim": {"nested": "value"},
                            "type": "factual",
                            "verified": True,
                            "verification_note": "note",
                        }
                    ],
                },
            },
            ["A"],
            False,
            ".claim must be a string",
            id="f1_8_claim_object",
        ),
        # Finding 1 (F1-8/F2-8): Missing type field
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {"claim": "flag exists", "verified": True, "verification_note": "note"}
                    ],
                },
            },
            ["A"],
            False,
            ".type must be one of",
            id="f1_8_type_missing",
        ),
        # Finding 1 (F1-8/F2-8): Non-string type: list
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {
                            "claim": "flag exists",
                            "type": [],
                            "verified": True,
                            "verification_note": "note",
                        }
                    ],
                },
            },
            ["A"],
            False,
            ".type must be one of",
            id="f1_8_type_list",
        ),
        # Finding 1 (F1-8/F2-8): Invalid type enum
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {
                            "claim": "flag exists",
                            "type": "invalid_enum",
                            "verified": True,
                            "verification_note": "note",
                        }
                    ],
                },
            },
            ["A"],
            False,
            ".type must be one of",
            id="f1_8_type_invalid_enum",
        ),
        # Finding 1 (F1-8/F2-8): Missing verification_note field
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [{"claim": "flag exists", "type": "factual", "verified": True}],
                },
            },
            ["A"],
            False,
            ".verification_note must be a string",
            id="f1_8_verification_note_missing",
        ),
        # Finding 1 (F1-8/F2-8): Non-string verification_note: null
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {
                            "claim": "flag exists",
                            "type": "factual",
                            "verified": True,
                            "verification_note": None,
                        }
                    ],
                },
            },
            ["A"],
            False,
            ".verification_note must be a string",
            id="f1_8_verification_note_null",
        ),
        # Finding 1 (F1-8/F2-8): Non-string verification_note: integer
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
                "universal": {
                    "passed": False,
                    "claims": [
                        {
                            "claim": "flag exists",
                            "type": "factual",
                            "verified": True,
                            "verification_note": 123,
                        }
                    ],
                },
            },
            ["A"],
            False,
            ".verification_note must be a string",
            id="f1_8_verification_note_integer",
        ),
        # Finding 2 (F1-8 assertion evidence): Missing assertion evidence
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True}],
                "universal": {"passed": True, "claims": []},
            },
            ["A"],
            False,
            ".evidence must be a string",
            id="f2_evidence_missing",
        ),
        # Finding 2 (F1-8 assertion evidence): Non-string evidence: null
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": None}],
                "universal": {"passed": True, "claims": []},
            },
            ["A"],
            False,
            ".evidence must be a string",
            id="f2_evidence_null",
        ),
        # Finding 2 (F1-8 assertion evidence): Non-string evidence: list
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": []}],
                "universal": {"passed": True, "claims": []},
            },
            ["A"],
            False,
            ".evidence must be a string",
            id="f2_evidence_list",
        ),
        # Finding 2 (F1-8 assertion evidence): Non-string evidence: boolean
        pytest.param(
            {
                "assertions": [{"text": "A", "passed": True, "evidence": False}],
                "universal": {"passed": True, "claims": []},
            },
            ["A"],
            False,
            ".evidence must be a string",
            id="f2_evidence_boolean",
        ),
    ],
)
def test_validate_grader_payload_validation(
    payload, required_assertions, should_pass, expected_error_substring
):
    validated, error = grade.validate_grader_payload(payload, required_assertions)
    if should_pass:
        assert error is None
        assert validated is not None
        assert "summary" in validated
        assert validated["summary"]["total"] == len(required_assertions)
    else:
        assert error is not None
        assert expected_error_substring in error


@pytest.mark.parametrize(
    ("override_payload", "expected_configuration", "expected_run", "expected_eval_id"),
    [
        # Overwriting configuration with a list: should be ignored and dropped
        ({"config": [], "run": "hacked-run", "eval_id": 999}, "with_skill", "run-1", 42),
        # Overwriting configuration with another string group: should be ignored and dropped
        ({"config": "without_skill", "eval_name": "other"}, "with_skill", "run-1", 42),
    ],
)
def test_grade_unit_metadata_overrides_prevented(
    tmp_path, monkeypatch, override_payload, expected_configuration, expected_run, expected_eval_id
):
    response_file = tmp_path / "response.md"
    response_file.write_text("dummy response", encoding="utf-8")
    grading_output = tmp_path / "grading.json"

    unit = grade.GradingUnit(
        eval_id=42,
        eval_name="test-eval",
        bucket="gate",
        kind="single-turn",
        config="with_skill",
        run="run-1",
        prior_context="none",
        user_message="test user message",
        response_path=response_file,
        output_grading_path=grading_output,
        assertions=["A"],
        universal_assertion="none",
        mock_repo="",
    )

    mock_grader_response = {
        "assertions": [{"text": "A", "passed": True, "evidence": "quote"}],
        "universal": {"passed": True, "claims": []},
        **override_payload,
    }

    monkeypatch.setattr(
        grade,
        "invoke_grader",
        lambda prompt, model, timeout: mock_grader_response,
    )

    record = grade.grade_unit(unit, model=None, timeout=60)
    assert record["config"] == expected_configuration
    assert record["run"] == expected_run
    assert record["eval_id"] == expected_eval_id
    assert record["eval_name"] == "test-eval"

    # Verify summarize can aggregate the record without TypeError
    summary = grade.summarize([record])
    assert summary["errored"] == 0
    assert summary["total_units_graded"] == 1
    assert summary["mean_pass_rate_with_skill"] == 1.0


@pytest.mark.parametrize(
    "status_content",
    [
        "[]",
        "null",
        "true",
        "1",
        '"ok"',
    ],
)
def test_discover_grading_units_status_non_object_shapes(tmp_path, status_content):
    run_dir = tmp_path / "run-0"
    outputs_dir = run_dir / "outputs"
    outputs_dir.mkdir(parents=True)
    (outputs_dir / "response.md").write_text("test response", encoding="utf-8")
    (run_dir / "status.json").write_text(status_content, encoding="utf-8")

    eval_entry = {
        "id": 1,
        "name": "eval-1",
        "kind": "single-turn",
        "user": "hi",
        "assertions": ["A"],
    }

    # Non-object status shapes must be skipped without AttributeError
    units = grade._units_for_run(run_dir, eval_entry, "with_skill", "universal")
    assert units == []
