from newsdedup import load_state, save_state


def test_load_state_missing_file_returns_zero(tmp_path):
    state_file = tmp_path / "missing_state"

    assert load_state(str(state_file)) == 0


def test_save_and_load_state_round_trip(tmp_path):
    state_file = tmp_path / "state"

    save_state(1234, str(state_file))

    assert load_state(str(state_file)) == 1234


def test_load_state_ignores_corrupt_content(tmp_path):
    state_file = tmp_path / "state"
    state_file.write_text("not-a-number")

    assert load_state(str(state_file)) == 0
