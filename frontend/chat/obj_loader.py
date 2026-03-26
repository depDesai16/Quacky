import os


class ObjLoader:
    def __init__(self, filename):
        """Initialize the instance state."""
        self.vertices = []
        self.normals = []
        self.faces = []
        self.materials = {}
        self.current_material = None
        self.load(filename)

    def load_mtl(self, mtl_path):
        """Load mtl."""
        current = None
        with open(mtl_path, "r") as f:
            for line in f:
                if line.startswith("newmtl"):
                    current = line.split()[1]
                    self.materials[current] = {"Kd": (1.0, 1.0, 1.0)}
                elif line.startswith("Kd") and current:
                    values = tuple(map(float, line.split()[1:4]))
                    self.materials[current]["Kd"] = values

    def load(self, filename):
        """Load state values."""
        base_dir = os.path.dirname(filename)
        with open(filename, "r") as f:
            for line in f:
                if line.startswith("mtllib"):
                    mtl_file = line.split()[1]
                    self.load_mtl(os.path.join(base_dir, mtl_file))
                elif line.startswith("v "):
                    parts = line.strip().split()
                    self.vertices.append(tuple(map(float, parts[1:4])))
                elif line.startswith("vn"):
                    parts = line.strip().split()
                    self.normals.append(tuple(map(float, parts[1:4])))
                elif line.startswith("usemtl"):
                    self.current_material = line.split()[1]
                elif line.startswith("f"):
                    parts = line.strip().split()[1:]
                    face = []
                    for part in parts:
                        vals = part.split('/')
                        v_idx = int(vals[0]) - 1
                        n_idx = int(vals[2]) - 1 if len(vals) > 2 and vals[2] else None
                        face.append((v_idx, n_idx))
                    self.faces.append((face, self.current_material))