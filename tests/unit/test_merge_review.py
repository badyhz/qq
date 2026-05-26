import pytest

from core.merge_review import MergeRequest, MergeReviewPipeline, ReviewStatus


# ---------- helpers ----------

def _setup() -> MergeReviewPipeline:
    pipe = MergeReviewPipeline()
    pipe.set_canonical("core/worker_pool.py", "abc123")
    return pipe


# ---------- tests ----------

def test_propose_creates_mr():
    pipe = _setup()
    # same hash as canonical -> PROPOSED (no conflict)
    mr = pipe.propose("core/worker_pool.py", "T710", "abc123")
    assert mr.status == ReviewStatus.PROPOSED
    assert mr.id == "MR-0001"
    assert mr.proposing_task == "T710"


def test_propose_auto_detects_conflict():
    pipe = _setup()
    # candidate differs from canonical -> CONFLICT
    mr = pipe.propose("core/worker_pool.py", "T710", "def456")
    assert mr.status == ReviewStatus.CONFLICT


def test_propose_no_conflict_when_hashes_match():
    pipe = _setup()
    mr = pipe.propose("core/worker_pool.py", "T710", "abc123")
    assert mr.status == ReviewStatus.PROPOSED


def test_accept_updates_canonical():
    pipe = _setup()
    mr = pipe.propose("core/worker_pool.py", "T710", "def456")
    pipe.accept(mr.id, "reviewer-1")
    assert pipe._canonical_hashes["core/worker_pool.py"] == "def456"
    assert mr.status == ReviewStatus.ACCEPTED


def test_reject_preserves_canonical():
    pipe = _setup()
    mr = pipe.propose("core/worker_pool.py", "T710", "def456")
    pipe.reject(mr.id, "reviewer-1", reason="low quality")
    assert pipe._canonical_hashes["core/worker_pool.py"] == "abc123"
    assert mr.status == ReviewStatus.REJECTED
    assert mr.review_notes == "low quality"


def test_detect_conflicts_for_same_component():
    pipe = _setup()
    mr1 = pipe.propose("core/worker_pool.py", "T710", "def456")
    mr2 = pipe.propose("core/worker_pool.py", "T720", "789aaa")
    conflicts = pipe.detect_conflicts("core/worker_pool.py")
    assert len(conflicts) == 2
    assert mr1 in conflicts and mr2 in conflicts


def test_list_open_excludes_terminal():
    pipe = _setup()
    mr1 = pipe.propose("core/worker_pool.py", "T710", "def456")
    mr2 = pipe.propose("core/worker_pool.py", "T720", "789aaa")
    pipe.accept(mr1.id, "reviewer-1")
    pipe.reject(mr2.id, "reviewer-1")
    open_mrs = pipe.list_open()
    assert len(open_mrs) == 0


def test_review_transitions_status():
    pipe = _setup()
    mr = pipe.propose("core/worker_pool.py", "T710", "def456")
    pipe.review(mr.id, "reviewer-1", notes="looking into it")
    assert mr.status == ReviewStatus.REVIEWING
    assert mr.review_notes == "looking into it"


def test_multiple_mrs_on_same_component():
    pipe = _setup()
    mr1 = pipe.propose("core/worker_pool.py", "T710", "aaa111")
    mr2 = pipe.propose("core/worker_pool.py", "T720", "bbb222")
    mr3 = pipe.propose("core/worker_pool.py", "T730", "ccc333")
    assert mr1.id == "MR-0001"
    assert mr3.id == "MR-0003"
    assert len(pipe.list_open()) == 3


def test_summary_stats():
    pipe = _setup()
    pipe.propose("core/worker_pool.py", "T710", "def456")
    pipe.propose("core/signal_engine.py", "T720", "aaa")
    s = pipe.summary()
    assert s["total_mrs"] == 2
    assert s["open_mrs"] == 2
    assert s["tracked_components"] == 1  # only worker_pool was set


def test_get_returns_none_for_unknown():
    pipe = MergeReviewPipeline()
    assert pipe.get("MR-9999") is None


def test_accept_then_new_propose_uses_updated_canonical():
    pipe = _setup()
    mr1 = pipe.propose("core/worker_pool.py", "T710", "def456")
    pipe.accept(mr1.id, "r")
    # now canonical is def456; propose with same hash -> PROPOSED, not CONFLICT
    mr2 = pipe.propose("core/worker_pool.py", "T720", "def456")
    assert mr2.status == ReviewStatus.PROPOSED
    assert mr2.canonical_hash == "def456"


def test_reject_unknown_mr_raises():
    pipe = MergeReviewPipeline()
    with pytest.raises(KeyError, match="Unknown MR"):
        pipe.reject("MR-0042", "r")
