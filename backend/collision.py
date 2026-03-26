import numpy as np
from scipy.spatial import cKDTree

class CollisionDetector:
    def __init__(self, threshold_km=0.1):
        self.threshold_km = threshold_km

    def detect_collisions(self, engine):
        """
        Use scipy.spatial.cKDTree to find all O(N log N) pairs of objects
        within the threshold_km distance.
        """
        if engine.count < 2:
            return []

        active_positions = engine.positions[:engine.count]
        
        # Build KD-Tree
        tree = cKDTree(active_positions)
        
        # Query all pairs within threshold
        # Returns a set of tuples containing indices (i, j) where distance < threshold
        pairs = tree.query_pairs(r=self.threshold_km)
        
        collisions = []
        for i, j in pairs:
            # We only care about Satellite-Debris or Satellite-Satellite collisions
            if engine.types[i] == 1 or engine.types[j] == 1:
                # Dist is less than threshold, but let's compute exact
                dist = np.linalg.norm(active_positions[i] - active_positions[j])
                
                # Assign roles based on who is the satellite (prefer i)
                sat_idx, deb_idx = (i, j) if engine.types[i] == 1 else (j, i)
                
                collisions.append({
                    "satellite": engine.ids[sat_idx],
                    "debris": engine.ids[deb_idx],
                    "distance": float(dist)
                })
                
        return collisions
