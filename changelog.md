0.4.0
-----
- Replaced boost.numpy based bindings with pybind11 bindings
- Changed build pipeline to the pybind11 recommended one (see https://github.com/pybind/python_example). as set up now, it should work for any python version, OS, conda and pip. (So far windows and < py36 has not been tested yet.)
- Small change in the cpp source to be c++17 compatible
- Small change in the interface; MeshModel.ray_query now takes an argument of shape [*, 2, 3] rather than [*, 6]
- More aggresive GIL release
- Fewer memory copies when returning ndarrays