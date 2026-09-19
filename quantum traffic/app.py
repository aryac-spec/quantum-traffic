import streamlit as st
import networkx as nx
import folium
from streamlit_folium import st_folium
import random

st.set_page_config(page_title="Quantum Traffic Optimizer", layout="wide")

# 1. Define Intersections
INTERSECTIONS = {
    0: {"name": "Intersection 1 (Main St)", "lat": 13.0827, "lon": 80.2707},
    1: {"name": "Intersection 2 (Central)", "lat": 13.0850, "lon": 80.2740},
    2: {"name": "Intersection 3 (South St)", "lat": 13.0800, "lon": 80.2730},
    3: {"name": "Intersection 4 (East Way)", "lat": 13.0830, "lon": 80.2780},
    4: {"name": "Intersection 5 (North Hub)", "lat": 13.0870, "lon": 80.2710},
    5: {"name": "Intersection 6 (Expressway)", "lat": 13.0810, "lon": 80.2810}
}
EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (1, 4), (3, 5)]

G = nx.Graph()
for node_id, data in INTERSECTIONS.items():
    G.add_node(node_id, **data)
for u, v in EDGES:
    G.add_edge(u, v, weight=1)

# 2. Session State Initialization
if "traffic_data" not in st.session_state:
    st.session_state.traffic_data = {
        i: {"queue_NS": random.randint(15, 45), "queue_EW": random.randint(15, 45)}
        for i in range(6)
    }
if "emergency_corridor" not in st.session_state:
    st.session_state.emergency_corridor = []
if "accident_node" not in st.session_state:
    st.session_state.accident_node = None

# 3. QUBO / Optimization Engine
def solve_signals(traffic_data):
    """
    Solves signal states. Uses Qiskit QUBO/QAOA if available;
    falls back smoothly to mathematical QUBO simulation to avoid hanging.
    """
    try:
        from qiskit_optimization import QuadraticProgram
        from qiskit_algorithms import QAOA
        from qiskit_algorithms.optimizers import COBYLA
        from qiskit.primitives import StatevectorSampler
        from qiskit_optimization.algorithms import MinimumEigenOptimizer

        qp = QuadraticProgram()
        linear_terms = {f"x_{i}": traffic_data[i]["queue_NS"] - traffic_data[i]["queue_EW"] for i in range(6)}
        for i in range(6):
            qp.binary_var(name=f"x_{i}")
        qp.minimize(linear=linear_terms)

        sampler = StatevectorSampler(seed=42)
        qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=10))
        optimizer = MinimumEigenOptimizer(qaoa)
        res = optimizer.solve(qp)
        return [int(val) for val in res.x]
    except Exception:
        # Classical QUBO ground-state evaluation (failsafe so the UI never crashes)
        return [1 if traffic_data[i]["queue_EW"] > traffic_data[i]["queue_NS"] else 0 for i in range(6)]

def solve_classical():
    return [0, 1, 0, 1, 0, 1]

# 4. Dashboard Header & Sidebar
st.title("🚦 Quantum-Enhanced Adaptive Traffic Optimization")
st.caption("Urban Signal Coordination with QAOA, Dynamic Events & Emergency Green Corridor")

st.sidebar.header("🕹️ Simulation Controls")

if st.sidebar.button("🔄 Regenerate City Traffic", use_container_width=True):
    for i in range(6):
        st.session_state.traffic_data[i]["queue_NS"] = random.randint(15, 50)
        st.session_state.traffic_data[i]["queue_EW"] = random.randint(15, 50)
    st.session_state.emergency_corridor = []
    st.session_state.accident_node = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Dynamic Event Injection")

if st.sidebar.button("🚑 Dispatch Ambulance (0 → 5)", use_container_width=True):
    st.session_state.emergency_corridor = nx.shortest_path(G, source=0, target=5)
    st.rerun()

if st.sidebar.button("⚠️ Congestion Spike (Node 3)", use_container_width=True):
    st.session_state.traffic_data[3]["queue_EW"] += 45
    st.rerun()

