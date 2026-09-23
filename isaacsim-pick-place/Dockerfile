# docker build -t rlmesh-examples/isaacsim-pick-place isaacsim-pick-place
FROM nvcr.io/nvidia/isaac-sim:6.1.0

ARG RLMESH_VERSION=0.1.0
RUN /isaac-sim/python.sh -m pip install --no-cache-dir "rlmesh[numpy]==${RLMESH_VERSION}" gymnasium

ENV ACCEPT_EULA=Y PRIVACY_CONSENT=Y PYTHONUNBUFFERED=1 PYTHONPATH=/app \
    RLMESH_ADDRESS=0.0.0.0:50051
COPY ur10e_pick_place.py /app/

LABEL dev.rlmesh.package='{"schemaVersion":1,"name":"ur10e-pick-place","description":"UR10e and Robotiq pick and place with RLMesh adapters on Isaac Sim 6.1.","tags":["gpu"],"resources":{"memory":"16Gi"}}'

EXPOSE 50051
# Keep Isaac's Python as PID 1 so Ctrl-C and docker stop reach the server.
ENTRYPOINT ["bash", "-c", "source /isaac-sim/setup_python_env.sh && CARB_APP_PATH=/isaac-sim/kit ISAAC_PATH=/isaac-sim EXP_PATH=/isaac-sim/apps LD_PRELOAD=/isaac-sim/kit/libcarb.so exec /isaac-sim/kit/python/bin/python3 \"$@\"", "--"]
CMD ["-m", "rlmesh.serve", "--env", "ur10e_pick_place:UR10ePickPlace"]
