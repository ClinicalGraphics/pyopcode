#include <iostream>
#include <boost/cstdfloat.hpp>
#include <boost/cstdint.hpp>
#include <boost/python.hpp>
#include <boost/python/numpy.hpp>
#include "opcode/Opcode.h"
 
namespace p = boost::python;
namespace np = boost::python::numpy;


class ReleaseGIL {
    /*
    allocate this on the stack to get GIL release handling
    */
    public:
        inline ReleaseGIL(){
            save_state = PyEval_SaveThread();
        }

        inline ~ReleaseGIL(){
            PyEval_RestoreThread(save_state);
        }
    private:
        PyThreadState *save_state;
};


class MeshModel {
    /*
    wrapper class for vertices and triangles,
    and corresponding opcode-model, or collision detection acceleration structure
    */
    public:
        const np::ndarray vertices;  // <boost::float32_t, 2>    
        const np::ndarray triangles;  // <boost::int32_t, 2>
        const Opcode::MeshInterface interface;
        const Opcode::Model model;

        explicit MeshModel(const np::ndarray vertices, const np::ndarray triangles) :
            vertices    (vertices),
            triangles   (triangles),
            interface   (init_interface()),
            model       (init_model())
        {}

        np::ndarray ray_query(const np::ndarray rays) const {
            // rays has shape [n_rays, 2*3]; note that contiguity in all axes is important
            // returns first faceid or -1 in case of no hit
            const np::dtype rays_dtype = np::dtype::get_builtin<boost::float32_t>();
            if (rays.get_nd() != 2
                || rays.shape(1) != 6
                || !(rays.get_flags() & np::ndarray::C_CONTIGUOUS)
                || rays.get_dtype().get_itemsize() != 4
                || rays.get_dtype() != rays_dtype) {
                PyErr_SetString(PyExc_ValueError, "rays must be a C-contiguous (n,6) array of dtype f4.");
                p::throw_error_already_set();
            }

            const boost::int32_t n_rays = rays.shape(0);
            // view input array as array of IceMaths::Ray
            const IceMaths::Ray* ice_rays = reinterpret_cast<IceMaths::Ray *>(rays.get_data());
            // result ndarray
            const p::tuple shape = p::make_tuple(n_rays);
            const np::dtype dtype = np::dtype::get_builtin<boost::int32_t>();
            np::ndarray faces = np::empty(shape, dtype);

            Opcode::RayCollider RC = Opcode::RayCollider();
            RC.SetFirstContact(false);
            RC.SetTemporalCoherence(true);
            RC.SetClosestHit(true);
            RC.SetCulling(false);

            static udword Cache;
            Opcode::CollisionFaces CF;
            RC.SetDestination(&CF);

            // write to the numpy buffer using raw pointer access for greater speed
            boost::int32_t* faces_ptr = reinterpret_cast<boost::int32_t*>(faces.get_data());
            for (boost::int32_t i=0; i < n_rays; i++) {
                bool status(RC.Collide(ice_rays[i], model, 0, &Cache));
                faces_ptr[i] = RC.GetNbIntersections() ? CF.GetFaces()[0].mFaceID : -1;
            }
            return faces;
        }

    private:
        Opcode::MeshInterface init_interface() const {
            Opcode::MeshInterface interface;

            const np::dtype triangles_dtype = np::dtype::get_builtin<boost::int32_t>();
            if (triangles.get_nd() != 2
                || triangles.shape(1) != 3
                || !(triangles.get_flags() & np::ndarray::C_CONTIGUOUS)
                || triangles.get_dtype().get_itemsize() != 4
                || triangles.get_dtype() != triangles_dtype) {
                PyErr_SetString(PyExc_ValueError, "triangles must be a C-contiguous (n,3) array of dtype i4.");
                p::throw_error_already_set();
            }
            const np::dtype vertices_dtype = np::dtype::get_builtin<boost::float32_t>();
            if (vertices.get_nd() != 2
                || vertices.shape(1) != 3
                || !(vertices.get_flags() & np::ndarray::C_CONTIGUOUS)
                || vertices.get_dtype().get_itemsize() != 4
                || vertices.get_dtype() != vertices_dtype) {
                PyErr_SetString(PyExc_ValueError, "vertices must be a C-contiguous (n,3) array of dtype f4.");
                p::throw_error_already_set();
            }

            interface.SetNbTriangles(triangles.shape(0));
            interface.SetNbVertices(vertices.shape(0));
            interface.SetPointers(
                reinterpret_cast<IceMaths::IndexedTriangle *>(triangles.get_data()),
                reinterpret_cast<IceMaths::Point *>(vertices.get_data())
            );
            return interface;
        }

