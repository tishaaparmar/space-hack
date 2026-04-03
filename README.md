# Orbital Insight ACM (Autonomous Constellation Manager) 🚀

Submitted for the **National Space Hackathon 2026**

A high-performance, autonomous space situational awareness and collision avoidance system. Built to handle $O(N \log N)$ spatial indexing for real-time tracking of thousands of space objects, predicting conjunctions, and executing fuel-efficient evasion and recovery maneuvers while respecting real-world physical constraints.

## 🌟 Key Features

### 1. Autonomous Predictive Collision Avoidance (COLA)
- **TCA (Time of Closest Approach) Algorithm**: Calculates the exact future intersection points using relative position and velocity vectors.
- **Minimum $\Delta v$ Optimization**: Computes the exact minimum thrust required to guarantee a 5 km safety envelope at TCA.
- **Directional priority**: Maneuvers are prioritized along the satellite's velocity vector for maximum fuel efficiency.

### 2. Physical Constants & Constraints Enforced
- **Real-world physics**: RK4 Integration incorporating J2 perturbation for accurate orbital propagation.
- **Thruster Cooldown & Signal Latency**: Enforces a 600s cooldown between burns and models a 10s latency.
- **Line-of-Sight (LOS) Checks**: Burn commands require visibility to one of the 6 designated global ground stations (e.g., ISTRAC, Svalbard, Goldstone).
- **Tsiolkovsky Fuel Depletion**: Accurately modeled fuel mass reduction per burn.

### 3. Automated Fleet Recovery
- **Station-Keeping**: Constantly monitors drift from nominal orbital slots.
- **Recovery Burns**: Satellites autonomously schedule phasing burns to return to their slots after executing an evasion maneuver, ensuring maximum constellation uptime (>98%).

### 4. High-Performance Architecture
- **$O(N \log N)$ Spatial Indexing**: Utilizes SciPy's `cKDTree` for rapid spatial querying of debris clouds, safely supporting 10,000+ simulated objects.
- **Unified Container Deployment**: FastAPI backend and Next.js frontend compiled and orchestrated concurrently through a single highly optimized Docker container.

### 5. Tactical UI Dashboard
- **Real-time Telemetry Visualization**: Full global ground track map marking active satellites, debris clouds, and ground stations.
- **Conjunction Radar**: A tactical bullseye view highlighting incoming threats inside critical thresholds (1 km, 5 km).
- **Fleet Health & Event Logs**: Tracks fuel (EOL warnings), uptime percentage, and real-time maneuver execution timelines.

---

## 🛠️ Project Structure

- `backend/`: FastAPI application handling the physics engine, collision detection, and maneuver planning algorithms.
- `frontend/`: Next.js web application for visualizing the fleet health, map rendering (`react-simple-maps`), and timeline.
- `simulate_data3.py`: The final simulation stress-test script injecting multi-threat scenarios against 50 satellites and massive debris fields.
- `Dockerfile` & `start.sh`: Universal packaging script handling Python dependencies, Node compilation, and concurrent service execution.

---

## 🚀 Getting Started

The entire application runs from a single unified Docker container covering both the Next.js frontend and the FastAPI backend.

### Prerequisites
- Docker / Docker Desktop

### 1. Build and Run via Docker

Navigate to the root directory `c:\Projects\Hackathons\space-hack\space-hack` and build the container:

```bash
docker build -t orbital-insight-acm .
```

Run the container:

```bash
docker run -p 3000:3000 -p 8000:8000 orbital-insight-acm
```

### 2. Access the Application
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Run the Stress Test Simulation
In a **separate** terminal window (while the Docker container is running), execute the data simulation script to inject the satellites and threats into the running system.

```bash
pip install requests
python simulate_data3.py
```

Watch the Next.js dashboard as the simulation runs through its steps. You will see collision warnings, autonomous evasion maneuvers ($\Delta v$ lines plotted), and subsequent recovery burns in real-time.