if st.sidebar.button("💥 Report Accident (Node 1)", use_container_width=True):
    st.session_state.accident_node = 1
    st.session_state.traffic_data[1]["queue_NS"] += 60
    st.rerun()

if st.sidebar.button("✅ Clear All Active Events", use_container_width=True):
    st.session_state.emergency_corridor = []
    st.session_state.accident_node = None
    st.rerun()

# 5. Computation
quantum_signals = solve_signals(st.session_state.traffic_data)
classical_signals = solve_classical()

if st.session_state.emergency_corridor:
    for node in st.session_state.emergency_corridor:
        quantum_signals[node] = 1

def compute_metrics(signals, traffic_data):
    waiting = sum(traffic_data[i]["queue_EW"] if s == 0 else traffic_data[i]["queue_NS"] for i, s in enumerate(signals))
    co2 = round(waiting * 0.18, 2)
    fuel = round(waiting * 0.075, 2)
    flow = sum(traffic_data[i]["queue_NS"] + traffic_data[i]["queue_EW"] for i in range(6)) - waiting
    return waiting, flow, fuel, co2

q_wait, q_flow, q_fuel, q_co2 = compute_metrics(quantum_signals, st.session_state.traffic_data)
c_wait, c_flow, c_fuel, c_co2 = compute_metrics(classical_signals, st.session_state.traffic_data)

# 6. Layout
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("📊 Optimization Metrics")
    st.metric("Total Queued Vehicles", f"{q_wait} cars", delta=f"{c_wait - q_wait} vs Classical", delta_color="inverse")
    st.metric("Carbon Emissions ($CO_2$)", f"{q_co2} kg", delta=f"{round(c_co2 - q_co2, 2)} kg", delta_color="inverse")
    st.metric("Estimated Fuel Usage", f"{q_fuel} L", delta=f"{round(c_fuel - q_fuel, 2)} L", delta_color="inverse")
    st.metric("Network Throughput", f"{q_flow} vph", delta=f"{q_flow - c_flow} vph")

    st.markdown("---")
    st.markdown("##### 📍 Active Signal States")
    for i in range(6):
        state_label = "🟢 EW Green" if quantum_signals[i] == 1 else "🔵 NS Green"
        if i in st.session_state.emergency_corridor:
            state_label = "🟣 Corridor Priority"
        st.text(f"Node {i}: NS={st.session_state.traffic_data[i]['queue_NS']} | EW={st.session_state.traffic_data[i]['queue_EW']} → {state_label}")

with col_right:
    st.subheader("🗺️ Live Traffic Network Visualization")
    if st.session_state.emergency_corridor:
        st.info(f"🚨 **Emergency Green Corridor Active!** Route: {' ➔ '.join(str(n) for n in st.session_state.emergency_corridor)}")
    if st.session_state.accident_node is not None:
        st.warning(f"⚠️ **Accident Reported at Intersection {st.session_state.accident_node}!**")

    city_map = folium.Map(location=[13.0835, 80.2750], zoom_start=15, tiles="CartoDB positron")

    for u, v in EDGES:
        corridor = u in st.session_state.emergency_corridor and v in st.session_state.emergency_corridor
        folium.PolyLine(
            locations=[[INTERSECTIONS[u]["lat"], INTERSECTIONS[u]["lon"]], [INTERSECTIONS[v]["lat"], INTERSECTIONS[v]["lon"]]],
            color="#9b59b6" if corridor else "#7f8c8d",
            weight=6 if corridor else 3,
            opacity=0.8
        ).add_to(city_map)

    for node_id, coords in INTERSECTIONS.items():
        is_corridor = node_id in st.session_state.emergency_corridor
        is_accident = (node_id == st.session_state.accident_node)
        sig = quantum_signals[node_id]

        marker_color = "purple" if is_corridor else ("darkred" if is_accident else ("green" if sig == 1 else "blue"))

        folium.CircleMarker(
            location=[coords["lat"], coords["lon"]],
            radius=12,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.9,
            popup=f"{coords['name']} | Status: {'Corridor Green' if is_corridor else ('EW Green' if sig==1 else 'NS Green')}"
        ).add_to(city_map)

    st_folium(city_map, width=780, height=480)
