from build123d import *

part = Box(40, 20, 10)
export_gltf(part, "export/test.glb", binary=True)