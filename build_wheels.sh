#!/bin/bash
set -e -x

# Clear out old builds
rm -rf /io/dist /io/wheelhouse /io/build

# Dynamically find and loop through modern Python versions (3.10 and newer).
# We explicitly skip the experimental free-threaded variants (cp313t, cp314t)
# because their ecosystem (e.g. Pillow) does not yet provide pre-built wheels.
for PYDIR in /opt/python/cp31*; do
    if [ ! -d "$PYDIR" ]; then
        continue
    fi

    BASENAME=$(basename "$PYDIR")
    # Skip free-threaded builds
    if [[ "$BASENAME" == *t ]]; then
        echo "Skipping experimental free-threaded interpreter: ${BASENAME}"
        continue
    fi

    PYBIN="${PYDIR}/bin"
    echo "========================================================"
    echo "Building wheel using: ${PYBIN}/python"
    echo "========================================================"

    # Upgrade packaging tools inside this specific Python environment.
    "${PYBIN}/pip" install --upgrade pip build setuptools wheel pytest -q

    # Build the raw wheel
    "${PYBIN}/pip" wheel /io/ --no-deps -w /io/dist/

    # Locate the wheel that was just built by this interpreter
    WHL=$(ls /io/dist/fast_sudoku-*-${BASENAME}-*.whl 2>/dev/null | head -1)
    if [ -z "$WHL" ]; then
        echo "ERROR: no wheel matching *-${BASENAME}-* found in /io/dist"
        ls -la /io/dist/
        exit 1
    fi

    echo "Testing ${WHL} with ${PYBIN}/python"

    # Runtime dependencies (installed separately for clearer errors)
    "${PYBIN}/pip" install numpy pillow -q

    # The wheel itself (--no-deps because we just installed them)
    "${PYBIN}/pip" install "$WHL" --no-deps --force-reinstall -q

    # Run the tests
    "${PYBIN}/python" -m pytest /io/tests -q
done

# Repair the wheels using auditwheel (unchanged)
echo "Repairing wheels to make them manylinux compliant..."
for whl in /io/dist/*.whl; do
    auditwheel repair "$whl" \
        --plat manylinux_2_28_x86_64 \
        -w /io/wheelhouse/
done

echo "Successfully built and repaired wheels in 'wheelhouse/'!"
