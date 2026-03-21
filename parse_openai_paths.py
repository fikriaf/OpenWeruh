from svgpathtools import svg2paths
paths, attributes = svg2paths('assets/openai_whitebg.svg')
for i, path in enumerate(paths):
    print(f"Path {i} BBox: {path.bbox()}")
