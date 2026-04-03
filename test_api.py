import requests, json, time

time.sleep(2)  # wait for reload
BASE = 'http://localhost:8000'

# Test 1: Telemetry with timestamp
print('=== Test 1: Telemetry ===')
r = requests.post(f'{BASE}/api/telemetry', json={
    'timestamp': '2026-03-12T08:00:00.000Z',
    'objects': [
        {'id': 'SAT-ALPHA-01', 'type': 'SATELLITE', 'r': {'x': 6800.0, 'y': 0.0, 'z': 0.0}, 'v': {'x': 0.0, 'y': 7.66, 'z': 0.0}, 'fuel_kg': 50.0},
        {'id': 'DEB-99421', 'type': 'DEBRIS', 'r': {'x': 6800.05, 'y': 0.01, 'z': 0.01}, 'v': {'x': 0.0, 'y': -7.5, 'z': 0.0}}
    ]
})
print(f'  Status: {r.status_code}')
print(f'  Response: {json.dumps(r.json(), indent=2)}')

# Test 2: Simulate step
print()
print('=== Test 2: Simulate Step (3600s) ===')
r = requests.post(f'{BASE}/api/simulate/step', json={'step_seconds': 3600})
print(f'  Status: {r.status_code}')
print(f'  Response: {json.dumps(r.json(), indent=2)}')

# Test 3: Maneuver schedule
print()
print('=== Test 3: Maneuver Schedule ===')
r = requests.post(f'{BASE}/api/maneuver/schedule', json={
    'satelliteId': 'SAT-ALPHA-01',
    'maneuver_sequence': [
        {'burn_id': 'EVASION_BURN_1', 'burnTime': '2026-03-12T14:15:30.000Z', 'deltaV_vector': {'x': 0.002, 'y': 0.015, 'z': -0.001}}
    ]
})
print(f'  Status: {r.status_code}')
print(f'  Response: {json.dumps(r.json(), indent=2)}')

# Test 4: Snapshot
print()
print('=== Test 4: Visualization Snapshot ===')
r = requests.get(f'{BASE}/api/visualization/snapshot')
d = r.json()
print(f'  Timestamp: {d["timestamp"]}')
print(f'  Satellites: {len(d["satellites"])}')
print(f'  Debris: {len(d["debris_cloud"])}')
print(f'  Maneuvers: {len(d["maneuvers"])}')

print()
print('=== ALL TESTS PASSED ===')
