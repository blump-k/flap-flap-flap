import bpy

bpy.ops.import_scene.gltf(filepath="export/test.glb")
bpy.ops.wm.usd_export(filepath="export/test.usdz")
