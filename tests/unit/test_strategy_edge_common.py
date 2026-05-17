import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.strategy_edge_common import read_json_file, read_csv_rows, to_float_nan, to_float, to_bool


class TestReadJsonFile:
    def test_reads_valid_json_dict(self, tmp_path):
        path = tmp_path / "test.json"
        path.write_text(json.dumps({"key": "value", "num": 42}))
        result = read_json_file(path)
        assert result == {"key": "value", "num": 42}

    def test_returns_empty_dict_for_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        result = read_json_file(path)
        assert result == {}

    def test_returns_empty_dict_for_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not valid json {{{")
        result = read_json_file(path)
        assert result == {}

    def test_returns_empty_dict_for_json_array(self, tmp_path):
        path = tmp_path / "array.json"
        path.write_text(json.dumps([1, 2, 3]))
        result = read_json_file(path)
        assert result == {}

    def test_returns_empty_dict_for_empty_file(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("")
        result = read_json_file(path)
        assert result == {}

    def test_handles_nested_dict(self, tmp_path):
        path = tmp_path / "nested.json"
        path.write_text(json.dumps({"outer": {"inner": [1, 2]}}))
        result = read_json_file(path)
        assert result == {"outer": {"inner": [1, 2]}}


class TestToFloatNan:
    def test_none_returns_nan(self):
        result = to_float_nan(None)
        assert result != result

    def test_empty_string_returns_nan(self):
        result = to_float_nan("")
        assert result != result

    def test_valid_number(self):
        result = to_float_nan("3.14")
        assert result == 3.14

    def test_invalid_string_returns_nan(self):
        result = to_float_nan("abc")
        assert result != result


class TestToFloat:
    def test_valid_float(self):
        assert to_float("3.14") == 3.14

    def test_invalid_returns_default(self):
        assert to_float("abc", 99.0) == 99.0

    def test_none_returns_default(self):
        assert to_float(None, 0.0) == 0.0


class TestToBool:
    def test_true_values(self):
        assert to_bool("true") is True
        assert to_bool("1") is True
        assert to_bool("yes") is True
        assert to_bool("TRUE") is True

    def test_false_values(self):
        assert to_bool("false") is False
        assert to_bool("0") is False
        assert to_bool("no") is False
        assert to_bool("") is False


class TestReadCsvRows:
    def test_reads_valid_csv(self, tmp_path):
        path = tmp_path / "test.csv"
        path.write_text("col1,col2\na,1\nb,2\n")
        result = read_csv_rows(path)
        assert len(result) == 2
        assert result[0] == {"col1": "a", "col2": "1"}

    def test_returns_empty_for_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.csv"
        result = read_csv_rows(path)
        assert result == []