
#include <stdexcept>

#include <boost/cstdfloat.hpp>
#include <boost/cstdint.hpp>

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include "opcode/Opcode.h"


namespace py = pybind11;


typedef py::array_t<boost::float32_t, py::array::c_style> float_array;
typedef py::array_t<boost::int32_t, py::array::c_style> int_array;



/**
 * \brief constructs a set of strides for a c-style array, given its shape and itemsize
 */
template <typename I>
std::vector<I> c_strides(std::vector<I>& shape, I itemsize){
    std::vector<I> strides; 
    auto ndim = shape.size();
    strides.resize(ndim);
    strides[ndim-1] = itemsize;
    for (auto i=ndim; i>1; i--){
        strides[i-2] = strides[i-1] * shape[i-1];
    }
    return strides;
}

/**
 * \brief compute number of bytes taken by a contiguous array, given its shape and itemsize
 */
template <typename A>
size_t nbytes(A& shape, size_t itemsize){
    int n = itemsize;
    for (auto& s : shape) {
        n *= s;
    }
    return n;
}

/**
 * \brief Returns a view on the input c-style pyarray, with a new shape and dtype
 */
template<typename To, typename Ti>
py::array_t<To, py::array::c_style>
reinterpret_pyarray(
    py::array_t<Ti, py::array::c_style> arr, 
    std::vector<size_t> shape
){
    auto info = arr.request();

    if (nbytes(info.shape, sizeof(Ti)) != nbytes(shape, sizeof(To)))
        throw std::runtime_error("Impossible contiguous reinterpret cast");

    return py::array(
        shape,
        c_strides(shape, sizeof(To)),
        reinterpret_cast<To*>(info.ptr),
        arr
    );
}


/** 
Validate the shape of a pybind array
throw an exception is shape assumptions are not satisfied

Parameters:
    arr: pybind array to check
    shape: std::array; negative values denote unconstrained axes 
**/
template<typename A, size_t N, typename S>
void validate_shape(const A& arr, std::array<int32_t, N> shape, S message){
    auto arr_shape = arr.shape();
    if (shape.size() != arr.ndim()) throw std::runtime_error(message);
    for (auto i=0; i<arr.ndim(); i++) {
        if (shape[i] >= 0) {
            if (shape[i] != arr_shape[i]) {
                throw std::runtime_error(message);
            }
        }
    }
}


/**
 * \brief Returns py::array wrapping a sequence, with the lifetime of the array tied to the sequence
 */
template <typename Sequence>
inline py::array_t<typename Sequence::value_type, py::array::c_style> as_pyarray(Sequence &&seq) {
    auto size = seq.size();
    auto data = seq.data();
    std::unique_ptr<Sequence> seq_ptr = std::make_unique<Sequence>(std::move(seq));
    auto capsule = py::capsule(seq_ptr.get(), [](void *p) { std::unique_ptr<Sequence>(reinterpret_cast<Sequence*>(p)); });
    seq_ptr.release();
    return py::array(size, data, capsule);
}



class MeshModel {

    private:
        const float_array vertices;   
        const int_array triangles;
        const Opcode::MeshInterface interface;
        const Opcode::Model model;

    public:

        explicit MeshModel(const float_array vertices, const int_array triangles) :
            /*
            parameters
             vertices: py:array<float>32, shape [n_vertices, 3] 
                vertex coordinates
             triangles: py:array<int32>, shape [n_triangles, 3]
                each trinagle is a triplex of indices into the vertices array
            */
            vertices    (vertices),
            triangles   (triangles),
            interface   (init_interface()),
            model       (init_model())
        {
        }

        int_array ray_query(const float_array rays) const {
            /*
            parameters
                rays: py:array<float32>[n_rays, 2, 3]
                    axis-1 contains origin and direction vectors
                    note that contiguity in all axes is important
            returns: 
                faces: py::array<int32>[n_rays]
                    first triangle index or -1 in case of no hit 
            */ 
            validate_shape(
                rays, 
                std::array<int, 3>{-1, 2, 3}, 
                "Rays should have shape [*, 2, 3]"
            );

            auto ice_rays = reinterpret_cast<IceMaths::Ray *>(rays.request().ptr);
            auto n_rays = rays.shape()[0];
            std::vector<int32_t> faces;

            {
                py::gil_scoped_release release;

                faces.reserve(n_rays);

                Opcode::RayCollider RC = Opcode::RayCollider();
                RC.SetFirstContact(false);
                RC.SetTemporalCoherence(true);
                RC.SetClosestHit(true);
                RC.SetCulling(false);

                static udword Cache;
                Opcode::CollisionFaces CF;
                RC.SetDestination(&CF);

                // perform ray queries and push results to vector
                for (auto i=0; i < n_rays; i++) {
                    bool status(RC.Collide(ice_rays[i], model, 0, &Cache));
                    faces.push_back(RC.GetNbIntersections() ? CF.GetFaces()[0].mFaceID : -1);
                }
            }

            return as_pyarray(std::move(faces));
        }



