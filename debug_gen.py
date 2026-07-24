import sys
sys.path.insert(0, '.')

from src.kty import KTY

box = KTY(
    size=(600, 400, 400),
    quality="high",
    state="closed",
)
obj = box.generate()

# Проверяем размеры напрямую
print(f"OBJ LOCATION: {obj.location}")
print(f"OBJ SCALE: {obj.scale}")
print(f"OBJ DIMENSIONS: {obj.dimensions}")

# Также проверим mesh vertices bounds
mesh = obj.data
min_x = min(v.co.x for v in mesh.vertices)
max_x = max(v.co.x for v in mesh.vertices)
min_y = min(v.co.y for v in mesh.vertices)
max_y = max(v.co.y for v in mesh.vertices)
min_z = min(v.co.z for v in mesh.vertices)
max_z = max(v.co.z for v in mesh.vertices)
print(f"VERTEX BOUNDS X: {min_x} to {max_x} (size: {max_x - min_x})")
print(f"VERTEX BOUNDS Y: {min_y} to {max_y} (size: {max_y - min_y})")
print(f"VERTEX BOUNDS Z: {min_z} to {max_z} (size: {max_z - min_z})")
