import numpy as np
import numpy.testing as npt
import pyopcode
import pytest


@pytest.fixture(autouse=True)
def fix_randomness():
    np.random.seed(41)


def triangle_soup(N, range=(0, 0)):
    # create a trianglesoup
    vertices = np.random.uniform(-0.5, 0.5, size=(N * 3, 3)).astype(np.float32)
    view = vertices.reshape(N, 3, 3)
    view += np.random.uniform(*range, size=(N, 1, 3))
    triangles = np.arange(N * 3).reshape(N, 3).astype(np.int32)
    return vertices, triangles


def test_invalid():
    vertices = np.random.rand(10, 3)
    triangles = np.arange(10 * 3).reshape(10, 3).astype(np.int32)

    with pytest.raises(Exception):
        pyopcode.Model(vertices, triangles)

    vertices = np.random.rand(10, 2).astype(np.float32)
    with pytest.raises(Exception):
        pyopcode.Model(vertices, triangles)


def test_manual():
    vertices_a = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
    ], dtype='f4')
    triangles_a = np.array([
        [0, 1, 2],
        [3, 2, 1],
    ], dtype='i4')
    vertices_b = (vertices_a.copy() + [0.6, 0.6, 0]).astype('f4')
    triangles_b = triangles_a.copy()
    mesh_a = pyopcode.Model(vertices_a, triangles_a)
    mesh_b = pyopcode.Model(vertices_b, triangles_b)
    collider = pyopcode.Collision(mesh_a, mesh_b)
    transform = np.identity(4, dtype=np.float32)

    idx = collider.query(transform, transform)
    npt.assert_array_equal(idx, np.array([
        [1, 0],
    ], dtype='i4'))


def test_triangle_intersection():
    vertices_a, triangles_a = triangle_soup(10)
    vertices_b, triangles_b = triangle_soup(10)
    mesh_a = pyopcode.Model(vertices_a, triangles_a)
    mesh_b = pyopcode.Model(vertices_b, triangles_b)

    collider = pyopcode.Collision(mesh_a, mesh_b)
    transform = np.identity(4).astype(np.float32)
    idx = collider.query(transform, transform)
    print(idx)
    assert idx.shape[0] == 19  # matches to np seed 41


def test_no_triangle_intersection():
    vertices_a, triangles_a = triangle_soup(10)
    vertices_b, triangles_b = triangle_soup(10, range=(40, 41))  # apply insane offset to avoid any intersection
    mesh_a = pyopcode.Model(vertices_a, triangles_a)
    mesh_b = pyopcode.Model(vertices_b, triangles_b)

    collider = pyopcode.Collision(mesh_a, mesh_b)
    transform = np.identity(4).astype(np.float32)
    idx = collider.query(transform, transform)
    assert idx.shape[0] == 0


def test_basic():
    """no runtime erros plox"""
    vertices, triangles = triangle_soup(10)
    mesh0 = pyopcode.Model(vertices, triangles)
    mesh1 = pyopcode.Model(vertices, triangles)

    col = pyopcode.Collision(mesh0, mesh1)

    identity = np.identity(4).astype(np.float32)
    idx = col.query(identity, identity)
    print(idx)


def test_GIL():
    """tests running of multiple queries in a threadpool"""
    vertices, triangles = triangle_soup(10000, (-5, 5))
    mesh0 = pyopcode.Model(vertices, triangles)
    vertices, triangles = triangle_soup(10000, (-5, 5))
    mesh1 = pyopcode.Model(vertices, triangles)

    col = pyopcode.Collision(mesh0, mesh1)

    identity = np.identity(4).astype(np.float32)

    def transform_generator():
        """generate affine rotation matrices"""
        np.random.seed(42)
        for i in range(100):
            r = np.random.normal(size=(3, 3))
            u, _, v = np.linalg.svd(r)
            r = u.dot(np.eye(*r.shape)).dot(v)
            a = identity.copy()
            a[:3, :3] = r
            yield a

    from multiprocessing.pool import ThreadPool
    pool = ThreadPool(processes=4)
    results = pool.imap_unordered(lambda affine: col.query(affine, identity), transform_generator())

    import time
    start = time.time()
    for r in results:
        print(len(r))
    print(time.time() - start)


def test_rays():
    vertices, triangles = triangle_soup(10)
    mesh = pyopcode.Model(vertices, triangles)

    rays = np.random.normal(0, 1, (100, 2, 3)).astype(np.float32)
    faces = mesh.ray_query(rays)
    print(faces)
