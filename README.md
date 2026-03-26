# Space Hack

A space situational awareness and collision avoidance system featuring a FastAPI backend for orbital mechanics calculations and a Next.js dashboard for visualizing satellite telemetry and potential conjunctions.

## Project Structure

- `backend/`: FastAPI application handling orbital physics, collision detection, and maneuver planning.
- `frontend/`: Next.js web application for visualizing the fleet, ground tracks, and conjunction radar.
- `simulate_data.py`: A Python script to generate simulated telemetry data (satellites and space debris) testing.
- `docker-compose.yml`: Configuration to easily orchestrate and run both the frontend and backend services via Docker.

## Getting Started

### Using Docker (Recommended)

To run the entire stack (backend and frontend) using Docker Compose:

```bash
docker-compose up --build
```
- The frontend will be available at `http://localhost:3000`
- The backend API will be available at `http://localhost:8000`

### Local Development

#### Backend
1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   uvicorn main:app --reload
   ```

#### Frontend
1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

#### Simulated Data
You can generate test data to populate the platform using the simulator script:
```bash
pip install -r requirements.txt
python simulate_data.py
```
