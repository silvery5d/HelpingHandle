from app.services.geo_service import bounding_box, haversine_distance


def test_haversine_tokyo_tower_to_shibuya():
    # Tokyo Tower: 35.6586, 139.7454
    # Shibuya Station: 35.6580, 139.7016
    dist = haversine_distance(35.6586, 139.7454, 35.6580, 139.7016)
    assert 3.5 < dist < 4.5  # ~3.9 km


def test_haversine_same_point():
    dist = haversine_distance(35.0, 139.0, 35.0, 139.0)
    assert dist == 0.0


def test_bounding_box():
    min_lat, max_lat, min_lon, max_lon = bounding_box(35.6586, 139.7454, 10.0)
    assert min_lat < 35.6586 < max_lat
    assert min_lon < 139.7454 < max_lon
    # Roughly 0.09 degrees per 10km
    assert abs(max_lat - min_lat) > 0.1
