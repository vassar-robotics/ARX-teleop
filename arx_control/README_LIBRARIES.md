# ARX Control Libraries

## Important: Binary Files Not Included (Best Practice)

The ARX control libraries (`.so` files) are platform-specific and should not be included in the git repository. 

**Note**: Currently the binaries ARE checked into git (in `arx_control/lib/`) for convenience, but this is not recommended practice. These are Linux x86_64 binaries and will NOT work on macOS or other platforms.

## Setup Instructions

### Linux (Ubuntu/Debian)

1. **From R5 SDK** (if you have it):
   ```bash
   cd arx_control
   ./setup_libraries.sh
   ```

2. **Manual copy**:
   ```bash
   # Copy from R5 SDK
   cp -r /path/to/R5/py/ARX_R5_python/bimanual/lib/* arx_control/lib/
   ```

### macOS

The ARX libraries need to be compiled for macOS. Options:

1. **Build from source** (if available):
   - Contact ARX for macOS build instructions
   - The libraries will have `.dylib` extension instead of `.so`

2. **Use Docker**:
   ```bash
   # Run Linux environment in Docker
   docker run -it --rm -v $(pwd):/workspace ubuntu:22.04
   # Inside container, install and run as Linux
   ```

3. **Remote development**:
   - Use VS Code Remote SSH to develop on a Linux machine
   - Use GitHub Codespaces or similar cloud development

### Windows

Windows support requires `.dll` files. Contact ARX for Windows binaries.

## Library Structure

Expected structure after setup:
```
arx_control/lib/
├── arx_r5_python/
│   ├── arx_r5_python.cpython-*.so (or .dylib on macOS)
│   └── kinematic_solver.cpython-*.so
├── arx_r5_src/
│   ├── libarx_r5_src.so
│   └── include/  (headers for compilation)
└── libkinematic_solver.so
```

## Alternative Solutions

### 1. Submodule for Binaries
Create a separate repo for platform-specific binaries:
```bash
git submodule add https://github.com/yourorg/arx-binaries.git arx_control/lib
```

### 2. Download During Setup
Modify `setup_libraries.sh` to download from a release server:
```bash
wget https://github.com/yourorg/arx-teleop/releases/download/v1.0/arx-libs-${PLATFORM}.tar.gz
```

### 3. Build from Source
If ARX provides source code, add a proper build system:
- CMake for C++ libraries
- setuptools for Python extensions

## Checking Library Compatibility

```bash
# Check if libraries are present
ls -la arx_control/lib/

# Check library architecture (Linux/macOS)
file arx_control/lib/arx_r5_src/libarx_r5_src.so

# Check Python compatibility
python3 -c "import arx_r5_python" 
```

## Troubleshooting

- **Import Error on macOS**: You're trying to use Linux `.so` files. You need macOS `.dylib` files.
- **Architecture mismatch**: Make sure libraries match your system (x86_64 vs arm64)
- **Python version mismatch**: Libraries are compiled for specific Python versions (e.g., cpython-313)