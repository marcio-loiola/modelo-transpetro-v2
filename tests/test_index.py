from src.pipeline.bio_index import bio_index_0_10, bio_class_from_excess_ratio

def test_index_bounds():
    assert 0 <= bio_index_0_10(0.0) <= 10
    assert 0 <= bio_index_0_10(0.5) <= 10

def test_class():
    assert bio_class_from_excess_ratio(0.05) == 'Leve'
    assert bio_class_from_excess_ratio(0.15) == 'Moderada'
    assert bio_class_from_excess_ratio(0.25) == 'Severa'