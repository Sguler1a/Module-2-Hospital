import sys
import platform
import timeit

print("Python version:", sys.version)
print("Platform machine:", platform.machine())
print("Platform architecture:", platform.architecture())

try:
    import numpy as np
    print("Numpy version:", np.__version__)
    print("Numpy config info:")
    np.show_config()
except ImportError:
    print("Numpy not installed")
