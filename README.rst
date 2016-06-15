|Build Status| |Build status|

pyOPCODE
========================

Numpy bindings for the OPCODE collision detection library.

Currently, this only wraps the functionality to perform efficient triangle-triangle collisions between two rigid triangle meshes, using AABB trees.

 * Mesh(vertices, triangles) -> Mesh instance
 * Collision(Mesh_0, Mesh_1) -> Collision instance
 * Collision.query(affine4x4_0, affine4x4_1) -> ndarray, [n_collisions, 2], int

Support for wrapping the raytracing/picking code is planned as well.

In general; the hard part in making this package is getting the code to compile. Given that is does that, extending the interface should generally by simple.

Currently supported platforms are windows, linux, on both python 2.7 and 3.5


.. |Build Status| image:: https://travis-ci.org/ClinicalGraphics/pyopcode.svg?branch=master
   :target: https://travis-ci.org/ClinicalGraphics/pyopcode
.. |Build status| image:: https://ci.appveyor.com/api/projects/status/px6alq8csvoh0t19?svg=true
   :target: https://ci.appveyor.com/project/clinicalgraphics/pyopcode
