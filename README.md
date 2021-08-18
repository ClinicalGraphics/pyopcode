# pyopcode

Python bindings for the OPCODE collision detection library.

Note that the bindings provide access to only a small portion of the full library.
Pull requests to expose a larger API surface area are welcome.

Current functionality includes:

* Ray-querying triangle meshes
* Colliding pairs of triangle meshes under affine transformations

See the test suite for various usage examples.

## API

### pyopcode.Model(vertices, triangle)

This class represents a triangle mesh and the constructor takes two arguments:

* `vertices: ndarray float32 [n_vertices, 3])`
* `triangles: ndarray int32 [n_triangles, 3])`

The `vertices` array is expected to hold object space 3D coordinates
and `triangles` indexes the `vertices` array.

Instances of this class expose the method `ray_query`, and they can be passed
to the `pyopcode.Collision` constructor to create a collider.

### pyopcode.Model.ray_query(rays)

This instance method takes a single argument:

* `rays: ndarray float32 [n_rays, 2, 3]`

And returns a single array:

* `faces: ndarray int32 [n_rays]`

The `rays` array is expected to hold a 3D origin coordinate and direction
vector for each ray.

The returned `faces` array holds the index of the first triangle that is hit
by each ray, or `-1` in case of no hit.

### pyopcode.Collision(mesh0, mesh1)

This class represents a mesh collider and the constructor takes two arguments:

* `mesh0: pyopcode.Model`
* `mesh1: pyopcode.Model`

Instances of this class expose the method `query`.

### pyopcode.Collision.query(affine0, affine1)

This instance method takes two arguments:

* `affine0: ndarray float32 [4, 4]`
* `affine1: ndarray float32 [4, 4]`

And returns a single array:

* `pairs: ndarray int32 [n_pairs, 2]`

The `affine0` and `affine1` arrays are expected to hold 3D affine transformation
matrices for each of the two mesh models that were passed to the constructor.
These are applied to the models during the query collision.

The returned `pairs` array holds index pairs of triangles that collided.

## Collision example

```python
import numpy as np
import pyopcode

# create two simple triangle meshes to collide
vertices_a = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
    ], dtype="f4")
triangles_a = np.array([
        [0, 1, 2],
        [3, 2, 1],
    ], dtype="i4")
mesh0 = pyopcode.Model(vertices_a, triangles_a)

vertices_b = (vertices_a.copy() + [0.6, 0.6, 0]).astype("f4")
triangles_b = triangles_a.copy()
mesh1 = pyopcode.Model(vertices_b, triangles_b)

# create collider
collider = pyopcode.Collision(mesh0, mesh1)

# collide the models under affine transforms
affine0 = np.identity(4, dtype="f4")
affine1 = np.identity(4, dtype="f4")
pairs = collider.query(affine0, affine1)
```

## Development and releasing

Build locally:

* `python -m pip wheel -w wheelhouse --no-deps .`

Develop and test locally (replace `bin` with `Scripts` on windows):

* `python -m venv .venv`
* `.venv/bin/pip install -e .[dev]`
* `.venv/bin/pytest tests`
* `.venv/bin/black .`

Release by pushing a tag that starts with `v`, for example `v0.1.0`.

Ensure you update the version number in `setup.py`.

## Dependency management

Sadly the virtual environment and dependency management tools
aren't quite ready for libraries just yet. So when adjusting dependencies,
ensure you update all places they are configured:

* `.github\workflows\build_wheels.yml`
  * Check `CIBW_TEST_REQUIRES`
  * Check `Build sdist`
* `pyproject.toml`
  * Check `build-system.requires`
* `setup.py`
  * Check `install_requires`
  * Check `extras_require`
  * Check `python_requires`