    private:
        Opcode::MeshInterface init_interface() const {

            validate_shape(triangles, std::array<int, 2>{-1, 3}, "Triangles should have shape [*, 3]");
            validate_shape(vertices, std::array<int, 2>{-1, 3}, "Vertices should have shape [*, 3]");

            Opcode::MeshInterface interface;
            interface.SetNbTriangles(triangles.shape()[0]);
            interface.SetNbVertices(vertices.shape()[0]);
            interface.SetPointers(
                reinterpret_cast<IceMaths::IndexedTriangle *>(triangles.request().ptr),
                reinterpret_cast<IceMaths::Point *>(vertices.request().ptr)
            );
            return interface;
        }

        Opcode::Model init_model() const {
            py::gil_scoped_release release;

            //Tree building settings
            Opcode::OPCODECREATE OPCC;
            OPCC.mIMesh = const_cast<Opcode::MeshInterface*>(&interface);
            OPCC.mNoLeaf = true;
            OPCC.mQuantized = false;
            OPCC.mKeepOriginal = false;

            Opcode::Model model;
            model.Build(OPCC);
            return model;
        }

    friend class MeshCollision;
};


class MeshCollision {

private:
    const MeshModel& mesh0;
    const MeshModel& mesh1;

    const Opcode::BVTCache cache;

    Opcode::BVTCache init_cache() const {
        Opcode::BVTCache cache;
        cache.Model0 = &mesh0.model;
        cache.Model1 = &mesh1.model;
        return cache;
    }

public:
    explicit MeshCollision(const MeshModel& mesh0, const MeshModel& mesh1) :
        mesh0(mesh0),
        mesh1(mesh1),
        cache(init_cache())
    {}

    int_array query(const float_array affine0, const float_array affine1) const {
        /*
        parameters
            affine0: py::array<float32>[4, 4]
            affine1: py::array<float32>[4, 4]
        returns
            pairs: py::array<int32>[n_pairs, 2]
                each pair of ints denotes a pair of indices into the triangle arrays of both meshes
        */
        validate_shape(affine0, std::array<int, 2>{4, 4}, "Affine should have shape [4, 4]");
        validate_shape(affine1, std::array<int, 2>{4, 4}, "Affine should have shape [4, 4]");

        auto affine0_ptr = reinterpret_cast<IceMaths::Matrix4x4*>(affine0.request().ptr);
        auto affine1_ptr = reinterpret_cast<IceMaths::Matrix4x4*>(affine1.request().ptr);

        // declare outside gil scope
        std::vector<boost::int32_t> pairs;
        unsigned long n_pairs = 0;

        // Collision query
        Opcode::AABBTreeCollider TC;
        {
            py::gil_scoped_release release;

            const bool IsOk(
                TC.Collide(
                    const_cast<Opcode::BVTCache&>(cache),       // const in this context, but not for TC
                    affine0_ptr,
                    affine1_ptr
                )
            );

            // lets see how much hits we have
            n_pairs = TC.GetContactStatus() ? TC.GetNbPairs() : 0;
            const IceCore::Pair* ice_pairs = TC.GetContactStatus() ? TC.GetPairs() : (IceCore::Pair*)0;
            auto foo = reinterpret_cast<const boost::int32_t*>(ice_pairs);
            // push pairs into vector. 
            // alternatively, make our capsule hang on to AABBTreeCollider?
            // internal container type may have null pointer when empty; not sure how py::array feels about that
            pairs.insert(pairs.end(), foo, foo + n_pairs * 2);
        }

        // return view with shape [n_pairs, 2]
        // return reinterpret_pyarray<boost::int32_t>(
        //     as_pyarray(std::move(pairs)), 
        //     std::vector<size_t>{n_pairs, 2}
        // );
        auto foo = as_pyarray(std::move(pairs));
        foo.resize(std::vector<size_t>{n_pairs, 2});
        return foo;

    }
};



PYBIND11_MODULE(pyopcode, m) {

    py::class_<MeshModel>(m, "Model")
        .def(py::init<float_array, int_array>())
        .def("ray_query", &MeshModel::ray_query);

    py::class_<MeshCollision>(m, "Collision")
        .def(py::init<MeshModel&, MeshModel&>())
        .def("query", &MeshCollision::query);

}