        Opcode::Model init_model() const {
            //Tree building settings
            Opcode::OPCODECREATE OPCC;
            OPCC.mIMesh = const_cast<Opcode::MeshInterface*>(&interface);
            OPCC.mNoLeaf = true;
            OPCC.mQuantized = false;
            OPCC.mKeepOriginal = false;

            Opcode::Model model;
            {
                ReleaseGIL GIL;         // release GIL during heavy lifting without python calls
                model.Build(OPCC);
            }
            return model;
        }
};


class MeshCollision {
    // typedef ndarray<real_t, 2> affine_t;

    const MeshModel& mesh0;
    const MeshModel& mesh1;

    const Opcode::BVTCache cache;

public:
    explicit MeshCollision(const MeshModel& mesh0, const MeshModel& mesh1) :
        mesh0(mesh0),
        mesh1(mesh1),
        cache(init_cache())
    {}

    Opcode::BVTCache init_cache() const {
        Opcode::BVTCache cache;
        cache.Model0 = &mesh0.model;
        cache.Model1 = &mesh1.model;
        return cache;
    }

    // [int, 2]
    np::ndarray query(const np::ndarray affine0, const np::ndarray affine1) const {
        const np::dtype affine_dtype = np::dtype::get_builtin<boost::float32_t>();
        if (affine0.get_nd() != 2
            || affine0.shape(0) != 4
            || affine0.shape(1) != 4
            || !(affine0.get_flags() & np::ndarray::C_CONTIGUOUS || affine0.get_flags() & np::ndarray::F_CONTIGUOUS)
            || affine0.get_dtype().get_itemsize() != 4
            || affine0.get_dtype() != affine_dtype) {
            PyErr_SetString(PyExc_ValueError, "affine0 must be C or F-contiguous (4,4) array of dtype f4.");
            p::throw_error_already_set();
        }
        if (affine1.get_nd() != 2
            || affine1.shape(0) != 4
            || affine1.shape(1) != 4
            || !(affine1.get_flags() & np::ndarray::C_CONTIGUOUS || affine1.get_flags() & np::ndarray::F_CONTIGUOUS)
            || affine1.get_dtype().get_itemsize() != 4
            || affine1.get_dtype() != affine_dtype) {
            PyErr_SetString(PyExc_ValueError, "affine1 must be C or F-contiguous (4,4) array of dtype f4.");
            p::throw_error_already_set();
        }

        // Collision query
        Opcode::AABBTreeCollider TC;
        {
            ReleaseGIL GIL;         // release GIL during heavy lifting without python calls
            const bool IsOk(
                TC.Collide(
                    const_cast<Opcode::BVTCache&>(cache),       // const in this context, but not for TC
                    reinterpret_cast<IceMaths::Matrix4x4*>(affine0.get_data()),
                    reinterpret_cast<IceMaths::Matrix4x4*>(affine1.get_data())
                )
            );
        }

        // lets see how much hits we have
        const boost::int32_t n_pairs = TC.GetContactStatus() ? TC.GetNbPairs() : 0;
        const IceCore::Pair* ice_pairs = TC.GetContactStatus() ? TC.GetPairs() : (IceCore::Pair*)0;

        // result ndarray
        const p::tuple shape = p::make_tuple(n_pairs, 2);
        const np::dtype dtype = np::dtype::get_builtin<boost::int32_t>();
        np::ndarray pairs = np::empty(shape, dtype);

        // write to the numpy result array using raw pointer access for greater speed
        boost::int32_t* pairs_ptr = reinterpret_cast<boost::int32_t*>(pairs.get_data());
        for (boost::int32_t i=0; i < n_pairs; i++) {
            pairs_ptr[2*i] = ice_pairs[i].id0;
            pairs_ptr[2*i+1] = ice_pairs[i].id1;
        }
        
        return pairs;
    }
};


BOOST_PYTHON_MODULE(api)
{
    PyEval_InitThreads(); // init Python GIL control
    Py_Initialize(); // init Python
    np::initialize(); // init Numpy

    p::class_<MeshModel>("Model", p::init<np::ndarray, np::ndarray>())
        .def("ray_query", &MeshModel::ray_query)
        ;

    p::class_<MeshCollision>("Collision", p::init<MeshModel&, MeshModel&>())
        .def("query", &MeshCollision::query)
        ;
}
