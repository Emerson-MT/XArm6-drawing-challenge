import math

def discretize_path(points, step=10):
    """
    Input:
        points = [(x,y), (x,y), ...]

    Output:
        lista discretizada a cada `step` píxeles.
    """
    if len(points) < 2:
        return []

    new_points = [points[0]]
    acc = 0

    for i in range(1, len(points)):
        x1, y1 = points[i-1]
        x2, y2 = points[i]

        dist = math.hypot(x2-x1, y2-y1)

        if dist + acc < step:
            acc += dist
            continue

        ratio = (step - acc) / dist
        nx = x1 + ratio*(x2-x1)
        ny = y1 + ratio*(y2-y1)

        new_points.append((nx, ny))
        acc = 0

    return new_points
