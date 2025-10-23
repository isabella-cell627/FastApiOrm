import pytest
from fastapi_orm.performance import N1Detector, QueryInfo, N1Warning


def test_query_info_creation():
    """Test QueryInfo dataclass creation"""
    query = QueryInfo(
        sql="SELECT * FROM users",
        timestamp=123.45,
        duration=0.01
    )
    
    assert query.sql == "SELECT * FROM users"
    assert query.timestamp == 123.45
    assert query.duration == 0.01


def test_n1_warning_creation():
    """Test N1Warning dataclass creation"""
    warning = N1Warning(
        pattern="SELECT * FROM posts WHERE user_id = ?",
        count=10,
        total_time=0.5
    )
    
    assert warning.pattern == "SELECT * FROM posts WHERE user_id = ?"
    assert warning.count == 10
    assert warning.total_time == 0.5
    assert warning.severity == "medium"


def test_n1_detector_initialization():
    """Test N1Detector initialization"""
    detector = N1Detector(threshold=5, time_window=2.0)
    
    assert detector.threshold == 5
    assert detector.time_window == 2.0
    assert detector.enabled is True


def test_n1_detector_start_stop():
    """Test detector start and stop"""
    detector = N1Detector()
    
    detector.start()
    assert detector._is_running is True
    
    detector.stop()
    assert detector._is_running is False


def test_n1_detector_record_query():
    """Test recording queries"""
    detector = N1Detector()
    detector.start()
    
    detector.record_query("SELECT * FROM users", duration=0.01)
    detector.record_query("SELECT * FROM posts WHERE user_id = 1", duration=0.02)
    detector.record_query("SELECT * FROM posts WHERE user_id = 2", duration=0.02)
    
    assert len(detector._query_history) == 3


def test_n1_detector_detect_similar_queries():
    """Test detecting similar queries"""
    detector = N1Detector(threshold=3)
    detector.start()
    
    detector.record_query("SELECT * FROM posts WHERE user_id = 1", duration=0.01)
    detector.record_query("SELECT * FROM posts WHERE user_id = 2", duration=0.01)
    detector.record_query("SELECT * FROM posts WHERE user_id = 3", duration=0.01)
    detector.record_query("SELECT * FROM posts WHERE user_id = 4", duration=0.01)
    
    detector.analyze()
    warnings = detector.get_warnings()
    
    assert len(warnings) > 0


def test_n1_detector_no_warnings():
    """Test no warnings for diverse queries"""
    detector = N1Detector(threshold=5)
    detector.start()
    
    detector.record_query("SELECT * FROM users", duration=0.01)
    detector.record_query("SELECT * FROM posts", duration=0.01)
    detector.record_query("SELECT * FROM comments", duration=0.01)
    
    detector.analyze()
    warnings = detector.get_warnings()
    
    assert len(warnings) == 0


def test_n1_detector_get_warnings():
    """Test getting warnings"""
    detector = N1Detector()
    warnings = detector.get_warnings()
    
    assert isinstance(warnings, list)


def test_n1_detector_clear():
    """Test clearing detector history"""
    detector = N1Detector()
    detector.start()
    
    detector.record_query("SELECT * FROM users", duration=0.01)
    detector.record_query("SELECT * FROM posts", duration=0.01)
    
    detector.clear()
    
    assert len(detector._query_history) == 0
    assert len(detector._warnings) == 0


def test_n1_detector_disabled():
    """Test detector when disabled"""
    detector = N1Detector(enabled=False)
    
    detector.record_query("SELECT * FROM users", duration=0.01)
    
    assert len(detector._query_history) == 0


def test_n1_detector_severity_levels():
    """Test warning severity levels"""
    warning_medium = N1Warning(pattern="test", count=5, total_time=0.5, severity="medium")
    warning_high = N1Warning(pattern="test", count=20, total_time=2.0, severity="high")
    warning_critical = N1Warning(pattern="test", count=100, total_time=10.0, severity="critical")
    
    assert warning_medium.severity == "medium"
    assert warning_high.severity == "high"
    assert warning_critical.severity == "critical"


def test_n1_detector_get_stats():
    """Test getting detector statistics"""
    detector = N1Detector()
    detector.start()
    
    detector.record_query("SELECT * FROM users", duration=0.01)
    detector.record_query("SELECT * FROM posts", duration=0.02)
    
    stats = detector.get_stats()
    
    assert "total_queries" in stats
    assert "total_time" in stats
    assert stats["total_queries"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
